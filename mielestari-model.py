#!/usr/bin/env python3
"""
Model finansial uji kasus PT MieLestari Tbk (FIKTIF) - kurori-deck.
Semua angka internal perusahaan FIKTIF (brief 24 Nov 2026).
Data riset nyata TIDAK dihitung di sini - hanya dipakai sebagai konteks di deck.

Jalankan: python3 mielestari-model.py
Keluaran: angka NPV/tornado/Monte Carlo + JSON untuk build script deck.
"""
import json
import numpy as np

# ---------------------------------------------------------------- inputs (FIKTIF)
PRICE = 7500            # Rp/bungkus Lestari Sehat
VOL_Y1 = 60_000_000     # bungkus tahun-1
GROWTH = 0.25           # pertumbuhan volume per tahun
MARGIN = 0.38           # marjin kotor premium PADA HARGA DASAR (v6: lihat HPP di bawah)
# v6 (25 Nov 2026, perbaikan Sonnet r3 gap 1): HPP per bungkus adalah RUPIAH TETAP,
# bukan persen dari harga. HPP = Rp 4.650 = 7.500 x (1 - 0,38). Marjin 38% hanya
# berlaku di harga dasar; bila harga digeser, HPP tetap Rp 4.650 dan laba kotor
# per bungkus = harga - 4.650. Model v1-v5 memakai gp = harga x marjin, sehingga
# HPP ikut turun saat harga turun (di titik impas Rp 2.505, HPP model hanya
# Rp 1.553 - lebih murah dari HPP massal Rp 2.340; tidak masuk akal untuk produk
# premium). Angka dasar di Rp 7.500 TIDAK berubah karena perubahan ini.
PRICE_BASE = 7500       # harga dasar; HPP diturunkan dari marjin pada harga ini
HPP_PACK = 4650         # Rp/bungkus, TETAP = PRICE_BASE * (1 - MARGIN)
MKT_Y1 = 45.0           # Rp miliar, pemasaran tahun-1
MKT_LATER = 25.0        # Rp miliar/tahun tahun 2-5 (ASUMSI, FIKTIF - lihat catatan)
CANNIB = 0.15           # kanibalisasi, % dari volume premium
INVEST_A = 180.0        # Rp miliar
DISCOUNT = 0.12
YEARS = 5

MASSAL_PRICE = 3000     # Rp/bungkus (FIKTIF)
MASSAL_MARGIN = 0.22    # marjin kotor massal (FIKTIF)
MASSAL_MARGIN_RP = MASSAL_PRICE * MASSAL_MARGIN  # Rp 660/bungkus

# Opsi B (defend) - asumsi FIKTIF, dinyatakan di deck:
#   distribusi + efisiensi menambah volume massal 40 jt bungkus/tahun (flat)
#   pada marjin Rp 660 + penghematan biaya Rp 10 miliar/tahun.
INVEST_B = 60.0
B_VOL_ADD = 40_000_000
B_SAVING = 10.0

# Opsi C (partner) - asumsi FIKTIF, dinyatakan di deck:
#   saham minoritas 40% pada pemain sehat; mitra menjual 30 jt bungkus
#   tahun-1 @ Rp 7.000, marjin 30% (Rp 2.100/bungkus), tumbuh 20%/tahun.
INVEST_C = 90.0
C_SHARE = 0.40
C_VOL_Y1 = 30_000_000
C_PRICE = 7000
C_MARGIN = 0.30
C_GROWTH = 0.20

# ---------------------------------------------------------------- helpers
def pv_factor(t):
    return 1.0 / (1.0 + DISCOUNT) ** t

def npv_a(price=PRICE, vol_y1=VOL_Y1, margin=MARGIN,
          mkt_y1=MKT_Y1, cannib=CANNIB, invest=INVEST_A):
    """NPV opsi A (Rp miliar). Arus kas = laba kotor - pemasaran - biaya kanibalisasi.
    v6: HPP per bungkus TETAP (PRICE_BASE x (1-margin)); marjin = marjin pada
    harga dasar. Laba kotor per bungkus = harga - HPP."""
    hpp = PRICE_BASE * (1 - margin)
    gp_pack = price - hpp
    npv = -invest
    cfs = []
    for t in range(1, YEARS + 1):
        vol = vol_y1 * (1.0 + GROWTH) ** (t - 1)
        gross = vol * gp_pack / 1e9
        mkt = mkt_y1 if t == 1 else MKT_LATER
        cann = cannib * vol * MASSAL_MARGIN_RP / 1e9
        cf = gross - mkt - cann
        cfs.append(cf)
        npv += cf * pv_factor(t)
    return npv, cfs

