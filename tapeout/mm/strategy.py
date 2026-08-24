"""报价引擎。

三条设计结论直接落在这里：
  1. 锚在比值上，不锚在绝对价上（BEM 显示价不可成交）。
     官方腿跟市场中价，巨兽腿由 fair_ratio 定价 —— 市场比值虚高时，
     我们的巨兽卖价自然落在市场卖价下方，买价远离市场，方向性倾斜自动产生。
  2. gas 占官方 NAND 单价约一成，所以半价差有 gas 下限，且用滞回抑制改单。
  3. 簿子极薄（巨兽卖一仅 10 颗），clip 和持仓上限都必须小。
"""
from __future__ import annotations
from dataclasses import dataclass

from config import BotConfig, LegConfig
from risk import Book, RiskGate
from valuation import RatioModel
from venue import BookTop, Order, Quote, Side, Venue


@dataclass
class Desired:
    bid: Quote | None
    ask: Quote | None
    fair: float
    note: str = ""


class MarketMaker:
    def __init__(self, cfg: BotConfig, venue: Venue):
        self.cfg = cfg
        self.venue = venue
        self.ratio = RatioModel(cfg)
        self.book = Book()
        self.gate = RiskGate(cfg)
        self.legs = {cfg.official.name: cfg.official, cfg.behemoth.name: cfg.behemoth}

    # ---------- 公允值 ----------
    def fair_values(self, tops: dict[str, BookTop]) -> dict[str, float] | None:
        off, beh = self.cfg.official.name, self.cfg.behemoth.name
        m_off, m_beh = tops[off].mid, tops[beh].mid
        if m_off is None or m_off <= 0:
            return None
        if m_beh is not None and m_beh > 0:
            self.ratio.observe(m_beh / m_off)
        fair_off = m_off              # 官方腿永远跟市场中价（流动性最好的一条）
        if self.cfg.anchor == "market":
            if m_beh is None or m_beh <= 0:
                return None
            fair_beh = m_beh          # 纯做市：不带方向观点
        else:
            fair_beh = fair_off * self.ratio.fair_ratio()
        return {off: fair_off, beh: fair_beh}

    # ---------- 半价差 ----------
    def half_spread(self, leg: LegConfig, fair: float) -> float:
        """基础价差与 gas 下限取大：单笔毛利必须显著覆盖一次进出的 gas。"""
        base = fair * leg.base_half_spread_bps / 10_000.0
        gas_floor = (self.cfg.fees.gas_per_tx_bnb * leg.min_edge_over_gas) / max(1, leg.clip)
        return max(base, gas_floor)

    # ---------- 盘口夹取 ----------
    @staticmethod
    def clamp_to_book(q: Quote | None, top: BookTop) -> Quote | None:
        """绝不报出比盘口已有价格更差的价。

        公允值远离市场时（巨兽虚高 3 倍就是这种情况），朴素报价会把卖单挂在
        自己的公允值上 —— 而市场买一比它高一倍，等于主动送钱。这里把卖价抬到
        至少等于买一、买价压到至多等于卖一；跨价时按对面可见量截断，避免撒单。
        """
        if q is None:
            return None
        if q.side is Side.SELL and top.bid is not None and q.price_bnb < top.bid:
            return Quote(Side.SELL, top.bid, min(q.size, max(1, top.bid_size)))
        if q.side is Side.BUY and top.ask is not None and q.price_bnb > top.ask:
            return Quote(Side.BUY, top.ask, min(q.size, max(1, top.ask_size)))
        return q

    # ---------- 报价 ----------
    def desired(self, leg: LegConfig, fair: float, top: BookTop | None = None) -> Desired:
        hs = self.half_spread(leg, fair)
        pos = self.book.pos(leg.name).units
        # 库存偏移：持多则整体下移，逼自己卖出
        raw = (pos - leg.target_position) / max(1, leg.max_position)
        skew = max(-1.0, min(1.0, raw)) * leg.skew_coef * hs
        buy_room, sell_room = self.gate.position_room(leg, self.book)
        bid_sz, ask_sz = min(leg.clip, buy_room), min(leg.clip, sell_room)
        bid = Quote(Side.BUY, fair - hs - skew, bid_sz) if bid_sz > 0 else None
        ask = Quote(Side.SELL, fair + hs - skew, ask_sz) if ask_sz > 0 else None
        if top is not None:
            bid, ask = self.clamp_to_book(bid, top), self.clamp_to_book(ask, top)
        note = ""
        if bid_sz == 0:
            note = "多头打满，只挂卖"
        elif ask_sz == 0:
            note = "空头打满，只挂买"
        return Desired(bid=bid, ask=ask, fair=fair, note=note)

    # ---------- 改单滞回（省 gas 的关键）----------
    def needs_replace(self, leg: LegConfig, existing: Order | None, want: Quote | None,
                      fair: float) -> bool:
        if want is None:
            return existing is not None
        if existing is None:
            return True
        if existing.remaining != want.size:
            return True
        drift = abs(existing.price_bnb - want.price_bnb) / fair * 10_000.0
        return drift > leg.requote_bps

    def reconcile(self, leg: LegConfig, want: Desired) -> list[tuple[str, object]]:
        """把现存挂单收敛到目标。返回动作日志。dry_run 下只记录不发单。"""
        acts: list[tuple[str, object]] = []
        cur = {Side.BUY: None, Side.SELL: None}
        for o in self.venue.open_orders(leg.name):
            cur[o.side] = o
        for side, w in ((Side.BUY, want.bid), (Side.SELL, want.ask)):
            e = cur[side]
            if not self.needs_replace(leg, e, w, want.fair):
                continue
            if e is not None:
                acts.append(("cancel", e))
                if not self.cfg.dry_run:
                    self.venue.cancel(e)
                self.book.gas_spent_bnb += self.cfg.fees.gas_per_tx_bnb
            if w is not None:
                acts.append(("place", (leg.name, w)))
                if not self.cfg.dry_run:
                    self.venue.place(leg.name, w)
                self.book.gas_spent_bnb += self.cfg.fees.gas_per_tx_bnb
        return acts

    def pull_all(self) -> None:
        for name in self.legs:
            for o in self.venue.open_orders(name):
                self.venue.cancel(o)
                self.book.gas_spent_bnb += self.cfg.fees.gas_per_tx_bnb

    # ---------- 单个 tick ----------
    def on_tick(self, *, bnb_balance: float, quote_age_sec: float = 0.0) -> dict:
        for f in self.venue.drain_fills():
            self.book.pos(f.leg).apply(f)
        tops = {name: self.venue.top(name) for name in self.legs}
        fv = self.fair_values(tops)
        if fv is None:
            self.pull_all()
            return {"status": "no-market"}
        off, beh = self.cfg.official.name, self.cfg.behemoth.name
        m_ratio = (tops[beh].mid / tops[off].mid) if tops[off].mid else None
        if not self.gate.check(self.book, fv, market_ratio=m_ratio,
                               quote_age_sec=quote_age_sec, bnb_balance=bnb_balance):
            self.pull_all()
            return {"status": "halted", "reasons": self.gate.reasons}
        acts = []
        for name, leg in self.legs.items():
            acts += self.reconcile(leg, self.desired(leg, fv[name], tops[name]))
        return {"status": "ok", "fair": fv, "market_ratio": m_ratio,
                "fair_ratio": self.ratio.fair_ratio(),
                "richness": self.ratio.richness(m_ratio) if m_ratio else None,
                "actions": acts, "pnl_bnb": self.book.mark_to_market(fv),
                "positions": {k: v.units for k, v in self.book.positions.items()}}
