"""Coleta de fontes oficiais: API oficial do X (opcional) e feeds RSS/Atom (Substack)."""
import email.utils
import html
import re
from datetime import datetime, timezone

import requests
from defusedxml import ElementTree as ET  # protege contra XML malicioso (entity expansion)

from .models import Item

UA = {"User-Agent": "hayes-signal-monitor/1.0"}
TIMEOUT = 8
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
NS_CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
NS_ATOM = "{http://www.w3.org/2005/Atom}"


class RateLimited(Exception):
    pass


def clean_html(s):
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", s or ""))).strip()


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def to_iso(s):
    if not s:
        return _now_iso()
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return _now_iso()
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_feed(xml_text, source, author="Arthur Hayes"):
    root = ET.fromstring(xml_text)
    items = []
    for it in root.iter("item"):  # RSS 2.0
        link = (it.findtext("link") or "").strip()
        guid = (it.findtext("guid") or link).strip()
        if not guid:
            continue
        body = it.findtext(NS_CONTENT + "encoded") or it.findtext("description") or ""
        items.append(
            Item(
                id=f"rss:{source}:{guid}",
                source=source,
                author=author,
                title=clean_html(it.findtext("title")),
                text=clean_html(body)[:8000],
                url=link,
                published_at=to_iso(it.findtext("pubDate")),
            )
        )
    for en in root.iter(NS_ATOM + "entry"):  # Atom
        link_el = en.find(NS_ATOM + "link")
        link = link_el.get("href", "") if link_el is not None else ""
        guid = (en.findtext(NS_ATOM + "id") or link).strip()
        if not guid:
            continue
        body = en.findtext(NS_ATOM + "content") or en.findtext(NS_ATOM + "summary") or ""
        items.append(
            Item(
                id=f"rss:{source}:{guid}",
                source=source,
                author=author,
                title=clean_html(en.findtext(NS_ATOM + "title")),
                text=clean_html(body)[:8000],
                url=link,
                published_at=to_iso(en.findtext(NS_ATOM + "updated") or en.findtext(NS_ATOM + "published")),
            )
        )
    return items


def fetch_rss(name, url):
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    return parse_feed(r.text, name)


def _check(r):
    if r.status_code == 429:
        raise RateLimited(f"X API 429 (reset={r.headers.get('x-rate-limit-reset')})")
    r.raise_for_status()


def fetch_x(bearer, username, since_id=None, user_id=None, exclude="retweets,replies"):
    """API oficial v2. Usa since_id para só ler (e só pagar por) posts novos."""
    headers = {"Authorization": f"Bearer {bearer}", **UA}
    if not user_id:
        r = requests.get(f"https://api.x.com/2/users/by/username/{username}", headers=headers, timeout=TIMEOUT)
        _check(r)
        user_id = r.json()["data"]["id"]
    params = {
        "max_results": 100 if since_id else 10,  # 1ª execução: poucos posts, evita custo
        "tweet.fields": "created_at,public_metrics,note_tweet",
    }
    if exclude:
        params["exclude"] = exclude
    if since_id:
        params["since_id"] = since_id
    r = requests.get(f"https://api.x.com/2/users/{user_id}/tweets", headers=headers, params=params, timeout=TIMEOUT)
    _check(r)
    items = []
    for t in r.json().get("data") or []:
        text = (t.get("note_tweet") or {}).get("text") or t.get("text", "")
        items.append(
            Item(
                id=f"x:{t['id']}",
                source="x",
                author=username,
                title="",
                text=text,
                url=f"https://x.com/{username}/status/{t['id']}",
                published_at=to_iso(t.get("created_at")),
                metrics=t.get("public_metrics") or {},
            )
        )
    return user_id, items