def npv_b():
    cf = B_VOL_ADD * MASSAL_MARGIN_RP / 1e9 + B_SAVING  # Rp miliar/tahun
    ann = sum(pv_factor(t) for t in range(1, YEARS + 1))
    return cf * ann - INVEST_B, [cf] * YEARS

def npv_c():
    npv = -INVEST_C
    cfs = []
    for t in range(1, YEARS + 1):
        vol = C_VOL_Y1 * (1.0 + C_GROWTH) ** (t - 1)
        gross = vol * C_PRICE * C_MARGIN / 1e9
        cf = C_SHARE * gross
        cfs.append(cf)
        npv += cf * pv_factor(t)
    return npv, cfs

def payback(cfs, invest):
    cum = 0.0
    for t, cf in enumerate(cfs, start=1):
        prev = cum
        cum += cf
        if cum >= invest:
            frac = (invest - prev) / cf if cf else 0.0
            return (t - 1) + frac
    return None

def breakeven_volume():
    """Volume tahun-1 (juta bungkus) agar NPV A = 0. Pencarian biner."""
    lo, hi = 0.0, VOL_Y1
    for _ in range(60):
        mid = (lo + hi) / 2
        v, _ = npv_a(vol_y1=mid)
        if v > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2 / 1e6

# ---------------------------------------------------------------- base case
npvA, cfA = npv_a()
npvB, cfB = npv_b()
npvC, cfC = npv_c()
pbA = payback(cfA, INVEST_A)

# ---------------------------------------------------------------- tornado (+-rentang brief, satu variabel diubah)
tornado = {}
tornado["Harga jual +-20%"] = (
    npv_a(price=PRICE * 0.8)[0], npv_a(price=PRICE * 1.2)[0])
tornado["Volume tahun-1 +-30%"] = (
    npv_a(vol_y1=VOL_Y1 * 0.7)[0], npv_a(vol_y1=VOL_Y1 * 1.3)[0])
tornado["Marjin +-5 poin"] = (
    npv_a(margin=MARGIN - 0.05)[0], npv_a(margin=MARGIN + 0.05)[0])
tornado["Pemasaran tahun-1 +-25%"] = (
    npv_a(mkt_y1=MKT_Y1 * 1.25)[0], npv_a(mkt_y1=MKT_Y1 * 0.75)[0])
tornado["Kanibalisasi +-10 poin"] = (
    npv_a(cannib=CANNIB + 0.10)[0], npv_a(cannib=CANNIB - 0.10)[0])

# ---------------------------------------------------------------- Monte Carlo (10.000 iterasi, segitiga, variabel 1-3)
rng = np.random.default_rng(20261125)
N = 10_000
p = rng.triangular(6000, 7500, 9000, N)
v = rng.triangular(42_000_000, 60_000_000, 78_000_000, N)
m = rng.triangular(0.33, 0.38, 0.43, N)
# arus kas tahunan berbentuk vektor: vol_t = v * 1.25**(t-1); gross = vol_t*(p-HPP)
# v6: HPP = 7500*(1-m) tetap per bungkus; m = marjin pada harga dasar.
npvs = np.full(N, -INVEST_A)
for t in range(1, YEARS + 1):
    vol_t = v * (1.0 + GROWTH) ** (t - 1)
    gross = vol_t * (p - PRICE_BASE * (1 - m)) / 1e9
    mkt = MKT_Y1 if t == 1 else MKT_LATER
    cann = CANNIB * vol_t * MASSAL_MARGIN_RP / 1e9
    npvs += (gross - mkt - cann) * pv_factor(t)
p_pos = float(np.mean(npvs > 0))
p10, p50, p90 = [float(x) for x in np.percentile(npvs, [10, 50, 90])]
mc_min, mc_max = float(npvs.min()), float(npvs.max())

# ---------------------------------------------------------------- checks
vol_y5 = VOL_Y1 * (1.0 + GROWTH) ** 4
spare_capacity = 1_200_000_000 * (1 - 0.78)  # bungkus/tahun
market_anchor = 14.54e9 * 2000 / 1e12        # Rp triliun
vol_share_y1 = VOL_Y1 / 14.54e9 * 100        # % dari pasar
def breakeven_price():
    """Harga (Rp/bungkus) agar NPV A = 0, volume dan variabel lain di nilai dasar.
    v6: HPP tetap Rp 4.650, jadi titik impas jauh lebih tinggi dari v1-v5 (Rp 2.505)."""
    lo, hi = 0.0, PRICE
    for _ in range(80):
        mid = (lo + hi) / 2
        v, _ = npv_a(price=mid)
        if v > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2

