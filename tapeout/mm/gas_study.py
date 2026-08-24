"""gas 与改单频率的敏感性 —— 这是这两个市场能否做市的决定性变量。"""
import statistics
from bot import run
from config import BotConfig
from venue import PaperVenue

def trial(anchor, requote_bps, gas, seed, ticks=600):
    cfg = BotConfig(); cfg.anchor = anchor; cfg.dry_run = False
    cfg.fees.gas_per_tx_bnb = gas
    cfg.official.requote_bps = requote_bps
    cfg.behemoth.requote_bps = requote_bps * 1.5
    cfg.risk.max_daily_loss_bnb = 999    # 关掉停机，看完整 600 tick 的经济性
    v = PaperVenue({cfg.official.name: 0.00299, cfg.behemoth.name: 0.0530}, seed=seed)
    o = run(cfg, v, ticks, bnb_balance=1.0, verbose=False)
    return o["pnl_bnb"], o["gas_bnb"]

print("600 tick，关闭停机，20 个种子中位数（BNB）\n")
for anchor in ("market", "ratio"):
    print(f"--- 锚 = {anchor} ---")
    print(f"{'改单阈值bps':>11}{'gas/笔':>9}{'净PnL':>10}{'其中gas':>10}{'毛利':>10}")
    for rq in (80, 300, 1000):
        for gas in (0.0003, 0.00005):
            rs = [trial(anchor, rq, gas, s) for s in range(1, 21)]
            net = statistics.median(r[0] for r in rs)
            g = statistics.median(r[1] for r in rs)
            print(f"{rq:>11}{gas:>9.5f}{net:>+10.4f}{g:>10.4f}{net+g:>+10.4f}")
    print()
