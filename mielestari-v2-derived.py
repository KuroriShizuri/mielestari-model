#!/usr/bin/env python3
"""Angka turunan v2 dari model v1 (input sama, tanpa hitung ulang NPV dasar).
Sumber: mielestari-model-output.json + mielestari-model.py (fungsi npv_a).
Semua angka turunan FIKTIF, asumsi dinyatakan di deck.
"""
import json
import sys
sys.path.insert(0, ".")
import numpy as np

# import fungsi model tanpa menjalankan ulang output-nya: salin rumus inti
PRICE, VOL_Y1, GROWTH, MARGIN = 7500, 60_000_000, 0.25, 0.38
MKT_Y1, MKT_LATER, CANNIB, INVEST_A, DISC = 45.0, 25.0, 0.15, 180.0, 0.12
MASSAL_RP = 660.0  # Rp/bungkus marjin massal (3000 x 22%)

with open("mielestari-model-output.json") as f:
    M = json.load(f)

def npv_a(price=PRICE, vol_y1=VOL_Y1, margin=MARGIN, mkt_y1=MKT_Y1,
          cannib=CANNIB, invest=INVEST_A, delay=0):
    npv = -invest / (1 + DISC) ** delay
    cfs = []
    for t in range(1, 6):
        vol = vol_y1 * (1 + GROWTH) ** (t - 1)
        gross = vol * price * margin / 1e9
        mkt = mkt_y1 if t == 1 else MKT_LATER
        cann = cannib * vol * MASSAL_RP / 1e9
        cf = gross - mkt - cann
        cfs.append(cf)
        npv += cf / (1 + DISC) ** (t + delay)
    return npv, cfs

# --- sanity: NPV dasar cocok dengan JSON v1
base, cfA = npv_a()
assert abs(base - M["npv"]["A"]) < 0.5, (base, M["npv"]["A"])
assert abs(cfA[0] - M["cf_A"][0]) < 0.1

# --- A9: build-up kuartalan. Ramp thn-1: Q1 6, Q2 12, Q3 18, Q4 24 jt (pilot Jabodetabek).
#     Pemasaran thn-1 dibagi 15/12/10/8 = 45. Tahun 2-3: volume tumbuh 25%/thn, rata per kuartal.
q_vol = {1: [6, 12, 18, 24],
         2: [18.75] * 4,
         3: [23.4375] * 4}
q_mkt = {1: [15, 12, 10, 8], 2: [6.25] * 4, 3: [6.25] * 4}
quarters = []
for y in (1, 2, 3):
    for q in range(4):
        vol = q_vol[y][q]  # jt bungkus
        rev = vol * 1e6 * PRICE / 1e9
        gross = rev * MARGIN
        mkt = q_mkt[y][q]
        cann = CANNIB * vol * 1e6 * MASSAL_RP / 1e9
        cf = gross - mkt - cann
        quarters.append({"y": y, "q": q + 1, "vol": vol, "rev": round(rev, 1),
                         "gross": round(gross, 2), "mkt": mkt,
                         "cann": round(cann, 2), "cf": round(cf, 2)})
# cek konsistensi tahunan vs model
for y in (1, 2, 3):
    qs = [x for x in quarters if x["y"] == y]
    assert abs(sum(x["vol"] for x in qs) - VOL_Y1 * 1.25 ** (y - 1) / 1e6) < 0.01
    assert abs(sum(x["cf"] for x in qs) - cfA[y - 1]) < 0.6, (y, sum(x["cf"] for x in qs), cfA[y - 1])

# --- A16: grid sensitivitas dua arah (harga x volume)
prices = [6000, 6750, 7500, 8250, 9000]
vols = [42, 51, 60, 69, 78]  # jt
grid = [[round(npv_a(price=p, vol_y1=v * 1e6)[0]) for v in vols] for p in prices]
assert grid[2][2] == round(base)

# --- A17: skenario downside
scen = {}
scen["Harga -20% + volume -30%"] = round(npv_a(price=6000, vol_y1=42e6)[0])
scen["Volume -50%"] = round(npv_a(vol_y1=30e6)[0])
scen["Marjin -10 poin (28%)"] = round(npv_a(margin=0.28)[0])
scen["Kanibalisasi 40%"] = round(npv_a(cannib=0.40)[0])
scen["Peluncuran tertunda 1 tahun"] = round(npv_a(delay=1)[0])
scen["Harga -20% saja"] = round(npv_a(price=6000)[0])

# --- A14: unit economics per bungkus (Rp)
unit = {"harga": 7500, "hpp": 7500 * (1 - MARGIN), "laba_kotor": 7500 * MARGIN,
        "pemasaran_thn1": 45e9 / 60e6, "kanibalisasi": 0.15 * 660,
        "massal_harga": 3000, "massal_laba": 660}
unit["kontribusi_bersih_thn1"] = unit["laba_kotor"] - unit["pemasaran_thn1"] - unit["kanibalisasi"]

# --- A15: kapasitas & utilisasi
cap = []
used = 1_200_000_000 * 0.78
for y in range(1, 6):
    v = VOL_Y1 * 1.25 ** (y - 1)
    used_y = 936_000_000 + v
    cap.append({"y": y, "vol_premium_jt": round(v / 1e6, 1),
                "utilisasi_pct": round(used_y / 1_200_000_000 * 100, 1)})

# --- A10: arus kas per tahun A/B/C + kumulatif
cf = {"A": M["cf_A"], "B": M["cf_B"], "C": M["cf_C"]}
cum = {k: [round(sum(v[:i + 1]), 1) for i in range(5)] for k, v in cf.items()}
inv = {"A": 180.0, "B": 60.0, "C": 90.0}
npv_cum = {}
for k, v in cf.items():
    row = []
    for i in range(5):
        row.append(round(-inv[k] + sum(v[j] / 1.12 ** (j + 1) for j in range(i + 1)), 1))
    npv_cum[k] = row

# --- A18: kontribusi NPV per tahun (PV arus kas) opsi A
pv_cf = [round(c / 1.12 ** (t + 1), 1) for t, c in enumerate(cfA)]

out = {"quarters": quarters, "grid_prices": prices, "grid_vols": vols, "grid": grid,
       "scenarios": scen, "unit": unit, "capacity": cap, "cf": cf, "cum_cf": cum,
       "npv_cum": npv_cum, "pv_cf_A": pv_cf, "base_npv_A": round(base, 1)}
with open("mielestari-v2-derived.json", "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("quarters Y1 CF sum:", round(sum(x["cf"] for x in quarters if x["y"] == 1), 1), "vs model", cfA[0])
print("grid (harga x volume):")
for p, row in zip(prices, grid):
    print("  ", p, row)
print("scenarios:", scen)
print("unit:", {k: round(v, 1) for k, v in unit.items()})
print("capacity:", cap)
print("pv_cf_A:", pv_cf, "sum+(-180) =", round(sum(pv_cf) - 180, 1))
print("OK - mielestari-v2-derived.json tersimpan")