def breakeven_hpp():
    """HPP per bungkus (Rp) agar NPV A = 0, harga dan variabel lain di nilai dasar.
    Dicari lewat marjin: HPP = 7500 x (1 - marjin)."""
    lo_m, hi_m = 0.0, MARGIN  # marjin 0 -> HPP 7500 (NPV<0); marjin dasar -> NPV>0
    for _ in range(80):
        mid = (lo_m + hi_m) / 2
        v, _ = npv_a(margin=mid)
        if v > 0:
            hi_m = mid  # NPV positif: akar di bawah mid
        else:
            lo_m = mid  # NPV negatif: akar di atas mid
    be_margin = (lo_m + hi_m) / 2
    return PRICE_BASE * (1 - be_margin), be_margin

be_vol = breakeven_volume()
be_price = breakeven_price()
be_hpp, be_margin = breakeven_hpp()
# NPV per harga (volume dasar 60 jt) + skenario downside (v6, HPP tetap)
npv_per_price = {p: round(npv_a(price=p)[0], 1)
                 for p in [5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000]}
downside = {
    "harga_-20%_vol_-30%": round(npv_a(price=6000, vol_y1=42_000_000)[0], 1),
    "vol_-50%": round(npv_a(vol_y1=30_000_000)[0], 1),
    "harga_-20%_saja": round(npv_a(price=6000)[0], 1),
    "harga_-20%_vol_-50%": round(npv_a(price=6000, vol_y1=30_000_000)[0], 1),
    "harga_-10%_vol_-20%": round(npv_a(price=6750, vol_y1=48_000_000)[0], 1),
    "marjin_-10poin": round(npv_a(margin=0.28)[0], 1),
    "marjin_-10poin_vol_-30%": round(npv_a(margin=0.28, vol_y1=42_000_000)[0], 1),
    "triple_harga_-20%_vol_-30%_marjin_-5poin": round(
        npv_a(price=6000, vol_y1=42_000_000, margin=0.33)[0], 1),
    "kanibalisasi_40%": round(npv_a(cannib=0.40)[0], 1),
}

# ---------------------------------------------------------------- risiko (skor P x I 1-5; dampak dibenarkan delta NPV tornado)
#   Dampak diukur terhadap NPV A base Rp miliar: I=5 bila delta > 400; I=4 bila
#   150-400; I=3 bila 50-150; I=2 bila < 50. Probabilitas dari bukti riset §3.
risks = [
    {"id": "R1", "nama": "Kanibalisasi produk massal sendiri lebih besar dari model",
     "P": 3, "I": 2, "alasan": f"Kanibalisasi +10 poin hanya memotong NPV Rp {abs(tornado['Kanibalisasi +-10 poin'][0] - npvA):.0f} miliar (tornado)",
     "mitigasi": "Posisikan Lestari Sehat di kanal modern + kemasan berbeda; pantau pangsa massal per kuartal, hentikan promo silang bila kanibalisasi > 20%.",
     "residual_P": 2, "residual_I": 2},
    {"id": "R2", "nama": "Harga gandum / minyak sawit naik, marjin premium tergerus",
     "P": 4, "I": 3, "alasan": f"Marjin -5 poin memotong NPV Rp {abs(tornado['Marjin +-5 poin'][0] - npvA):.0f} miliar (tornado); harga komoditas bergejolak",
     "mitigasi": "Kontrak forward 12 bulan untuk gandum + minyak; diversifikasi 2 pemasok; efisiensi resep tanpa mengubah klaim.",
     "residual_P": 3, "residual_I": 2},
    {"id": "R3", "nama": "Daya beli turun, downgrading berlanjut, volume premium tidak tercapai",
     "P": 4, "I": 4, "alasan": f"Volume -30% memotong NPV Rp {abs(tornado['Volume tahun-1 +-30%'][0] - npvA):.0f} miliar (tornado); konsumsi per kapita -3,4% dan kelas menengah menyusut (R7-R9)",
     "mitigasi": "Peluncuran bertahap (pilot Jabodetabek 3 bulan); kemasan kecil harga masuk; hentikan ekspansi bila penjualan pilot < 70% target.",
     "residual_P": 3, "residual_I": 3},
    {"id": "R4", "nama": "Pemain besar (Indofood / Wings) masuk segmen sehat dengan skala distribusi",
     "P": 3, "I": 5, "alasan": "Indofood CBP menjual mie instan Rp 50,44 triliun (2023, R11); masuknya raksasa bisa memangkas ramp volume hingga separuh",
     "mitigasi": "Kecepatan ke pasar 12 bulan + penempatan eksklusif di modern trade; diferensiasi rasa dan klaim yang teruji lab.",
     "residual_P": 3, "residual_I": 4},
    {"id": "R5", "nama": 'Klaim "sehat" dipertanyakan regulator / konsumen',
     "P": 2, "I": 4, "alasan": "Klaim kesehatan diawasi BPOM; perbaikan label + reformulasi mahal dan merusak kepercayaan",
     "mitigasi": "Klaim sesuai aturan BPOM, uji lab independen sebelum luncur; tanpa klaim medis; siapkan dana relabel Rp 5 miliar.",
     "residual_P": 1, "residual_I": 3},
]

