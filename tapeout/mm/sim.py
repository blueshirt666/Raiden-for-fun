"""回测对比：两种锚 × 多个随机种子。"""
from __future__ import annotations
import statistics

from bot import run
from config import BotConfig
from venue import PaperVenue


def one(anchor: str, seed: int, ticks: int = 600, drift_bps: float = 0.0) -> dict:
    cfg = BotConfig(); cfg.anchor = anchor; cfg.dry_run = False
    v = PaperVenue({cfg.official.name: 0.00299, cfg.behemoth.name: 0.0530}, seed=seed)
    if drift_bps:                      # 给巨兽腿一个持续漂移，检验方向性风险
        base_step = v.step
        def step():
            base_step()
            v.mids[cfg.behemoth.name] *= (1 + drift_bps / 10_000.0)
        v.step = step
    out = run(cfg, v, ticks, bnb_balance=1.0, verbose=False)
    return {"pnl": out["pnl_bnb"], "gas": out["gas_bnb"], "ticks": out["ticks_run"],
            "halted": out["halted"], "pos": out["positions"]}


def sweep(anchor: str, drift_bps: float = 0.0, seeds=range(1, 21)) -> dict:
    rs = [one(anchor, s, drift_bps=drift_bps) for s in seeds]
    p = [r["pnl"] for r in rs]
    return {"anchor": anchor, "drift_bps": drift_bps, "n": len(rs),
            "median": statistics.median(p), "mean": statistics.fmean(p),
            "worst": min(p), "best": max(p),
            "halt_rate": sum(r["halted"] for r in rs) / len(rs),
            "ticks": statistics.fmean(r["ticks"] for r in rs),
            "gas": statistics.fmean(r["gas"] for r in rs)}


if __name__ == "__main__":
    print(f"{'锚':<8}{'比值漂移':>9}{'中位PnL':>10}{'最差':>10}{'最好':>10}{'停机率':>8}{'存活tick':>9}{'gas':>9}")
    print("-" * 73)
    for anchor in ("ratio", "market"):
        for drift in (0.0, +8.0, -8.0):
            r = sweep(anchor, drift)
            tag = {0.0: "无", 8.0: "巨兽走高", -8.0: "巨兽回落"}[drift]
            print(f"{anchor:<8}{tag:>9}{r['median']:>+10.4f}{r['worst']:>+10.4f}"
                  f"{r['best']:>+10.4f}{r['halt_rate']:>7.0%}{r['ticks']:>9.0f}{r['gas']:>9.4f}")
