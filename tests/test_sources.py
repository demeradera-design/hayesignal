import unittest

from hayes.sources import clean_html, parse_feed, to_iso

RSS = """<?xml version="1.0"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>Reality Test</title><link>https://cryptohayes.substack.com/p/reality-test</link>
<guid isPermaLink="false">abc-123</guid><pubDate>Mon, 02 Nov 2026 13:00:00 GMT</pubDate>
<description>short</description><content:encoded><![CDATA[<p>Bitcoin &amp; liquidity.</p>]]></content:encoded></item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry>
<id>tag:x,1</id><title>Hi</title><link href="https://example.com/1"/><updated>2026-11-02T13:00:00Z</updated>
<summary>Hello</summary></entry></feed>"""

EVIL = """<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]><rss><channel><item><guid>&b;</guid></item></channel></rss>"""


class SourcesTests(unittest.TestCase):
    def test_rss(self):
        (it,) = parse_feed(RSS, "Crypto Trader Digest")
        self.assertEqual(it.id, "rss:Crypto Trader Digest:abc-123")
        self.assertEqual(it.text, "Bitcoin & liquidity.")
        self.assertEqual(it.published_at, "2026-11-02T13:00:00+00:00")

    def test_atom(self):
        (it,) = parse_feed(ATOM, "x")
        self.assertEqual((it.url, it.text), ("https://example.com/1", "Hello"))

    def test_entities_rejected(self):
        with self.assertRaises(Exception):
            parse_feed(EVIL, "x")

    def test_helpers(self):
        self.assertEqual(clean_html("<b>a</b>&nbsp;b"), "a b")
        self.assertTrue(to_iso("2026-11-05T10:00:00.000Z").startswith("2026-11-05T10:00:00"))


if __name__ == "__main__":
    unittest.main()