# ---------------------------------------------------------------- output
def rp(x):
    return "Rp %.0f miliar" % x

print("=== MODEL FINANSIAL MIELESTARI (FIKTIF) ===")
print("Opsi A (build, invest Rp 180 miliar):  NPV = %s" % rp(npvA))
print("  Arus kas tahun 1-5 (Rp miliar):", ["%.1f" % c for c in cfA])
print("  Payback: %.1f tahun" % pbA)
print("Opsi B (defend, invest Rp 60 miliar): NPV = %s" % rp(npvB))
print("Opsi C (partner, invest Rp 90 miliar): NPV = %s" % rp(npvC))
print("Volume tahun-5 opsi A: %.1f juta bungkus (kapasitas sisa %.0f juta)" % (vol_y5 / 1e6, spare_capacity / 1e6))
print("Pangsa volume tahun-1 vs pasar: %.2f%% dari 14,54 miliar porsi" % vol_share_y1)
print("Jangkar ukuran pasar: 14,54 miliar x Rp 2.000 = Rp %.2f triliun" % market_anchor)
print("Break-even volume tahun-1 (NPV=0): %.1f juta bungkus" % be_vol)
print("Break-even harga (NPV=0, HPP tetap Rp 4.650): Rp %.0f" % be_price)
print("Break-even HPP (NPV=0, harga dasar): Rp %.0f (marjin %.1f%%)" % (be_hpp, be_margin * 100))
print("NPV per harga (60 jt):", {k: round(v, 1) for k, v in npv_per_price.items()})
print("Downside v6:", downside)
print()
print("=== TORNADO (NPV Rp miliar) ===")
for k, (lo, hi) in sorted(tornado.items(), key=lambda kv: kv[1][1] - kv[1][0], reverse=True):
    print("  %-28s rendah %8.0f | dasar %8.0f | tinggi %8.0f | rentang %8.0f" % (k, lo, npvA, hi, hi - lo))
print()
print("=== MONTE CARLO (10.000 iterasi, segitiga) ===")
print("  P(NPV>0) = %.2f%% (%d/%d)" % (p_pos * 100, int(round(p_pos * N)), N))
print("  P10 = %s | P50 = %s | P90 = %s | min = %s | maks = %s" % (rp(p10), rp(p50), rp(p90), rp(mc_min), rp(mc_max)))
print()
print("=== RISIKO (P x I) ===")
for r in risks:
    print("  %s %s: P=%d I=%d skor=%d -> residual P=%d I=%d skor=%d" % (
        r["id"], r["nama"], r["P"], r["I"], r["P"] * r["I"],
        r["residual_P"], r["residual_I"], r["residual_P"] * r["residual_I"]))

out = {
    "npv": {"A": round(npvA, 1), "B": round(npvB, 1), "C": round(npvC, 1)},
    "cf_A": [round(c, 1) for c in cfA],
    "cf_B": [round(c, 1) for c in cfB],
    "cf_C": [round(c, 1) for c in cfC],
    "payback_A": round(pbA, 2),
    "tornado": {k: [round(lo, 1), round(hi, 1)] for k, (lo, hi) in tornado.items()},
    "tornado_base": round(npvA, 1),
    "mc": {"p_pos": round(p_pos, 4), "p10": round(p10, 1), "p50": round(p50, 1),
           "p90": round(p90, 1), "min": round(mc_min, 1), "max": round(mc_max, 1),
           "n": N},
    "breakeven_vol_m": round(be_vol, 1),
    "breakeven_price_rp": round(be_price),
    "breakeven_hpp_rp": round(be_hpp),
    "breakeven_margin_pct": round(be_margin * 100, 1),
    "hpp_pack_rp": HPP_PACK,
    "npv_per_price": {str(k): v for k, v in npv_per_price.items()},
    "downside": downside,
    "vol_y5_m": round(vol_y5 / 1e6, 1),
    "spare_capacity_m": round(spare_capacity / 1e6, 0),
    "vol_share_y1_pct": round(vol_share_y1, 2),
    "market_anchor_triliun": round(market_anchor, 2),
    "risks": risks,
}
with open("mielestari-model-output.json", "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print()
print("JSON tersimpan: mielestari-model-output.json")
