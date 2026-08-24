"""场所抽象。PaperVenue 今天就能跑；真实下单见 chain.py。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import random


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Quote:
    """一侧的挂单意图。"""
    side: Side
    price_bnb: float
    size: int


@dataclass
class Order(Quote):
    order_id: str = ""
    leg: str = ""
    filled: int = 0

    @property
    def remaining(self) -> int:
        return self.size - self.filled


@dataclass
class Fill:
    leg: str
    side: Side
    price_bnb: float
    size: int
    fee_bnb: float = 0.0


@dataclass
class BookTop:
    """行情快照：某一腿的买一/卖一。"""
    bid: float | None
    ask: float | None
    bid_size: int = 0
    ask_size: int = 0

    @property
    def mid(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        return 0.5 * (self.bid + self.ask)


class Venue(ABC):
    """机器人只依赖这五个方法。换成真链只需实现这个接口。"""

    @abstractmethod
    def top(self, leg: str) -> BookTop: ...

    @abstractmethod
    def open_orders(self, leg: str) -> list[Order]: ...

    @abstractmethod
    def place(self, leg: str, quote: Quote) -> Order: ...

    @abstractmethod
    def cancel(self, order: Order) -> None: ...

    @abstractmethod
    def drain_fills(self) -> list[Fill]: ...


class PaperVenue(Venue):
    """带逆向选择的模拟撮合。

    外部中价随机游走；每 tick 以一定概率来一笔市价单，吃掉最优价一侧。
    我们的单只要比市场最优价更优就会先成交 —— 成交后中价朝该方向冲击，
    这就是逆向选择：报得越紧，被打穿得越狠。不建模这个，回测会骗人。
    """

    def __init__(self, mids: dict[str, float], *, spread_bps: float = 300.0,
                 vol_bps: float = 60.0, order_rate: float = 0.35,
                 trade_size: tuple[int, int] = (1, 6), impact_bps: float = 25.0,
                 fee_bps: float = 0.0, seed: int = 7):
        self.mids = dict(mids)
        self.spread = spread_bps / 10_000.0
        self.vol = vol_bps / 10_000.0
        self.order_rate = order_rate
        self.trade_size = trade_size
        self.impact = impact_bps / 10_000.0
        self.fee_bps = fee_bps
        self.rng = random.Random(seed)
        self._orders: dict[str, list[Order]] = {k: [] for k in mids}
        self._fills: list[Fill] = []
        self._seq = 0

    # --- Venue 接口 ---
    def top(self, leg: str) -> BookTop:
        m = self.mids[leg]
        return BookTop(bid=m * (1 - self.spread), ask=m * (1 + self.spread),
                       bid_size=50, ask_size=50)

    def open_orders(self, leg: str) -> list[Order]:
        return list(self._orders[leg])

    def place(self, leg: str, q: Quote) -> Order:
        self._seq += 1
        o = Order(side=q.side, price_bnb=q.price_bnb, size=q.size,
                  order_id=f"p{self._seq}", leg=leg)
        self._orders[leg].append(o)
        return o

    def cancel(self, order: Order) -> None:
        lst = self._orders.get(order.leg, [])
        if order in lst:
            lst.remove(order)

    def drain_fills(self) -> list[Fill]:
        f, self._fills = self._fills, []
        return f

    # --- 模拟推进 ---
    def step(self) -> None:
        for leg in self.mids:
            self.mids[leg] *= math_exp_shock(self.rng, self.vol)
            if self.rng.random() >= self.order_rate:
                continue
            taker_buys = self.rng.random() < 0.5
            size = self.rng.randint(*self.trade_size)
            self._match(leg, taker_buys, size)

    def _match(self, leg: str, taker_buys: bool, size: int) -> None:
        """市价单先吃更优的价格。我们的单优于市场最优价时被成交。"""
        t = self.top(leg)
        # 对手方买单 -> 吃卖盘 -> 我们的 SELL 单参与
        ours = [o for o in self._orders[leg]
                if (o.side is Side.SELL) == taker_buys and o.remaining > 0]
        if not ours:
            return
        ours.sort(key=lambda o: o.price_bnb, reverse=not taker_buys)
        best_mkt = t.ask if taker_buys else t.bid
        for o in ours:
            if size <= 0:
                break
            competitive = o.price_bnb <= best_mkt if taker_buys else o.price_bnb >= best_mkt
            if not competitive:
                continue
            n = min(size, o.remaining)
            o.filled += n
            size -= n
            self._fills.append(Fill(leg=leg, side=o.side, price_bnb=o.price_bnb,
                                    size=n, fee_bnb=o.price_bnb * n * self.fee_bps / 10_000.0))
            # 逆向选择：成交后中价朝吃单方向移动
            self.mids[leg] *= (1 + self.impact) if taker_buys else (1 - self.impact)
        self._orders[leg] = [o for o in self._orders[leg] if o.remaining > 0]


def math_exp_shock(rng: random.Random, vol: float) -> float:
    import math
    return math.exp(rng.gauss(0.0, vol))
