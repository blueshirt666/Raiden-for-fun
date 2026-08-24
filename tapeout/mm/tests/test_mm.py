import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest

from config import BotConfig
from risk import Book, RiskGate
from strategy import MarketMaker
from valuation import RatioModel, quality, weight, weight_per_nand, amm_realized_price
from venue import BookTop, Fill, PaperVenue, Quote, Side


class TestFormula(unittest.TestCase):
    def test_quality_clamps(self):
        self.assertEqual(quality(100, 100), 1.0)
        self.assertEqual(quality(1e9, 1), 4.0)          # 顶满
        self.assertEqual(quality(1, 1e9), 0.25)         # 触底
        with self.assertRaises(ValueError):
            quality(100, 0)

    def test_weight_matches_brief(self):
        # #260 V3: 83 门, K=938, q=4
        self.assertEqual(weight(83, 938, 4.0, 1), 3835)
        self.assertEqual(weight(83, 938, 4.0, 6), 23010)
        self.assertAlmostEqual(weight_per_nand(83, 938, 4.0, 1), 46.20, places=2)

    def test_amm_haircut_monotone(self):
        p = [amm_realized_price(a, 16.57, 12752) for a in (1, 100, 1000)]
        self.assertTrue(p[0] > p[1] > p[2])             # 卖得越多均价越差
        self.assertLess(p[0], 16.57)                    # 手续费使其永远低于中价


class TestRatioModel(unittest.TestCase):
    def setUp(self):
        self.cfg = BotConfig()
        self.rm = RatioModel(self.cfg)

    def test_cap_is_processor_ratio(self):
        self.assertEqual(self.rm.fundamental_cap, 6.0)

    def test_fair_ratio_never_runs_away_with_market(self):
        for _ in range(500):
            self.rm.observe(17.7)                       # 市场长期虚高
        fair = self.rm.fair_ratio()
        self.assertLessEqual(fair, 6.0 * (1 + self.cfg.ratio_blend) + 1e-9)
        self.assertLess(fair, 17.7)                     # 绝不跟着市场跑

    def test_richness(self):
        self.assertAlmostEqual(self.rm.richness(18.0), 3.0)

    def test_ignores_garbage(self):
        self.rm.observe(float("nan")); self.rm.observe(-1.0)
        self.assertEqual(self.rm.fair_ratio(), 6.0)


class TestClamp(unittest.TestCase):
    """回归测试：公允值远离市场时不得报出比盘口更差的价。"""

    def test_sell_lifted_to_bid(self):
        top = BookTop(bid=0.0514, ask=0.0546, bid_size=3, ask_size=50)
        q = MarketMaker.clamp_to_book(Quote(Side.SELL, 0.0252, 10), top)
        self.assertEqual(q.price_bnb, 0.0514)           # 不白送一半
        self.assertEqual(q.size, 3)                     # 按对面可见量截断

    def test_buy_capped_at_ask(self):
        top = BookTop(bid=0.0514, ask=0.0546, bid_size=50, ask_size=4)
        q = MarketMaker.clamp_to_book(Quote(Side.BUY, 0.09, 10), top)
        self.assertEqual((q.price_bnb, q.size), (0.0546, 4))

    def test_passive_quote_untouched(self):
        top = BookTop(bid=0.0028, ask=0.0031)
        q = MarketMaker.clamp_to_book(Quote(Side.SELL, 0.0030, 10), top)
        self.assertEqual(q.price_bnb, 0.0030)


def _mm(anchor="ratio"):
    cfg = BotConfig(); cfg.anchor = anchor; cfg.dry_run = False
    v = PaperVenue({cfg.official.name: 0.00299, cfg.behemoth.name: 0.0530})
    return cfg, v, MarketMaker(cfg, v)


