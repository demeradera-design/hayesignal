from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import config
from .analyzer import analyze
from .notify import send_webhook
from .sources import RateLimited, fetch_rss, fetch_x
from .store import Store


def poll_once(store=None):
    store = store or Store()
    if not store.acquire_lock(50):
        return {"skipped": "outra coleta em andamento"}
    try:
        return _poll(store)
    finally:
        store.release_lock()


def _poll(store):
    bootstrap = store.is_empty()
    report = {"bootstrap": bootstrap, "fetched": 0, "new": 0, "notified": False, "errors": []}
    tasks = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        if config.X_BEARER_TOKEN:
            tasks["x"] = ex.submit(
                fetch_x,
                config.X_BEARER_TOKEN,
                config.X_USERNAME,
                store.get("hayes:x_since_id"),
                store.get("hayes:x_user_id"),
                config.X_EXCLUDE,
            )
        for name, url in config.feeds():
            tasks[f"rss:{name}"] = ex.submit(fetch_rss, name, url)

    collected = []
    for key, fut in tasks.items():
        try:
            res = fut.result()
        except RateLimited as e:
            report["errors"].append(f"{key}: limite de requisições ({e})")
            continue
        except Exception as e:  # uma fonte fora do ar não derruba as outras
            report["errors"].append(f"{key}: {type(e).__name__}: {e}")
            continue
        if key == "x":
            user_id, items = res
            store.set("hayes:x_user_id", user_id)
            if items:
                store.set("hayes:x_since_id", str(max(int(i.id.split(":", 1)[1]) for i in items)))
            collected += items
        else:
            collected += res

    report["fetched"] = len(collected)
    collected.sort(key=lambda i: i.published_at)
    new_items = []
    for it in collected:
        if store.add_if_new(it.id):
            d = it.to_dict()
            d["analysis"] = analyze(f"{it.title}. {it.text}" if it.title else it.text)
            store.push_item(d)
            new_items.append(d)
    report["new"] = len(new_items)

    # Na 1ª execução só carrega o histórico; não dispara o robô com posts antigos.
    if new_items and not bootstrap and config.WEBHOOK_URL:
        report["notified"] = send_webhook(config.WEBHOOK_URL, config.WEBHOOK_SECRET, new_items)

    store.set("hayes:last_poll", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    return report
