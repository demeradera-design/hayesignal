"""Persistência via Redis REST (Upstash / Vercel KV). Sem credenciais, usa memória (não durável)."""
import json
import threading
import time

import requests

from .config import env

_MEM = {"seen": set(), "items": [], "kv": {}, "lock_until": 0.0}
_MEM_LOCK = threading.Lock()


class Store:
    def __init__(self, force_memory=False):
        url = env("UPSTASH_REDIS_REST_URL") or env("KV_REST_API_URL")
        token = env("UPSTASH_REDIS_REST_TOKEN") or env("KV_REST_API_TOKEN")
        self.persistent = bool(url and token) and not force_memory
        self._url, self._token = (url, token) if self.persistent else (None, None)
        self._mem = _MEM if not force_memory else {"seen": set(), "items": [], "kv": {}, "lock_until": 0.0}

    def _cmd(self, *args):
        r = requests.post(
            self._url, headers={"Authorization": f"Bearer {self._token}"}, json=list(args), timeout=6
        )
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result")

    # --- dedupe atômico ---
    def add_if_new(self, item_id):
        if self.persistent:
            return self._cmd("SADD", "hayes:seen", item_id) == 1
        with _MEM_LOCK:
            if item_id in self._mem["seen"]:
                return False
            self._mem["seen"].add(item_id)
            return True

    def is_empty(self):
        if self.persistent:
            return int(self._cmd("SCARD", "hayes:seen") or 0) == 0
        return not self._mem["seen"]

    # --- itens (mais novo primeiro) ---
    def push_item(self, item, keep=500):
        payload = json.dumps(item, ensure_ascii=False)
        if self.persistent:
            self._cmd("LPUSH", "hayes:items", payload)
            self._cmd("LTRIM", "hayes:items", 0, keep - 1)
        else:
            self._mem["items"].insert(0, payload)
            del self._mem["items"][keep:]

    def list_items(self, limit=100):
        if self.persistent:
            raw = self._cmd("LRANGE", "hayes:items", 0, limit - 1) or []
        else:
            raw = self._mem["items"][:limit]
        return [json.loads(x) for x in raw]

    # --- chave/valor ---
    def get(self, key):
        return self._cmd("GET", key) if self.persistent else self._mem["kv"].get(key)

    def set(self, key, value):
        if self.persistent:
            self._cmd("SET", key, value)
        else:
            self._mem["kv"][key] = value

    # --- trava anti-sobreposição (cron + GitHub Actions ao mesmo tempo) ---
    def acquire_lock(self, ttl=50):
        if self.persistent:
            return self._cmd("SET", "hayes:lock", "1", "NX", "EX", ttl) == "OK"
        with _MEM_LOCK:
            if time.time() < self._mem["lock_until"]:
                return False
            self._mem["lock_until"] = time.time() + ttl
            return True

    def release_lock(self):
        if self.persistent:
            self._cmd("DEL", "hayes:lock")
        else:
            self._mem["lock_until"] = 0.0
