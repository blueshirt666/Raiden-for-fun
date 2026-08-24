"""主循环。默认 dry-run；真实下单需要 chain.py 补完 + 显式 --live。"""
from __future__ import annotations
import argparse
import json
import time

from config import BotConfig
from strategy import MarketMaker
from valuation import RatioModel, liquidity_warning
from venue import PaperVenue, Venue


def build_venue(cfg: BotConfig, mode: str) -> Venue:
    """dry_run 只管**真实链上交易**。paper 场所本身就是沙盒，必须真的把单子
    放进模拟簿子里，否则每 tick 都会重复下单、白烧 gas，回测结果毫无意义。"""
    legs = {cfg.official.name: 0.00299, cfg.behemoth.name: 0.0530}
    if mode == "paper":
        cfg.dry_run = False
        return PaperVenue(legs, fee_bps=cfg.fees.taker_fee_bps)
    from chain import ChainVenue   # 缺 ABI 会在这里明确报错
    raise SystemExit("live 模式需要先补完 chain.py（见该文件文档）")


def run(cfg: BotConfig, venue: Venue, ticks: int, bnb_balance: float,
        interval: float = 0.0, verbose: bool = True) -> dict:
    mm = MarketMaker(cfg, venue)
    marks: dict[str, float] = {}
    warn = liquidity_warning(cfg)
    if warn and verbose:
        print(f"[流动性告警] {warn}\n")
    last = {}
    for i in range(ticks):
        last = mm.on_tick(bnb_balance=bnb_balance)
        if last.get("fair"):
            marks = last["fair"]          # 记住最后一次有效标记价，停机时用它算 PnL
        if last["status"] == "halted":
            if verbose:
                print(f"[停机] tick {i}: {'; '.join(last['reasons'])}")
            break
        if isinstance(venue, PaperVenue):
            venue.step()
        if verbose and i % max(1, ticks // 10) == 0 and last["status"] == "ok":
            print(f"tick {i:>4}  比值 {last['market_ratio']:.2f} "
                  f"(贵度 {last['richness']:.2f})  持仓 {last['positions']}  "
                  f"PnL {last['pnl_bnb']:+.5f} BNB")
        if interval:
            time.sleep(interval)
    # 停机时 last 里没有 pnl_bnb，必须用最后有效标记价重算，否则汇总全是 0
    final_pnl = mm.book.mark_to_market(marks) if marks else 0.0
    return {"last": last, "pnl_bnb": final_pnl, "ticks_run": i + 1,
            "gas_bnb": mm.book.gas_spent_bnb,
            "positions": {k: v.units for k, v in mm.book.positions.items()},
            "halted": mm.gate.halted, "reasons": mm.gate.reasons}


def main() -> None:
    ap = argparse.ArgumentParser(description="TapeOut 双晶体管做市机器人")
    ap.add_argument("--mode", choices=["paper", "live"], default="paper")
    ap.add_argument("--ticks", type=int, default=500)
    ap.add_argument("--bnb", type=float, default=1.0, help="可用 BNB 余额")
    ap.add_argument("--live", action="store_true", help="关闭 dry_run，真下单")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    cfg = BotConfig()
    cfg.dry_run = not a.live
    if a.live and a.mode == "paper":
        raise SystemExit("--live 只对 --mode live 有意义")
    venue = build_venue(cfg, a.mode)
    out = run(cfg, venue, a.ticks, a.bnb, verbose=not a.json)
    if a.json:
        print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
    else:
        print(f"\n结束：持仓 {out['positions']}  gas {out['gas_bnb']:.5f} BNB"
              f"{'  [已停机: ' + '; '.join(out['reasons']) + ']' if out['halted'] else ''}")


if __name__ == "__main__":
    main()
