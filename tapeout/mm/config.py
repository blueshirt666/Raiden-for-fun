"""参数。默认值取自 TAPEOUT_BRIEF.md §9 的 2026-08-24 快照，会过期，跑之前核一遍。"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Protocol:
    """链上锁死的公式参数（setFormula 已锁）。"""
    lam: int = 6            # 面积里 1 LATCH = 6 NAND
    lam_burn: int = 1       # 工本里 1 LATCH = 1 NAND
    beta: int = 3           # 深度指数
    Q: float = 4.0          # q 的上下限 [1/Q, Q]
    P_official: int = 1     # 官方处理器系数
    P_behemoth: int = 6     # 巨兽处理器系数


@dataclass
class Market:
    """市场快照。这些数会动，是机器人的输入不是常量。"""
    bnb_usd: float = 700.0
    bem_usd: float = 16.57              # 显示价，不等于可成交价
    bem_pool_usd: float = 12_752.0      # AMM 报价侧深度
    yield_per_weight: float = 0.008374  # BEM/天/权重
    total_weight: float = 847_064.0
    seats_used: int = 522
    seats_total: int = 534


@dataclass
class Fees:
    gas_per_tx_bnb: float = 0.0003      # BSC 上一笔的大致成本
    taker_fee_bps: float = 0.0          # 未知，需从合约确认
    maker_fee_bps: float = 0.0


@dataclass
class LegConfig:
    """单个晶体管品种的做市参数。"""
    name: str
    processor: str                       # 'official' | 'behemoth'
    clip: int = 10                       # 每笔挂单颗数
    max_position: int = 60               # 单边最大持仓（颗）
    target_position: int = 0
    base_half_spread_bps: float = 250.0  # 基础半价差
    skew_coef: float = 1.0               # 库存偏移强度（×半价差）
    requote_bps: float = 800.0           # 公允值漂移超过这个才改单（gas_study.py 实测标定）
    min_edge_over_gas: float = 2.0       # 单笔预期毛利至少是 gas 的几倍


@dataclass
class RiskLimits:
    max_notional_bnb: float = 2.0        # 两腿合计最大铺出去的 BNB
    min_bnb_reserve: float = 0.05        # 留作 gas 的余额下限
    max_daily_loss_bnb: float = 0.15     # 当日回撤上限，触及即停
    ratio_sane_lo: float = 1.0           # 比值离谱即停（数据源出问题的信号）
    ratio_sane_hi: float = 40.0
    max_consecutive_tx_failures: int = 3
    max_quote_age_sec: float = 300.0     # 行情过期就撤单


@dataclass
class BotConfig:
    protocol: Protocol = field(default_factory=Protocol)
    market: Market = field(default_factory=Market)
    fees: Fees = field(default_factory=Fees)
    risk: RiskLimits = field(default_factory=RiskLimits)
    official: LegConfig = field(default_factory=lambda: LegConfig("official-NAND", "official"))
    behemoth: LegConfig = field(default_factory=lambda: LegConfig(
        "behemoth-NAND", "behemoth", clip=2, max_position=10,
        base_half_spread_bps=400.0, requote_bps=1200.0))
    # 比值模型：巨兽 NAND 的产出上限是官方的 P_beh/P_off 倍
    ratio_seat_premium: float = 1.0      # 巨兽席位更稀缺时可 >1，需实测
    ratio_blend: float = 0.35            # 公允比值里市场 EWMA 的权重
    ratio_ewma_halflife_ticks: float = 60.0
    # 公允值锚：
    #   "ratio"  = 巨兽腿由基本面比值定价 → 市场比值虚高时结构性做空巨兽。
    #              盈亏由这个方向性仓位主导，不是价差捕获。押的是比值回归。
    #   "market" = 两腿都锚市场中价 → 纯做市，无方向观点，只赚价差和库存回归。
    anchor: str = "ratio"
    dry_run: bool = True                 # 只管真实链上交易；paper 场所不受此影响
