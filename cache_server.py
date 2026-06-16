"""
Simulasi Cache Server Sederhana
================================
Server HTTP localhost yang mensimulasikan cara kerja cache:
- Strategi LRU (Least Recently Used)
- Cache hit / miss tracking
- TTL (Time To Live) opsional
- Visual log di terminal
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import OrderedDict
import json
import time
import threading
import random

# ─────────────────────────────────────
# Implementasi LRU Cache
# ─────────────────────────────────────

class LRUCache:
    def __init__(self, capacity: int = 5, ttl: int = None):
        self.capacity  = capacity
        self.ttl       = ttl          # seconds, None = tidak expired
        self.cache     = OrderedDict()
        self.lock      = threading.Lock()
        self.stats     = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, key: str):
        with self.lock:
            if key not in self.cache:
                self.stats["misses"] += 1
                return None, "MISS"

            entry = self.cache[key]

            # Cek TTL
            if self.ttl and (time.time() - entry["created_at"]) > self.ttl:
                del self.cache[key]
                self.stats["misses"] += 1
                return None, "EXPIRED"

            # Pindah ke ujung (most recently used)
            self.cache.move_to_end(key)
            self.stats["hits"] += 1
            return entry["value"], "HIT"

    def put(self, key: str, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                self.cache[key]["value"] = value
                self.cache[key]["created_at"] = time.time()
            else:
                if len(self.cache) >= self.capacity:
                    # Hapus yang paling jarang dipakai (ujung kiri)
                    evicted_key, _ = self.cache.popitem(last=False)
                    self.stats["evictions"] += 1
                    print(f"  [EVICT] Key '{evicted_key}' dikeluarkan dari cache")

                self.cache[key] = {
                    "value": value,
                    "created_at": time.time()
                }

    def snapshot(self):
        """Kembalikan isi cache saat ini (dari MRU ke LRU)."""
        with self.lock:
            now = time.time()
            result = []
            for k, v in reversed(self.cache.items()):
                age = round(now - v["created_at"], 1)
                ttl_left = round(self.ttl - age, 1) if self.ttl else None
                result.append({
                    "key": k,
                    "value": v["value"],
                    "age_sec": age,
                    "ttl_left": ttl_left
                })
            return result

    @property
    def hit_rate(self):
        total = self.stats["hits"] + self.stats["misses"]
        return round((self.stats["hits"] / total * 100), 1) if total else 0.0


# ─────────────────────────────────────
# Simulasi "Database" lambat
# ─────────────────────────────────────

_db = {}
_db_delay = 0.3   # detik latency simulasi

def db_fetch(key: str):
    """Simulasikan query ke database yang lambat."""
    time.sleep(_db_delay)
    if key not in _db:
        # Auto-generate data untuk demo
        _db[key] = {
            "id": key,
            "name": f"User-{key.upper()}",
            "email": f"{key}@example.com",
            "score": random.randint(10, 99)
        }
    return _db[key]

def db_save(key: str, value):
    _db[key] = value


# ─────────────────────────────────────
# Instance Cache Global
# ─────────────────────────────────────

cache = LRUCache(capacity=5, ttl=30)


# ─────────────────────────────────────
# HTTP Handler
# ─────────────────────────────────────

HTML_PAGE = open("index.html", encoding="utf-8").read() if __name__ == "__main__" else ""

class CacheHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress default log; kita pakai custom

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        # ── Sajikan UI ──────────────────────────────
        if self.path == "/" or self.path == "/index.html":
            body = HTML_PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
            return

        # ── GET /cache/status ───────────────────────
        if self.path == "/cache/status":
            self.send_json({
                "capacity": cache.capacity,
                "size": len(cache.cache),
                "ttl": cache.ttl,
                "stats": cache.stats,
                "hit_rate": cache.hit_rate,
                "entries": cache.snapshot()
            })
            return

        # ── GET /data/<key> ─────────────────────────
        if self.path.startswith("/data/"):
            key = self.path[6:]
            if not key:
                self.send_json({"error": "Key tidak boleh kosong"}, 400)
                return

            t0 = time.time()
            value, result = cache.get(key)
            elapsed_ms = round((time.time() - t0) * 1000, 1)

            if result == "HIT":
                print(f"  ✅ HIT    '{key}'  ({elapsed_ms} ms)")
                self.send_json({
                    "key": key, "value": value,
                    "result": result, "elapsed_ms": elapsed_ms,
                    "source": "cache"
                })
                return

            # MISS atau EXPIRED → ambil dari DB
            label = "MISS" if result == "MISS" else "EXPIRED"
            print(f"  ❌ {label:<7} '{key}'  → query DB...")
            value = db_fetch(key)
            cache.put(key, value)
            elapsed_ms = round((time.time() - t0) * 1000, 1)
            print(f"            '{key}'  disimpan ke cache  ({elapsed_ms} ms total)")

            self.send_json({
                "key": key, "value": value,
                "result": result, "elapsed_ms": elapsed_ms,
                "source": "database"
            })
            return

        self.send_json({"error": "Path tidak ditemukan"}, 404)

    def do_POST(self):
        # ── POST /data/<key> ────────────────────────
        if self.path.startswith("/data/"):
            key = self.path[6:]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                value = json.loads(body)
            except Exception:
                self.send_json({"error": "Body bukan JSON valid"}, 400)
                return

            db_save(key, value)
            cache.put(key, value)
            print(f"  📝 PUT    '{key}'  → tersimpan ke DB + cache")
            self.send_json({"key": key, "value": value, "saved": True})
            return

        self.send_json({"error": "Path tidak ditemukan"}, 404)

    def do_DELETE(self):
        # ── DELETE /cache ───────────────────────────
        if self.path == "/cache":
            with cache.lock:
                cache.cache.clear()
            print("  🗑️  Cache dikosongkan")
            self.send_json({"cleared": True})
            return

        # ── DELETE /cache/<key> ─────────────────────
        if self.path.startswith("/cache/"):
            key = self.path[7:]
            with cache.lock:
                removed = key in cache.cache
                cache.cache.pop(key, None)
            print(f"  🗑️  Hapus  '{key}' dari cache ({'' if removed else 'tidak '}ada)")
            self.send_json({"key": key, "removed": removed})
            return

        self.send_json({"error": "Path tidak ditemukan"}, 404)


# ─────────────────────────────────────
# Entry Point
# ─────────────────────────────────────

def run(port: int = 8765):
    import os
    # Pindah ke folder ini agar bisa baca index.html
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    global HTML_PAGE
    HTML_PAGE = open("index.html", encoding="utf-8").read()

    server = HTTPServer(("localhost", port), CacheHandler)
    print("=" * 55)
    print("   🗄️   Cache Server Python  —  localhost:" + str(port))
    print("=" * 55)
    print(f"  Kapasitas cache : {cache.capacity} slot  |  TTL: {cache.ttl}s")
    print(f"  DB latency      : {_db_delay*1000:.0f} ms (simulasi)")
    print(f"  UI              : http://localhost:{port}")
    print("-" * 55)
    print("  [LEGEND]  ✅ HIT = dari cache  |  ❌ MISS = dari DB")
    print("=" * 55)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server dihentikan.")
        server.server_close()

if __name__ == "__main__":
    run()