class TestQuoting(unittest.TestCase):
    def test_inventory_skew_direction(self):
        cfg, v, mm = _mm()
        leg = cfg.official
        flat = mm.desired(leg, 0.003)
        mm.book.pos(leg.name).units = leg.max_position   # 多头打满
        long_ = mm.desired(leg, 0.003)
        self.assertLess(long_.ask.price_bnb, flat.ask.price_bnb)   # 下移逼自己卖
        self.assertIsNone(long_.bid)                               # 不再加多

    def test_short_limit_blocks_sell(self):
        cfg, v, mm = _mm()
        leg = cfg.official
        mm.book.pos(leg.name).units = -leg.max_position
        d = mm.desired(leg, 0.003)
        self.assertIsNone(d.ask)
        self.assertIsNotNone(d.bid)

    def test_half_spread_covers_gas(self):
        cfg, v, mm = _mm()
        cfg.fees.gas_per_tx_bnb = 0.01                   # 极端 gas
        hs = mm.half_spread(cfg.official, 0.003)
        self.assertGreaterEqual(hs * cfg.official.clip,
                                cfg.fees.gas_per_tx_bnb * cfg.official.min_edge_over_gas)

    def test_requote_hysteresis(self):
        cfg, v, mm = _mm()
        leg = cfg.official
        o = v.place(leg.name, Quote(Side.BUY, 0.00300, leg.clip))
        same = Quote(Side.BUY, 0.00300 * 1.001, leg.clip)   # 漂移 10bps < 800
        self.assertFalse(mm.needs_replace(leg, o, same, 0.003))
        far = Quote(Side.BUY, 0.00300 * 1.2, leg.clip)      # 漂移 2000bps
        self.assertTrue(mm.needs_replace(leg, o, far, 0.003))

    def test_ratio_anchor_prices_behemoth_below_market(self):
        cfg, v, mm = _mm("ratio")
        fv = mm.fair_values({n: v.top(n) for n in mm.legs})
        self.assertLess(fv[cfg.behemoth.name], v.top(cfg.behemoth.name).mid)

    def test_market_anchor_tracks_mid(self):
        cfg, v, mm = _mm("market")
        fv = mm.fair_values({n: v.top(n) for n in mm.legs})
        self.assertAlmostEqual(fv[cfg.behemoth.name], v.top(cfg.behemoth.name).mid)


class TestRisk(unittest.TestCase):
    def test_position_accounting(self):
        b = Book()
        b.pos("x").apply(Fill("x", Side.BUY, 0.01, 5))
        b.pos("x").apply(Fill("x", Side.SELL, 0.02, 5))
        self.assertEqual(b.pos("x").units, 0)
        self.assertAlmostEqual(b.mark_to_market({"x": 0.0}), 0.05)   # 赚 5×0.01

    def test_halts_are_sticky(self):
        cfg = BotConfig(); g = RiskGate(cfg); b = Book()
        self.assertFalse(g.check(b, {}, market_ratio=1e6, quote_age_sec=0, bnb_balance=1))
        self.assertTrue(g.halted)
        # 条件恢复正常也不自动重启
        self.assertFalse(g.check(b, {}, market_ratio=6.0, quote_age_sec=0, bnb_balance=1))

    def test_low_balance_halts(self):
        cfg = BotConfig(); g = RiskGate(cfg)
        g.check(Book(), {}, market_ratio=6.0, quote_age_sec=0,
                bnb_balance=cfg.risk.min_bnb_reserve / 2)
        self.assertTrue(g.halted)

    def test_pull_all_on_halt(self):
        cfg, v, mm = _mm()
        mm.on_tick(bnb_balance=1.0)
        self.assertTrue(any(v.open_orders(n) for n in mm.legs))
        r = mm.on_tick(bnb_balance=0.0)                  # 余额不足
        self.assertEqual(r["status"], "halted")
        self.assertFalse(any(v.open_orders(n) for n in mm.legs))


class TestPaperVenue(unittest.TestCase):
    def test_aggressive_sell_fills(self):
        v = PaperVenue({"x": 1.0}, order_rate=1.0, seed=3)
        v.place("x", Quote(Side.SELL, 0.5, 20))          # 远低于市场卖一
        for _ in range(30):
            v.step()
        self.assertTrue(v.drain_fills())

    def test_passive_quote_does_not_fill(self):
        v = PaperVenue({"x": 1.0}, order_rate=1.0, vol_bps=0.0, impact_bps=0.0, seed=3)
        v.place("x", Quote(Side.SELL, 5.0, 20))          # 远高于市场
        for _ in range(30):
            v.step()
        self.assertEqual(v.drain_fills(), [])


class TestChainStub(unittest.TestCase):
    def test_refuses_without_abi(self):
        from chain import ChainVenue, MissingABIError
        with self.assertRaises(MissingABIError):
            ChainVenue("https://rpc", "0xdD20B9537b9f5DB9d2A23E6B11Ad863cF81930d8")


if __name__ == "__main__":
    unittest.main(verbosity=2)
