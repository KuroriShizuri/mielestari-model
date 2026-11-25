# mielestari-model — Model Finansial Uji Kasus PT MieLestari Tbk (FIKTIF)

Model perhitungan untuk deck case competition **"Lestari Sehat"** (uji mode
case competition kurori-deck, November 2026). Semua angka internal perusahaan
adalah **FIKTIF** — PT MieLestari Tbk adalah perusahaan fiktif; data riset
nyata (WINA, BPS Susenas, Nexdigm, dll.) hanya dipakai sebagai konteks di
deck, bukan dihitung di sini.

## Cara menjalankan

```bash
python3 mielestari-model.py        # model utama -> mielestari-model-output.json
python3 mielestari-v2-derived.py   # angka turunan (kuartalan, grid, skenario)
python3 mielestari-v4-derived.py   # angka turunan v4 (omzet, uji bobot MAUT, histogram)
```

Butuh Python 3 + NumPy. Tidak ada dependensi lain.

## Hasil utama (model utama)

| Opsi | Investasi | NPV 5 tahun (diskonto 12%) | Arus kas tahun 1-5 (Rp miliar) |
|------|-----------|----------------------------|--------------------------------|
| A. Masuk (build) | Rp 180 miliar | **Rp 641 miliar** | 120,1 - 181,3 - 232,9 - 297,4 - 378,0 |
| B. Bertahan (defend) | Rp 60 miliar | Rp 71 miliar | 36,4 tiap tahun |
| C. Kemitraan (partner) | Rp 90 miliar | Rp 40 miliar | 25,2 - 30,2 - 36,3 - 43,5 - 52,3 |

- Payback opsi A: **1,3 tahun**.
- Break-even volume tahun-1 (NPV = 0): **18,6 juta bungkus** (69% di bawah asumsi 60 juta).
- Monte Carlo 10.000 iterasi (distribusi segitiga, seed 20261125):
  **P(NPV > 0) = 100%** (10.000/10.000); P10 Rp 457 miliar, P50 Rp 633 miliar,
  P90 Rp 838 miliar; terendah Rp 245 miliar, tertinggi Rp 1.180 miliar.
- Tornado (satu variabel digeser ke ujung rentangnya): volume ±30% → NPV
  Rp 362-920 miliar; harga ±20% → Rp 449-834 miliar; marjin ±5 poin →
  Rp 514-768 miliar; pemasaran ±25% → Rp 631-651 miliar; kanibalisasi
  ±10 poin → Rp 619-663 miliar.

## Input model (semua FIKTIF)

| Variabel | Nilai dasar | Rentang sensitivitas |
|----------|-------------|----------------------|
| Harga Lestari Sehat | Rp 7.500/bungkus | ±20% |
| Volume tahun-1 | 60 juta bungkus | ±30% |
| Marjin kotor premium | 38% | ±5 poin |
| Pemasaran tahun-1 | Rp 45 miliar | ±25% |
| Kanibalisasi | 15% volume premium | ±10 poin |

Asumsi lain: pertumbuhan volume 25%/tahun; diskonto 12%; horizon 5 tahun;
pemasaran tahun 2-5 Rp 25 miliar/tahun (asumsi); marjin massal Rp 660/bungkus
(Rp 3.000 x 22%) untuk biaya kanibalisasi. Opsi B: +40 juta bungkus massal/
tahun + hemat Rp 10 miliar/tahun. Opsi C: 40% saham mitra; mitra 30 juta
bungkus tahun-1 @ Rp 7.000, marjin 30%, tumbuh 20%/tahun.

## File

- `mielestari-model.py` — model utama (NPV, tornado, Monte Carlo, risiko P x I)
- `mielestari-model-output.json` — hasil model utama
- `mielestari-v2-derived.py` / `mielestari-v2-derived.json` — build-up kuartalan,
  grid sensitivitas harga x volume, skenario downside, unit economics, kapasitas
- `mielestari-v4-derived.py` / `mielestari-v4-derived.json` — omzet tahun 1-5,
  uji bobot MAUT, bin histogram Monte Carlo

## Verifikasi cepat

```bash
python3 mielestari-model.py | head -8   # NPV A harus Rp 641 miliar
```

Deck yang memakai model ini: uji kasus MieLestari (kurori-deck-skill).
Lisensi: MIT.
