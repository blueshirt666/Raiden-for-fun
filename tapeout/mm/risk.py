"""风控。任何一条触发就撤单停机，不留"再试一次"的口子。"""
from __future__ import annotations
from dataclasses import dataclass, field

from config import BotConfig
from venue import Fill, Side


@dataclass
class Position:
    units: int = 0
    cost_bnb: float = 0.0      # 累计净现金流（买为负、卖为正）

    def apply(self, f: Fill) -> None:
        if f.side is Side.BUY:
            self.units += f.size
            self.cost_bnb -= f.price_bnb * f.size
        else:
            self.units -= f.size
            self.cost_bnb += f.price_bnb * f.size
        self.cost_bnb -= f.fee_bnb


@dataclass
class Book:
    positions: dict[str, Position] = field(default_factory=dict)
    gas_spent_bnb: float = 0.0
    tx_failures: int = 0

    def pos(self, leg: str) -> Position:
        return self.positions.setdefault(leg, Position())

    def mark_to_market(self, marks: dict[str, float]) -> float:
        """已实现现金流 + 未实现持仓市值 - gas。"""
        v = -self.gas_spent_bnb
        for leg, p in self.positions.items():
            v += p.cost_bnb + p.units * marks.get(leg, 0.0)
        return v

    def notional(self, marks: dict[str, float]) -> float:
        return sum(abs(p.units) * marks.get(leg, 0.0)
                   for leg, p in self.positions.items())


class RiskGate:
    def __init__(self, cfg: BotConfig):
        self.cfg = cfg
        self.halted = False
        self.reasons: list[str] = []
        self._peak_pnl = 0.0

    def _halt(self, why: str) -> None:
        if why not in self.reasons:
            self.reasons.append(why)
        self.halted = True

    def check(self, book: Book, marks: dict[str, float], *,
              market_ratio: float | None, quote_age_sec: float,
              bnb_balance: float) -> bool:
        """返回是否允许继续报价。停机后不自动恢复。"""
        r = self.cfg.risk
        pnl = book.mark_to_market(marks)
        self._peak_pnl = max(self._peak_pnl, pnl)
        if self._peak_pnl - pnl > r.max_daily_loss_bnb:
            self._halt(f"回撤 {self._peak_pnl - pnl:.4f} BNB 超过上限 {r.max_daily_loss_bnb}")
        if book.notional(marks) > r.max_notional_bnb:
            self._halt(f"铺出去的名义 {book.notional(marks):.3f} 超过上限 {r.max_notional_bnb}")
        if bnb_balance < r.min_bnb_reserve:
            self._halt(f"BNB 余额 {bnb_balance:.4f} 低于 gas 储备 {r.min_bnb_reserve}")
        if market_ratio is not None and not (r.ratio_sane_lo <= market_ratio <= r.ratio_sane_hi):
            self._halt(f"比值 {market_ratio:.2f} 离开合理区间 —— 疑似行情源故障")
        if quote_age_sec > r.max_quote_age_sec:
            self._halt(f"行情已过期 {quote_age_sec:.0f}s")
        if book.tx_failures >= r.max_consecutive_tx_failures:
            self._halt(f"连续 {book.tx_failures} 笔交易失败")
        return not self.halted

    def position_room(self, leg_cfg, book: Book) -> tuple[int, int]:
        """还能买多少 / 还能卖多少（颗）。"""
        u = book.pos(leg_cfg.name).units
        return (max(0, leg_cfg.max_position - u), max(0, leg_cfg.max_position + u))
