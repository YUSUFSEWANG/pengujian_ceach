# 🗄 Simulasi Cache Sederhana — Python LRU

Proyek ini mensimulasikan cara kerja **cache** menggunakan Python murni
(tanpa library eksternal) dengan antarmuka web di `localhost`.

---

## Cara Menjalankan

```bash
# Masuk ke folder ini
cd cache-demo

# Jalankan server (Python 3.8+)
python cache_server.py
```

Kemudian buka browser di: **http://localhost:8765**

---

## Fitur

| Fitur | Keterangan |
|---|---|
| LRU Cache | Least Recently Used — slot paling lama tidak dipakai digeser keluar |
| TTL | Setiap entri otomatis expired setelah 30 detik |
| Simulasi DB | Request MISS akan delay 300 ms (meniru query ke database sungguhan) |
| Cache HIT | Request pada key yang sama ke-2 kalinya < 1 ms |
| REST API | Bisa dipakai dari terminal, Postman, atau kode Anda sendiri |

---

## Endpoint API

```
GET    /data/<key>          — Ambil data (lewat cache dulu)
POST   /data/<key>          — Simpan data (ke DB + cache)
DELETE /cache/<key>         — Hapus satu key dari cache
DELETE /cache               — Kosongkan seluruh cache
GET    /cache/status        — Lihat isi cache & statistik
```

### Contoh dengan curl

```bash
# Ambil data (MISS pertama, HIT ke-2)
curl http://localhost:8765/data/alice
curl http://localhost:8765/data/alice

# Simpan data sendiri
curl -X POST http://localhost:8765/data/bob \
     -H "Content-Type: application/json" \
     -d '{"nama":"Bob","kota":"Jakarta"}'

# Lihat isi cache
curl http://localhost:8765/cache/status | python -m json.tool

# Hapus satu key
curl -X DELETE http://localhost:8765/cache/alice

# Reset semua
curl -X DELETE http://localhost:8765/cache
```

---

## Cara Kerja Cache (Ringkas)

```
Request GET /data/alice
         │
         ▼
    ┌─────────────┐
    │  Cache LRU  │──── HIT  ──→ kembalikan data (<1ms)
    │  (5 slot)   │
    └──────┬──────┘
           │ MISS
           ▼
    ┌─────────────┐
    │  Database   │──── query (~300ms) ──→ simpan ke cache ──→ kembalikan
    └─────────────┘
```

**LRU Eviction**: Ketika cache penuh (5 slot) dan ada key baru masuk,
slot yang paling lama tidak diakses (*Least Recently Used*) akan dibuang.

---

## Struktur File

```
cache-demo/
├── cache_server.py   ← server HTTP + logika cache (baca ini!)
├── index.html        ← UI visual di browser
└── README.md         ← panduan ini
```
