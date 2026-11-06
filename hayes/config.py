import os


def env(name, default=None):
    value = os.getenv(name)
    return value if value not in (None, "") else default


X_USERNAME = env("X_USERNAME", "CryptoHayes")
X_BEARER_TOKEN = env("X_BEARER_TOKEN")
X_EXCLUDE = env("X_EXCLUDE", "retweets,replies")
CRON_SECRET = env("CRON_SECRET")
WEBHOOK_URL = env("WEBHOOK_URL")
WEBHOOK_SECRET = env("WEBHOOK_SECRET")

# Fontes oficiais de Arthur Hayes. Formato: "Nome|URL,Nome|URL"
DEFAULT_FEEDS = (
    "Crypto Trader Digest|https://cryptohayes.substack.com/feed,"
    "Maelstrom|https://maelstromfund.substack.com/feed"
)


def _parse_feeds(raw):
    out = []
    for part in (raw or "").split(","):
        part = part.strip()
        if "|" not in part:
            continue
        name, url = part.split("|", 1)
        if url.strip().startswith("https://"):
            out.append((name.strip(), url.strip()))
    return out


def feeds():
    """HAYES_FEEDS substitui o padrão; EXTRA_FEEDS acrescenta (ex.: sua própria ponte RSS do X)."""
    return _parse_feeds(env("HAYES_FEEDS", DEFAULT_FEEDS)) + _parse_feeds(env("EXTRA_FEEDS"))
