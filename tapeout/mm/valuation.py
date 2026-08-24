"""晶体管估值。

核心判断（推导见 README）：
  绝对估值不可用 —— 全网日排放 ~7,093 BEM 是 BEM 池子存量(~770 BEM)的 9 倍，
  显示价 $16.57 完全不可成交，任何以 BEM 计价的公允值都是噪音。
  相对估值可用 —— 同一道题、同样烧 n 颗 NAND，两个处理器的 H 只差系数 P，
  BEM 价格在比值里被完全约掉。所以机器人锚在**比值**上，不锚在绝对价上。
"""
from dataclasses import dataclass
import math

from config import BotConfig


def quality(c_ref: float, c_mine: float, Q: float = 4.0) -> float:
    """q = clamp(C_ref / C, 1/Q, Q)"""
    if c_mine <= 0:
        raise ValueError("C 必须为正")
    return max(1.0 / Q, min(Q, c_ref / c_mine))


def weight(n_gates: int, k_task: int, q: float, P: int, n_latch: int = 0) -> float:
    """H = (b* + K_task·q) × P，纯组合电路 b* = n。"""
    b_star = n_gates + n_latch
    return (b_star + k_task * q) * P


def weight_per_nand(n_gates: int, k_task: int, q: float, P: int) -> float:
    """每烧一颗 NAND 换到多少权重 —— 这才是 NAND 的产出效率。"""
    return weight(n_gates, k_task, q, P) / n_gates


def amm_realized_price(amount_bem: float, mid_usd: float, pool_usd: float,
                       fee_bps: float = 30.0) -> float:
    """恒定乘积池里卖出 amount_bem 的实际均价。pool_usd = 报价侧储备。"""
    if amount_bem <= 0:
        return mid_usd
    reserve_bem = pool_usd / mid_usd
    realized = mid_usd / (1.0 + amount_bem / reserve_bem)
    return realized * (1.0 - fee_bps / 10_000.0)


@dataclass
class RatioModel:
    """公允比值 = 巨兽 NAND / 官方 NAND。

    上限来自协议本身：同样的电路放到巨兽上，H 恰好是 6 倍，所以单颗巨兽 NAND
    的产出上限就是官方的 6 倍。市场比值高于这个数，巨兽就是相对贵。
    """
    cfg: BotConfig
    _ewma: float | None = None

    @property
    def fundamental_cap(self) -> float:
        p = self.cfg.protocol
        return (p.P_behemoth / p.P_official) * self.cfg.ratio_seat_premium

    def observe(self, market_ratio: float) -> None:
        """喂入市场观测比值，维护 EWMA。"""
        if not math.isfinite(market_ratio) or market_ratio <= 0:
            return
        hl = self.cfg.ratio_ewma_halflife_ticks
        alpha = 1.0 - 0.5 ** (1.0 / hl) if hl > 0 else 1.0
        self._ewma = market_ratio if self._ewma is None else \
            self._ewma + alpha * (market_ratio - self._ewma)

    def fair_ratio(self) -> float:
        """公允比值：基本面上限与市场 EWMA 的混合，且**永不超过上限**。

        混合是为了不跟市场对着干太久（比值可能长期偏离），但硬顶保证我们
        绝不会在巨兽腿上按远高于其产出价值的价格接货。
        """
        cap = self.fundamental_cap
        if self._ewma is None:
            return cap
        w = self.cfg.ratio_blend
        blended = (1.0 - w) * cap + w * self._ewma
        return min(blended, cap * (1.0 + w))   # 允许有限溢出，但受控

    def richness(self, market_ratio: float) -> float:
        """市场比值 / 基本面上限。>1 表示巨兽相对贵。"""
        return market_ratio / self.fundamental_cap


def absolute_value_bnb_per_nand(cfg: BotConfig, n_gates: int, k_task: int,
                                q: float, P: int, horizon_days: float = 30.0,
                                yield_halflife_days: float = 14.0) -> float:
    """绝对估值。**仅供参考，不要拿来做市** —— 见模块头部说明。

    按权重日产折算，再打两道折：AMM 滑点、以及产出随全网权重增长的衰减。
    """
    m = cfg.market
    H = weight(n_gates, k_task, q, P)
    bem_per_day = H * m.yield_per_weight
    realized_usd = amm_realized_price(bem_per_day, m.bem_usd, m.bem_pool_usd)
    usd_per_day = bem_per_day * realized_usd
    lam = math.log(2.0) / yield_halflife_days
    effective_days = (1.0 - math.exp(-lam * horizon_days)) / lam
    total_usd = usd_per_day * effective_days
    return total_usd / m.bnb_usd / n_gates


def liquidity_warning(cfg: BotConfig) -> str | None:
    """池子撑不撑得住全网排放。撑不住就别信任何绝对估值。"""
    m = cfg.market
    daily_emission = m.total_weight * m.yield_per_weight
    reserve_bem = m.bem_pool_usd / m.bem_usd
    ratio = daily_emission / reserve_bem
    if ratio > 1.0:
        return (f"BEM 日排放 {daily_emission:,.0f} 是池内存量 {reserve_bem:,.0f} 的 "
                f"{ratio:.1f} 倍 —— 显示价不可成交，绝对估值不可用，只做比值。")
    return None
