import unittest
from datetime import datetime, timedelta, timezone

from hayes.analyzer import aggregate, analyze


class AnalyzerTests(unittest.TestCase):
    def test_bullish_btc(self):
        a = analyze("Bitcoin will explode higher. Back up the truck and buy.")
        self.assertGreater(a["assets"]["BTC"]["score"], 0)
        self.assertEqual(a["label"], "bullish")

    def test_bearish_hype_uppercase_ticker(self):
        a = analyze("I dumped HYPE and took profits. The hype around it is gone.")
        self.assertLess(a["assets"]["HYPE"]["score"], 0)

    def test_lowercase_hype_is_not_asset(self):
        self.assertNotIn("HYPE", analyze("There is too much hype in the market.")["assets"])

    def test_long_term_is_not_a_signal(self):
        self.assertEqual(analyze("This is a long-term and short-term view.")["signal_words"], 0)

    def test_themes(self):
        themes = analyze("Dollar liquidity is rising as the Fed eases.")["themes"]
        self.assertIn("liquidez", themes)
        self.assertIn("fed", themes)

    def test_neutral(self):
        a = analyze("Lunch was good.")
        self.assertEqual((a["assets"], a["label"]), ({}, "neutral"))

    def test_aggregate_decay(self):
        now = datetime(2026, 11, 5, tzinfo=timezone.utc)

        def item(hours_ago, score):
            return {
                "published_at": (now - timedelta(hours=hours_ago)).isoformat(),
                "analysis": {"assets": {"BTC": {"mentions": 1, "score": score}}},
            }

        out = aggregate([item(1, 1.0), item(40, -1.0), item(100, -1.0)], hours=48, now=now)
        self.assertEqual(out["BTC"]["mentions"], 2)  # o de 100 h fica fora da janela
        self.assertGreater(out["BTC"]["score"], 0)  # o recente pesa mais


if __name__ == "__main__":
    unittest.main()
