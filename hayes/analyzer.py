"""Análise heurística (palavras-chave) por ativo. É um *feature* para o seu modelo, não uma decisão."""
import re
from datetime import datetime, timezone


def _asset(ticker, names=()):
    parts = []
    if ticker:
        parts += [rf"\$(?i:{ticker})\b", rf"\b{ticker}\b"]  # ticker em maiúsculas evita falsos positivos (ex.: "hype", "near")
    if names:
        parts.append(r"(?i:\b(?:" + "|".join(names) + r")\b)")
    return re.compile("|".join(parts))


ASSETS = {
    "BTC": _asset("BTC", ["bitcoin"]),
    "ETH": _asset("ETH", ["ethereum", "ether"]),
    "SOL": _asset("SOL", ["solana"]),
    "HYPE": _asset("HYPE", ["hyperliquid"]),
    "ZEC": _asset("ZEC", ["zcash"]),
    "ENA": _asset("ENA", ["ethena"]),
    "NEAR": _asset("NEAR", ["near protocol"]),
    "FLOP": _asset("FLOP", ["flop network"]),
    "MSTR": _asset("MSTR", ["microstrategy"]),
    "UNI": _asset("UNI", ["uniswap"]),
    "USD": _asset("DXY", ["dollar"]),
    "JPY": _asset("JPY", ["yen", "boj"]),
    "GOLD": _asset(None, ["gold"]),
}

THEMES = {
    "liquidez": re.compile(r"liquidity|money print|\bQE\b|balance sheet|\bTGA\b|reverse repo", re.I),
    "fed": re.compile(r"\bfed\b|powell|fomc|rate cut|rate hike", re.I),
    "tesouro": re.compile(r"bessent|treasury|buyback|basis trade", re.I),
    "iene": re.compile(r"\byen\b|\bboj\b|carry trade", re.I),
    "china": re.compile(r"\bchina\b|\bpboc\b|yuan|renminbi", re.I),
    "bolha_ia": re.compile(r"ai bubble|nvidia|\bAI\b.*\bbubble", re.I),
    "tarifas": re.compile(r"tariff", re.I),
}

BULL = re.compile(
    r"bullish|\bbuy(?:ing)?\b|back up the truck|accumulat\w+|\brall(?:y|ies)\b|\bhigher\b|\bmoon\b|"
    r"send it|foregone conclusion|\bexplod\w+|upside|going long|\blongs\b|money print\w*",
    re.I,
)
BEAR = re.compile(
    r"bearish|\bsell(?:ing)?\b|\bdump(?:ed|ing)?\b|\bcrash\w*|collapse|take profits?|taking profits?|took profits?|"
    r"downside|recession|bubble burst\w*|cannot rally|\bexit(?:ed)?\b|\bshort(?:ing|ed)?\b(?!-? ?term)",
    re.I,
)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def label(score):
    if score > 0.25:
        return "bullish"
    if score < -0.25:
        return "bearish"
    return "neutral"


def _score(text):
    b, s = len(BULL.findall(text)), len(BEAR.findall(text))
    n = b + s
    return ((b - s) / n if n else 0.0), n


def analyze(text):
    text = text or ""
    sentences = [s for s in SENT_SPLIT.split(text) if s]
    assets = {}
    for name, rx in ASSETS.items():
        scores, mentions = [], 0
        for s in sentences:
            if rx.search(s):
                mentions += 1
                v, n = _score(s)
                if n:
                    scores.append(v)
        if mentions:
            assets[name] = {"mentions": mentions, "score": round(sum(scores) / len(scores), 2) if scores else 0.0}
    overall, n = _score(text)
    return {
        "assets": assets,
        "themes": [t for t, rx in THEMES.items() if rx.search(text)],
        "score": round(overall, 2),
        "label": label(overall),
        "signal_words": n,
    }


def aggregate(items, hours=48.0, half_life=24.0, now=None):
    """Score por ativo com decaimento exponencial (meia-vida em horas)."""
    now = now or datetime.now(timezone.utc)
    acc = {}
    for it in items:
        try:
            ts = datetime.fromisoformat(it["published_at"])
        except (KeyError, ValueError):
            continue
        age = max((now - ts).total_seconds() / 3600, 0.0)
        if age > hours:
            continue
        w = 0.5 ** (age / half_life)
        for asset, v in (it.get("analysis") or {}).get("assets", {}).items():
            e = acc.setdefault(asset, {"w": 0.0, "ws": 0.0, "mentions": 0, "last": ""})
            e["w"] += w
            e["ws"] += w * v["score"]
            e["mentions"] += v["mentions"]
            e["last"] = max(e["last"], it["published_at"])
    out = {}
    for asset, e in acc.items():
        sc = e["ws"] / e["w"] if e["w"] else 0.0
        out[asset] = {"score": round(sc, 2), "label": label(sc), "mentions": e["mentions"], "last_mention": e["last"]}
    return out
