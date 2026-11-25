#!/usr/bin/env python3
"""Angka turunan v4 dari model v1 (input sama). Semua angka FIKTIF, asumsi dinyatakan.
Sumber: mielestari-model.py + mielestari-model-output.json + mielestari-v2-derived.py.
Menulis: mielestari-v4-derived.json (dipakai build v4 + changelog).
"""
import json, sys
sys.path.insert(0, '.')
import numpy as np

with open('mielestari-model-output.json') as f:
    M = json.load(f)
with open('mielestari-v2-derived.json') as f:
    D = json.load(f)

PRICE, VOL_Y1, GROWTH, MARGIN = 7500, 60_000_000, 0.25, 0.38
MKT_Y1, MKT_LATER, CANNIB, INVEST_A, DISC = 45.0, 25.0, 0.15, 180.0, 0.12
MASSAL_RP = 660.0

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

base, cfA = npv_a()
assert abs(base - M['npv']['A']) < 0.5

# --- S3: omzet Lestari Sehat (Rp miliar) dari model: vol_t x Rp 7.500
rev = {}
for t in range(1, 6):
    vol = VOL_Y1 * (1 + GROWTH) ** (t - 1)
    rev[t] = {'vol_jt': round(vol / 1e6, 1), 'omzet': round(vol * PRICE / 1e9, 1),
              'share_pct': round(vol / 14.54e9 * 100, 2)}
print('omzet:', rev)
assert rev[1]['omzet'] == 450.0 and rev[3]['omzet'] == 703.1
assert rev[3]['vol_jt'] == 93.8 and rev[3]['share_pct'] == 0.64
# laba kotor tahun-3 (dari volume eksak, bukan yang dibulatkan)
rev[3]['gross'] = round(VOL_Y1 * (1 + GROWTH) ** 2 * PRICE * MARGIN / 1e9, 1)
assert rev[3]['gross'] == 267.2

# --- S6: uji bobot MAUT. Skor (A5): A=[5,3,4,3,3] B=[2,4,5,4,4] C=[2,5,3,3,5]
# urutan bobot: NPV, Kecepatan, Kapabilitas, Risiko, Fleksibilitas
scores = {'A': [5, 3, 4, 3, 3], 'B': [2, 4, 5, 4, 4], 'C': [2, 5, 3, 3, 5]}
def maut(w):
    return {k: round(sum(s * wi for s, wi in zip(v, w)), 2) for k, v in scores.items()}
base_w = [0.30, 0.15, 0.20, 0.20, 0.15]
print('MAUT base:', maut(base_w))
assert maut(base_w) == {'A': 3.8, 'B': 3.6, 'C': 3.3}
# A unggul selama bobot NPV > 25% (selisih A-B = 4*wNPV - 1)
alt_w = [0.20, 0.25, 0.20, 0.20, 0.15]  # NPV 20%, kecepatan 25%, sisanya tetap
print('MAUT NPV20%:', maut(alt_w))
assert maut(alt_w) == {'A': 3.6, 'B': 3.8, 'C': 3.6}
# ambang: wNPV=0.25 -> seri
tie_w = [0.25, 0.15, 0.20, 0.20, 0.20]
assert maut(tie_w)['A'] == maut(tie_w)['B'] == 3.7, maut(tie_w)

# --- S10/A7: regenerasi Monte Carlo (seed sama 20261125, rumus sama dengan model)
rng = np.random.default_rng(20261125)
N = 10_000
p = rng.triangular(6000, 7500, 9000, N)
v = rng.triangular(42_000_000, 60_000_000, 78_000_000, N)
m = rng.triangular(0.33, 0.38, 0.43, N)
npvs = np.full(N, -INVEST_A)
for t in range(1, 6):
    vol_t = v * (1.0 + GROWTH) ** (t - 1)
    gross = vol_t * p * m / 1e9
    mkt = MKT_Y1 if t == 1 else MKT_LATER
    cann = CANNIB * vol_t * MASSAL_RP / 1e9
    npvs += (gross - mkt - cann) / (1 + DISC) ** t
p10, p50, p90 = [float(x) for x in np.percentile(npvs, [10, 50, 90])]
assert abs(p10 - M['mc']['p10']) < 0.2 and abs(p50 - M['mc']['p50']) < 0.2
assert abs(p90 - M['mc']['p90']) < 0.2 and abs(float(npvs.min()) - M['mc']['min']) < 0.2
assert float(np.mean(npvs > 0)) == 1.0
# histogram: 30 bin, rentang 0-1200 (agar garis NPV=0 terlihat)
counts, edges = np.histogram(npvs, bins=30, range=(0, 1200))
print('hist bins:', counts.tolist())
print('P10/P50/P90:', round(p10, 1), round(p50, 1), round(p90, 1),
      'min/max:', round(float(npvs.min()), 1), round(float(npvs.max()), 1))

out = {
    'omzet': rev,
    'maut_base': maut(base_w),
    'maut_npv20': maut(alt_w),
    'maut_tie_npv25': maut(tie_w),
    'hist': {'counts': [int(c) for c in counts], 'edges': [round(float(e), 1) for e in edges],
             'p10': round(p10, 1), 'p50': round(p50, 1), 'p90': round(p90, 1),
             'min': round(float(npvs.min()), 1), 'max': round(float(npvs.max()), 1),
             'n': N, 'seed': 20261125},
}
with open('mielestari-v4-derived.json', 'w') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print('OK - mielestari-v4-derived.json tersimpan')
