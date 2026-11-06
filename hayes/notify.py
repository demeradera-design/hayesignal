import hashlib
import hmac
import json
import time

import requests


def send_webhook(url, secret, items):
    """POST assinado (HMAC-SHA256 sobre '<timestamp>.<corpo>') para o seu robô."""
    body = json.dumps(
        {"event": "hayes.new_items", "count": len(items), "items": items},
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    ts = str(int(time.time()))
    headers = {"Content-Type": "application/json", "X-Hayes-Timestamp": ts}
    if secret:
        sig = hmac.new(secret.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()
        headers["X-Hayes-Signature"] = "sha256=" + sig
    for _ in range(2):
        try:
            if requests.post(url, data=body, headers=headers, timeout=6).ok:
                return True
        except requests.RequestException:
            pass
    return False
