#!/usr/bin/env python3
"""Angka turunan v10 dari model v8 (HPP TETAP Rp 4.650/bungkus) + analisis v10.
Sumber: mielestari-model.py (v8) + mielestari-model-output.json.
Menulis: mielestari-v10-derived.json + canonical-numbers-v10.json (dipakai build v10
+ uji otomatis angka deck vs model).
BARU di v10: rumus umum silang B>A (t_premium > 22,5% + 0,17 x t_massal;
KOREKSI atas rumus Sonnet R7 "24,2% + 0,17x" yang double-count - 24,2% sudah
termasuk t_massal 10%) + bantalan NPV Gerbang 0 (syarat kelima Lanjut:
NPV pada kombinasi terukur pilot >= Rp 100 miliar; pada sudut keempat ambang
NPV hanya +7,7).
Semua angka FIKTIF, asumsi dinyatakan.
"""
import json
import sys

import numpy as np

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('mmodel', 'mielestari-model.py')
_mmodel = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mmodel)

with open('mielestari-model-output.json') as f:
    M = json.load(f)

PRICE, VOL_Y1, GROWTH, PRICE_BASE = 7500, 60_000_000, 0.25, 7500
MARGIN = 0.38
HPP = 4650  # Rp/bungkus, TETAP (v6)
MKT_Y1, MKT_LATER, CANNIB, INVEST_A, DISC = 45.0, 25.0, 0.15, 180.0, 0.12
MASSAL_RP = 660.0


def npv_a(price=PRICE, vol_y1=VOL_Y1, margin=MARGIN, mkt_y1=MKT_Y1,
          cannib=CANNIB, invest=INVEST_A):
    """Replika model v6: HPP tetap = PRICE_BASE*(1-margin); laba kotor = harga - HPP."""
    hpp = PRICE_BASE * (1 - margin)
    gp_pack = price - hpp
    npv = -invest
    cfs = []
    for t in range(1, 6):
        vol = vol_y1 * (1 + GROWTH) ** (t - 1)
        gross = vol * gp_pack / 1e9
        mkt = mkt_y1 if t == 1 else MKT_LATER
        cann = cannib * vol * MASSAL_RP / 1e9
        cf = gross - mkt - cann
        cfs.append(cf)
        npv += cf / (1 + DISC) ** t
    return npv, cfs


base, cfA = npv_a()
assert abs(base - M['npv']['A']) < 0.5, base
assert abs(base - 641) < 1, base  # angka dasar TIDAK berubah di v6
print('base NPV A:', round(base, 1), '| CF:', [round(c, 1) for c in cfA])

def rhu1(x):
    """Pembulatan tampil deck: nilai -> 1 desimal -> setengah ke atas (half-up).
    Dipakai KONSISTEN di semua angka bulat deck, supaya angka yang sama tidak
    pernah tampil 134 di satu tempat dan 135 di tempat lain."""
    import math
    return int(math.floor(round(float(x), 1) + 0.5))
npv_price = {}
for p in [5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000]:
    npv_price[p] = round(npv_a(price=p)[0], 1)
print('NPV per harga (60 jt):', npv_price)
assert npv_price[6000] == 134.5, npv_price[6000]
assert npv_price[7500] == 641.0 and npv_price[9000] == 1147.5
assert npv_price[5500] < 0  # harga 5.500 sudah di bawah titik impas

# --- 2. Harga titik impas (NPV=0), pencarian biner
lo, hi = 0.0, PRICE
for _ in range(80):
    mid = (lo + hi) / 2
    if npv_a(price=mid)[0] > 0:
        hi = mid
    else:
        lo = mid
be_price = (lo + hi) / 2
print('break-even price: Rp %.0f' % be_price)
assert abs(be_price - M['breakeven_price_rp']) < 2, be_price
assert be_price > 3000, 'titik impas harus DI ATAS harga massal (v6 fix)'
# HPP impas (marjin impas 12,7%): HPP = 7500*(1-0,127) = 6548
be_hpp = M['breakeven_hpp_rp']
print('break-even HPP: Rp', be_hpp, '| marjin impas:', M['breakeven_margin_pct'], '%')
assert abs(be_hpp - 6548) < 5

# --- 3. Grid 6x5 harga x volume (baris baru Rp 5.500 supaya garis impas memotong grid)
prices_g = [5500, 6000, 6750, 7500, 8250, 9000]
vols_g = [42_000_000, 51_000_000, 60_000_000, 69_000_000, 78_000_000]
grid_exact = [[npv_a(price=p, vol_y1=v)[0] for v in vols_g] for p in prices_g]
grid = [[rhu1(x) for x in row] for row in grid_exact]
print('grid 6x5:')
for p, row in zip(prices_g, grid):
    print('  ', p, row)
assert grid[0] == [-110, -72, -34, 4, 42], grid[0]
assert grid[1] == [8, 71, 135, 198, 261], grid[1]
assert grid[2] == [185, 286, 388, 489, 590], grid[2]
assert grid[3] == [362, 502, 641, 780, 920], grid[3]
assert grid[4] == [540, 717, 894, 1072, 1249], grid[4]
assert grid[5] == [717, 932, 1148, 1363, 1578], grid[5]
neg = sum(1 for r in grid for v in r if v < 0)
assert neg == 3, neg  # tepat 3 sel merah di baris 5.500
# rata-rata baris dihitung dari nilai eksak (NPV linear terhadap volume, jadi
# = NPV pada volume rata-rata 60 jt = NPV per harga baris itu)
row_avg = {str(p): rhu1(sum(row) / len(row)) for p, row in zip(prices_g, grid_exact)}
print('row averages:', row_avg)
assert row_avg['5500'] == -34 and row_avg['7500'] == 641 and row_avg['9000'] == 1148
assert row_avg['6000'] == rhu1(npv_price[6000]) == 135  # konsisten dgn strip S9
assert row_avg['8250'] == grid[4][2] == 894

# --- 4. Skenario downside (dari model; bandingkan dengan M['downside'])
ds = M['downside']
print('downside:', ds)
assert ds['harga_-20%_vol_-30%'] == 7.7
assert ds['harga_-20%_vol_-50%'] == -76.8
assert ds['triple_harga_-20%_vol_-30%_marjin_-5poin'] == -80.9
assert ds['vol_-50%'] == 176.5 and ds['marjin_-10poin'] == 387.7

# --- 5. MAUT: skor vs bobot NPV (TIDAK berubah di v6 — tidak bergantung pada HPP)
scores = {'A': [5, 3, 4, 3, 3], 'B': [2, 4, 5, 4, 4], 'C': [2, 5, 3, 3, 5]}
base_other = [0.15, 0.20, 0.20, 0.15]


def maut_at(w_npv):
    others = [(1 - w_npv) * o / sum(base_other) for o in base_other]
    w = [w_npv] + others
    return {k: round(sum(s * wi for s, wi in zip(v, w)), 2) for k, v in scores.items()}


curve = {}
for w in [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]:
    curve[int(w * 100)] = maut_at(w)
assert maut_at(0.30) == {'A': 3.8, 'B': 3.6, 'C': 3.3}
assert maut_at(0.25)['A'] == maut_at(0.25)['B'] == 3.71

# --- 6. Sanity chip S3 (tidak berubah) + omzet thn-3
s1 = 703.1 / 29100 * 100
s2 = 703.1 / 102700 * 100
assert abs(s1 - 2.4) < 0.05 and abs(s2 - 0.7) < 0.05
rev3_vol = VOL_Y1 * (1 + GROWTH) ** 2
rev3 = rev3_vol * PRICE / 1e9
assert abs(rev3 - 703.1) < 0.1
# pembulatan 703 vs 704: 93,8 jt x 7.500 = 703,5 -> deck memakai 703 di semua tempat
assert abs(rev3_vol / 1e6 - 93.8) < 0.05
print('rev thn-3: %.1f (vol %.1f jt); 703,5 dibulatkan ke 703' % (rev3, rev3_vol / 1e6))

# --- 7. Monte Carlo v6 (regenerasi dengan seed sama; HPP tetap)
rng = np.random.default_rng(20261125)
N = 10_000
p = rng.triangular(6000, 7500, 9000, N)
v = rng.triangular(42_000_000, 60_000_000, 78_000_000, N)
m = rng.triangular(0.33, 0.38, 0.43, N)
npvs = np.full(N, -INVEST_A)
for t in range(1, 6):
    vol_t = v * (1.0 + GROWTH) ** (t - 1)
    gross = vol_t * (p - PRICE_BASE * (1 - m)) / 1e9
    mkt = MKT_Y1 if t == 1 else MKT_LATER
    cann = CANNIB * vol_t * MASSAL_RP / 1e9
    npvs += (gross - mkt - cann) / (1 + DISC) ** t
mc = M['mc']
p10, p50, p90 = [float(x) for x in np.percentile(npvs, [10, 50, 90])]
print('MC v6: P(>0)=%.4f P10=%.1f P50=%.1f P90=%.1f min=%.1f max=%.1f'
      % (float(np.mean(npvs > 0)), p10, p50, p90, float(npvs.min()), float(npvs.max())))
assert abs(p10 - mc['p10']) < 1.0 and abs(p50 - mc['p50']) < 1.0 and abs(p90 - mc['p90']) < 1.0
assert abs(float(np.mean(npvs > 0)) - mc['p_pos']) < 0.001
# histogram: 24 bin, rentang 0..1600 (min ~10, maks ~1520)
counts, edges = np.histogram(npvs, bins=24, range=(0, 1600))
print('hist bins:', counts.tolist())
print('hist edges:', [round(e) for e in edges[:5]], '...', round(edges[-1]))
assert counts.sum() == N
assert int(counts.max()) > 500  # puncak distribusi jelas

# --- 8. Gerbang 0: volume setara 60% + NPV-nya
gate_vol_jt = 0.60 * 60  # 36 jt bungkus
gate_npv = round(npv_a(vol_y1=gate_vol_jt * 1_000_000)[0], 1)
print('Gate 0: 60%% dari rencana = %.0f jt -> NPV Rp %.1f miliar (impas 18,6 jt)'
      % (gate_vol_jt, gate_npv))
assert gate_npv > 0 and gate_npv < 641
assert abs(gate_npv - 269) < 2, gate_npv
gate_margin_pct = round((gate_vol_jt - 18.6) / 18.6 * 100)  # 94% di atas impas
print('volume 36 jt = %d%% di atas titik impas 18,6 jt' % gate_margin_pct)

# --- 9. Unit economics per bungkus (A14, harga dasar; HPP tetap)
# tahun-1: pemasaran 45.000/60 jt = 750; thn 2-5: 25.000/vol_t
ue = []
for t in range(1, 6):
    vol_t = VOL_Y1 * (1 + GROWTH) ** (t - 1)
    mkt_pack = (MKT_Y1 if t == 1 else MKT_LATER) * 1e9 / vol_t
    contrib = (PRICE - HPP) - mkt_pack - 0.15 * MASSAL_RP
    ue.append({'tahun': t, 'pemasaran_rp': round(mkt_pack),
               'kontribusi_rp': round(contrib)})
print('unit economics:', ue)
assert ue[0] == {'tahun': 1, 'pemasaran_rp': 750, 'kontribusi_rp': 2001}
assert ue[1]['kontribusi_rp'] == 2418 and ue[4]['kontribusi_rp'] == 2580

# --- 10. Tornado v6 (dari model; harga kini #1)
t = M['tornado']
print('tornado:', t)
assert abs(t['Harga jual +-20%'][0] - 134.5) < 0.6 and abs(t['Harga jual +-20%'][1] - 1147.5) < 0.6
assert abs(t['Volume tahun-1 +-30%'][0] - 362) < 1 and abs(t['Volume tahun-1 +-30%'][1] - 920) < 1
assert abs(t['Marjin +-5 poin'][0] - 514) < 1 and abs(t['Marjin +-5 poin'][1] - 768) < 1
assert abs(t['Kanibalisasi +-10 poin'][0] - 619) < 1 and abs(t['Pemasaran tahun-1 +-25%'][0] - 631) < 1

# --- 11. Sensitivitas margin dagang ke KETIGA opsi (v8; model v8) ---
# (tidak berubah di v9; HPP tetap: premium 4.650, massal 2.340, mitra 4.900)
# Brief diam soal margin dagang (distributor + ritel): model memakai Rp 7.500
# sebagai pendapatan per bungkus. Bila Rp 7.500 ternyata harga konsumen, margin
# dagang t memotong pendapatan SEMUA opsi; HPP TETAP (premium 4.650, massal
# 2.340, mitra 4.900) — bukan marjin % dari harga (itu bug v1-v5).
def rhu1(x):
    """Half-up ke bilangan bulat (aturan pembulatan deck sejak v6)."""
    import math
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))

trade = {}
for tm in [0, 0.15, 0.20, 0.225, 0.25, 0.30]:
    net_a = PRICE * (1 - tm)
    trade[str(int(tm * 1000))] = {
        't_pct': tm * 100,
        'net_a_rp': round(net_a),
        'npv_A': round(npv_a(price=net_a)[0], 1),
        'npv_B': round(_mmodel.npv_b_t(tm)[0], 1),
        'npv_C': round(_mmodel.npv_c_t(tm)[0], 1)}
print('trade margin A/B/C:',
      {k: (v['npv_A'], v['npv_B'], v['npv_C']) for k, v in trade.items()})
assert abs(trade['0']['npv_A'] - 641.0) < 0.6
assert abs(trade['0']['npv_B'] - M['npv']['B']) < 0.6
assert abs(trade['0']['npv_C'] - M['npv']['C']) < 0.6
assert abs(trade['150']['npv_A'] - 261.1) < 0.6
assert abs(trade['150']['npv_B'] - 6.3) < 0.6
assert abs(trade['150']['npv_C'] + 25.1) < 0.6
assert abs(trade['200']['npv_A'] - 134.5) < 0.6
assert abs(trade['200']['npv_B'] + 15.3) < 0.6
assert abs(trade['200']['npv_C'] + 46.7) < 0.6
assert abs(trade['225']['npv_A'] - M['npv']['B']) < 0.6
assert abs(trade['225']['npv_B'] + 26.1) < 0.6
assert abs(trade['225']['npv_C'] + 57.6) < 0.6
assert abs(trade['250']['npv_A'] - 7.8) < 0.6
assert abs(trade['250']['npv_B'] + 36.9) < 0.6
assert abs(trade['250']['npv_C'] + 68.4) < 0.6
assert abs(trade['300']['npv_A'] + 118.8) < 0.6
assert abs(trade['300']['npv_B'] + 58.6) < 0.6
assert abs(trade['300']['npv_C'] + 90.0) < 0.6
# titik nol tiap opsi (pencarian biner) + silang A=B (t ke semua opsi)
def _zero(f):
    lo, hi = 0.0, 0.5
    for _ in range(80):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
zero_A = _zero(lambda t: npv_a(price=PRICE * (1 - t))[0])
zero_B = _zero(lambda t: _mmodel.npv_b_t(t)[0])
zero_C = _zero(lambda t: _mmodel.npv_c_t(t)[0])
lo, hi = 0.0, 0.5
for _ in range(80):
    mid = (lo + hi) / 2
    if npv_a(price=PRICE * (1 - mid))[0] - _mmodel.npv_b_t(mid)[0] > 0:
        lo = mid
    else:
        hi = mid
crossover_ab = (lo + hi) / 2
cross_npv = npv_a(price=PRICE * (1 - crossover_ab))[0]
print('nol: A t=%.2f%% | B t=%.2f%% | C t=%.2f%% | silang A=B t=%.2f%% (NPV %.1f di sana)'
      % (zero_A * 100, zero_B * 100, zero_C * 100, crossover_ab * 100, cross_npv))
assert abs(zero_A - 0.253) < 0.002
assert abs(zero_B - 0.165) < 0.002
assert abs(zero_C - 0.092) < 0.002
assert abs(crossover_ab - 0.271) < 0.002
assert cross_npv < 0  # silang terjadi saat keduanya negatif -> tidak bermakna
# bilangan bulat deck (half-up dari 1 desimal)
trade_int = {k: {'A': int(rhu1(v['npv_A'])), 'B': int(rhu1(v['npv_B'])),
                 'C': int(rhu1(v['npv_C']))} for k, v in trade.items()}
print('trade bulat:', trade_int)
assert trade_int['150'] == {'A': 261, 'B': 6, 'C': -25}
assert trade_int['200'] == {'A': 135, 'B': -15, 'C': -47}
assert trade_int['225'] == {'A': 71, 'B': -26, 'C': -58}
assert trade_int['250'] == {'A': 8, 'B': -37, 'C': -68}
assert trade_int['300'] == {'A': -119, 'B': -59, 'C': -90}

# --- 12. Monte Carlo: P1 (segitiga) + P(negatif) sebaran seragam (v7) ---
mc_p1 = float(np.percentile(npvs, 1))
print('MC P1 (segitiga): %.1f | min %.1f' % (mc_p1, float(npvs.min())))
assert abs(mc_p1 - 157.2) < 1.0
rng_u = np.random.default_rng(20261125)
p_u = rng_u.uniform(6000, 9000, N)
v_u = rng_u.uniform(42_000_000, 78_000_000, N)
m_u = rng_u.uniform(0.33, 0.43, N)
npvs_u = np.full(N, -INVEST_A)
for tt in range(1, 6):
    vol_t = v_u * (1.0 + GROWTH) ** (tt - 1)
    gross = vol_t * (p_u - PRICE_BASE * (1 - m_u)) / 1e9
    mkt = MKT_Y1 if tt == 1 else MKT_LATER
    cann = CANNIB * vol_t * MASSAL_RP / 1e9
    npvs_u += (gross - mkt - cann) / (1 + DISC) ** tt
mc_uni_neg = float(np.mean(npvs_u < 0))
print('MC seragam: P(negatif)=%.4f (%d dari %d)' % (mc_uni_neg, int((npvs_u < 0).sum()), N))
assert abs(mc_uni_neg - 0.0026) < 0.001

# --- 13. Alasan ambang Gerbang 0 60% (v7; asumsi Tim Kurori) ---
be_vol_share = M['breakeven_vol_m'] / 60.0  # 18,6/60 = 31%
gate_ratio = be_vol_share / 0.50  # konversi niat->beli ~50%
print('impas volume = %.1f%% rencana; 31%% / 50%% = %.0f%% -> ambang 60%%'
      % (be_vol_share * 100, gate_ratio * 100))
assert abs(be_vol_share - 0.31) < 0.005
assert abs(gate_ratio - 0.62) < 0.01

# --- 14. BARU v9: baris kedua A30 + ambang gabungan Gerbang 0 ---
# Baris kedua menguji asumsi "margin dagang SAMA untuk ketiga opsi" (baris
# pertama A30): t premium bervariasi, t massal TETAP 10%. NPV B hanya
# bergantung pada t massal, jadi tetap +28,0 di semua baris; NPV A jatuh
# seperti baris pertama. Pada t premium 25%, B (28) sudah mengalahkan A (8).
npv_B_tmassal10 = round(_mmodel.npv_b_t(0.10)[0], 1)
row2 = {}
for tp in [0, 0.15, 0.20, 0.25, 0.30]:
    row2[str(int(tp * 1000))] = {
        't_prem_pct': tp * 100,
        't_massal_pct': 10,
        'npv_A': round(npv_a(price=PRICE * (1 - tp))[0], 1),
        'npv_B': npv_B_tmassal10}
print('baris kedua A30 (t_massal tetap 10%):',
      {k: (v['npv_A'], v['npv_B']) for k, v in row2.items()})
assert abs(npv_B_tmassal10 - 28.0) < 0.6
assert row2['0']['npv_A'] == 641.0 and row2['300']['npv_A'] == -118.8
assert row2['250']['npv_A'] < npv_B_tmassal10 < row2['200']['npv_A']
# silang A = B pada baris kedua (B tetap 28,0)
lo, hi = 0.0, 0.5
for _ in range(80):
    mid = (lo + hi) / 2
    if npv_a(price=PRICE * (1 - mid))[0] > npv_B_tmassal10:
        lo = mid
    else:
        hi = mid
row2_cross = (lo + hi) / 2
print('silang baris kedua A=B (B=28): t premium %.1f%%' % (row2_cross * 100))
assert abs(row2_cross - 0.242) < 0.003
row2_int = {k: {'A': int(rhu1(v['npv_A'])), 'B': int(rhu1(v['npv_B']))}
            for k, v in row2.items()}
assert row2_int['250'] == {'A': 8, 'B': 28}
assert row2_int['300'] == {'A': -119, 'B': 28}

# Ambang gabungan: NPV A >= 0 pada volume pilot (WTP 60% -> 36 jt;
# sell-through 70% -> 42 jt) memerlukan margin dagang MAKSIMUM yang lebih
# ketat dari 25,3% (yang berlaku di volume dasar 60 jt). Sonnet R6 menghitung
# 21,4% untuk 42 jt dari fit linier - model eksak: 20,4%. v9 memakai 20,4%.
def _zero_t_at_vol(vol):
    lo, hi = 0.0, 0.5
    for _ in range(80):
        mid = (lo + hi) / 2
        if npv_a(price=PRICE * (1 - mid), vol_y1=vol)[0] > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
comb_36 = _zero_t_at_vol(36_000_000)
comb_42 = _zero_t_at_vol(42_000_000)
print('ambang gabungan: vol 36 jt -> t < %.1f%% | vol 42 jt -> t < %.1f%%'
      % (comb_36 * 100, comb_42 * 100))
assert abs(comb_36 - 0.177) < 0.002
assert abs(comb_42 - 0.204) < 0.002
# bukti aturan gabungan: pada vol 36 jt, margin 20% ("Lanjut" bila dinilai
# sendiri) sudah NPV negatif - ambang harus hijau BERSAMAAN.
npv_36_t20 = round(npv_a(price=PRICE * (1 - 0.20), vol_y1=36_000_000)[0], 1)
npv_42_t20 = round(npv_a(price=PRICE * (1 - 0.20), vol_y1=42_000_000)[0], 1)
print('NPV vol 36 jt + t 20%%: %.1f | vol 42 jt + t 20%%: %.1f'
      % (npv_36_t20, npv_42_t20))
assert npv_36_t20 < 0 and npv_42_t20 > 0


# --- 15. BARU v10: rumus umum silang B > A (t_premium vs t_massal) ---
# Sonnet R7 mengusulkan "B > A bila t premium > 24,2% + 0,17 x t massal" -
# SALAH (double-count): 24,2% adalah silang PADA t_massal 10%, jadi sudah
# termasuk t_massal. Rumus benar dihitung dari model eksak: silang t_premium
# pada t_massal 0/10/20/30%, lalu fit linier t_p* = a + b * t_m.
def _cross_tp_for_tm(tm):
    npv_b = _mmodel.npv_b_t(tm)[0]
    lo, hi = 0.0, 0.5
    for _ in range(80):
        mid = (lo + hi) / 2
        if npv_a(price=PRICE * (1 - mid))[0] > npv_b:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, npv_b
cross_pts = {}
for tm in [0, 0.10, 0.20, 0.30]:
    tp, nb = _cross_tp_for_tm(tm)
    cross_pts[tm] = (round(tp * 100, 2), round(nb, 1))
print('silang B>A (t_premium* vs t_massal):', cross_pts)
assert abs(cross_pts[0][0] - 22.50) < 0.05
assert abs(cross_pts[0.10][0] - 24.21) < 0.05
assert abs(cross_pts[0.20][0] - 25.91) < 0.05
assert abs(cross_pts[0.30][0] - 27.62) < 0.05
assert cross_pts[0.10][1] == 28.0  # NPV B pada t_massal 10%
# fit linier (kuadrat terkecil) t_p* = a + b * t_m, keduanya dalam persen
xs = [tm * 100 for tm in cross_pts]
ys = [v[0] for v in cross_pts.values()]
n = len(xs)
mx, my = sum(xs) / n, sum(ys) / n
b_fit = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
a_fit = my - b_fit * mx
print('rumus umum: t_premium > %.2f%% + %.3f x t_massal' % (a_fit, b_fit))
assert abs(a_fit - 22.50) < 0.05
assert abs(b_fit - 0.171) < 0.002
# rumus Sonnet R7 ("24,2% + 0,17x") memberi 25,9% pada t_m 10% - SALAH 1,7 poin
assert abs((24.2 + 0.17 * 10) - cross_pts[0.10][0]) > 1.0

# --- 16. BARU v10: bantalan NPV Gerbang 0 (syarat kelima Lanjut) ---
# Pada sudut keempat ambang (volume 42 jt = sell-through 70%, margin 20%)
# NPV A hanya +7,7 - Rp 180 miliar tidak boleh dikomitmenkan untuk keuntungan
# nyaris nol. Syarat kelima: NPV pada kombinasi terukur pilot >= Rp 100 M.
# Mengetatkan ambang individual TIDAK jujur sebagai ambang: t < 14,8% pada
# 42 jt, atau volume >= 55,1 jt (sell-through 92%) pada t 20% - terlalu
# menuntut. Jadi syaratnya NPV kombinasi, bukan ambang individual baru.
npv_corner = round(npv_a(price=PRICE * (1 - 0.20), vol_y1=42_000_000)[0], 1)
print('NPV sudut (42 jt, t 20%%): %.1f' % npv_corner)
assert abs(npv_corner - 7.7) < 0.5
def _t_for_npv_at_vol(vol, target):
    lo, hi = 0.0, 0.5
    for _ in range(80):
        mid = (lo + hi) / 2
        if npv_a(price=PRICE * (1 - mid), vol_y1=vol)[0] > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
t_max_100_42 = _t_for_npv_at_vol(42_000_000, 100)
print('t maksimum agar NPV >= 100 pada vol 42 jt: %.1f%%' % (t_max_100_42 * 100))
assert abs(t_max_100_42 - 0.148) < 0.003
def _vol_for_npv_at_t(t, target):
    lo, hi = 10_000_000, 100_000_000
    for _ in range(80):
        mid = (lo + hi) / 2
        if npv_a(price=PRICE * (1 - t), vol_y1=mid)[0] > target:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2
vol_min_100_t20 = _vol_for_npv_at_t(0.20, 100)
print('volume minimum agar NPV >= 100 pada t 20%%: %.1f jt' % (vol_min_100_t20 / 1e6))
assert abs(vol_min_100_t20 / 1e6 - 55.1) < 0.5

out = {
    'npv_per_harga_60jt': {str(k): v for k, v in npv_price.items()},
    'breakeven_price_rp': round(be_price),
    'breakeven_hpp_rp': be_hpp,
    'breakeven_margin_pct': M['breakeven_margin_pct'],
    'breakeven_vol_jt': M['breakeven_vol_m'],
    'hpp_pack_rp': HPP,
    'grid_6x5': {'prices': prices_g, 'vols_jt': [42, 51, 60, 69, 78], 'npv': grid,
                 'neg_cells': neg, 'row_avg': row_avg},
    'downside': ds,
    'maut_curve': {str(k): v for k, v in curve.items()},
    'maut_crossover_npv_pct': 25,
    'sanity_pct': {'dari_29_1T': round(s1, 1), 'dari_102_7T': round(s2, 1)},
    'mc_ranges': {'harga': [6000, 7500, 9000], 'volume_jt': [42, 60, 78],
                  'marjin': [0.33, 0.38, 0.43]},
    'mc': {'p_pos': mc['p_pos'], 'p10': mc['p10'], 'p50': mc['p50'],
           'p90': mc['p90'], 'min': mc['min'], 'max': mc['max'],
           'p90_minus_p10': round(mc['p90'] - mc['p10'], 1)},
    'mc_hist': {'bins': [int(c) for c in counts], 'edges': [round(float(e), 1) for e in edges],
                'xmin': 0, 'xmax': 1600},
    'rev_thn3': round(rev3, 1),
    'gate0': {'pct': 60, 'vol_jt': gate_vol_jt, 'npv': gate_npv,
              'pct_above_breakeven': gate_margin_pct, 'test_cost_miliar': 2,
              'sellthrough_target_pct': 70},
    'unit_economics': ue,
    'tornado': {k: [round(lo, 1), round(hi, 1)] for k, (lo, hi) in
                ((kk, tuple(vv)) for kk, vv in t.items())},
    'tornado_base': M['tornado_base'],
    'trade_margin': trade,
    'trade_margin_int': trade_int,
    'trade_zero_pct': {'A': round(zero_A * 100, 1), 'B': round(zero_B * 100, 1),
                       'C': round(zero_C * 100, 1)},
    'trade_crossover_ab_pct': round(crossover_ab * 100, 1),
    'trade_crossover_ab_npv': round(cross_npv, 1),
    'trade_condition_pct': round(zero_A * 100, 1),
    'trade_breakeven_net_rp': round(PRICE * (1 - zero_A)),
    'mc_p1': round(mc_p1, 1),
    'mc_uniform_neg_pct': round(mc_uni_neg * 100, 2),
    'mc_uniform_neg_count': int((npvs_u < 0).sum()),
    'gate0_rationale': {'breakeven_vol_share_pct': round(be_vol_share * 100, 1),
                        'conversion_assumed_pct': 50,
                        'implied_threshold_pct': round(gate_ratio * 100),
                        'threshold_pct': 60},
    'trade_row2': row2,
    'trade_row2_int': row2_int,
    'trade_row2_B_tmassal10': npv_B_tmassal10,
    'trade_row2_crossover_tprem_pct': round(row2_cross * 100, 1),
    'combined_threshold': {'vol_36jt_t_max_pct': round(comb_36 * 100, 1),
                           'vol_42jt_t_max_pct': round(comb_42 * 100, 1),
                           'vol_60jt_t_max_pct': round(zero_A * 100, 1),
                           'npv_vol36_t20': npv_36_t20,
                           'npv_vol42_t20': npv_42_t20},
    'trade_crossover_general': {
        'intercept_pct': round(a_fit, 2),
        'slope': round(b_fit, 3),
        'points_pct': {str(int(tm * 100)): v[0] for tm, v in cross_pts.items()},
        'npv_B_at_tm': {str(int(tm * 100)): v[1] for tm, v in cross_pts.items()}},
    'gate0_npv_cushion': {
        'npv_corner_exact': npv_corner,
        'npv_corner_int': int(rhu1(npv_corner)),
        'npv_min_lanjut': 100,
        't_max_pct_at_42jt': round(t_max_100_42 * 100, 1),
        'vol_min_jt_at_t20': round(vol_min_100_t20 / 1e6, 1)},
}
with open('mielestari-v10-derived.json', 'w') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print('OK - mielestari-v10-derived.json tersimpan')

# --- canonical numbers: SATU sumber kebenaran untuk uji otomatis deck ---
canon = {
    'npv_A': 641, 'npv_B': 71, 'npv_C': 40,
    'payback_A': '1,33', 'cf_A': [120.1, 181.3, 232.9, 297.4, 378.0],
    'npv_per_harga': {'6000': 135, '6500': 303, '7000': 472, '7500': 641,
                      '8000': 810, '8500': 979, '9000': 1148},
    'breakeven_price': 5602, 'breakeven_vol_jt': 18.6,
    'breakeven_hpp': 6548, 'breakeven_margin_pct': 12.7,
    'hpp_pack': 4650, 'gross_pack': 2850,
    'mc_p_pos_pct': 100.0, 'mc_p10': 333, 'mc_p50': 628, 'mc_p90': 966,
    'mc_min': 10, 'mc_max': 1520,
    'downside': {'harga-20%+vol-30%': 8, 'vol-50%': 177, 'harga-20%': 135,
                 'harga-20%+vol-50%': -77, 'harga-10%+vol-20%': 253,
                 'marjin-10poin': 388, 'marjin-10poin+vol-30%': 185,
                 'triple': -81, 'kanibalisasi-40%': 585},
    'grid_6x5': grid,
    'tornado': {'harga': [135, 1148], 'volume': [362, 920], 'marjin': [514, 768],
                'kanibalisasi': [619, 663], 'pemasaran': [631, 651]},
    'trade_margin': {'0': {'A': 641, 'B': 71, 'C': 40},
                     '15': {'A': 261, 'B': 6, 'C': -25},
                     '20': {'A': 135, 'B': -15, 'C': -47},
                     '22.5': {'A': 71, 'B': -26, 'C': -58},
                     '25': {'A': 8, 'B': -37, 'C': -68},
                     '30': {'A': -119, 'B': -59, 'C': -90}},
    'trade_margin_exact': {k: (v['npv_A'], v['npv_B'], v['npv_C'])
                           for k, v in trade.items()},
    'trade_zero_pct': {'A': 25.3, 'B': 16.5, 'C': 9.2},
    'trade_crossover_ab_pct': 27.1, 'trade_crossover_ab_npv': -46,
    'trade_condition_pct': 25.3,
    'trade_breakeven_net_rp': 5602,
    'mc_p1': 157, 'mc_uniform_neg_pct': 0.3, 'mc_uniform_neg_count': 26,
    'gate0_threshold_pct': 60, 'gate0_breakeven_share_pct': 31,
    'gate0_vol_jt': 36, 'gate0_npv': 269,
    'trade_row2_B_tmassal10': 28,
    'trade_row2': {'0': {'A': 641, 'B': 28}, '15': {'A': 261, 'B': 28},
                   '20': {'A': 135, 'B': 28}, '25': {'A': 8, 'B': 28},
                   '30': {'A': -119, 'B': 28}},
    'trade_row2_crossover_tprem_pct': 24.2,
    'combined_threshold': {'vol_36jt_t_max_pct': round(comb_36 * 100, 1),
                           'vol_42jt_t_max_pct': round(comb_42 * 100, 1),
                           'vol_60jt_t_max_pct': round(zero_A * 100, 1),
                           'npv_vol36_t20': npv_36_t20,
                           'npv_vol42_t20': npv_42_t20},
    'trade_crossover_general': {'intercept_pct': 22.5, 'slope': 0.17,
                                'points_pct': {'0': 22.5, '10': 24.2,
                                               '20': 25.9, '30': 27.6}},
    'gate0_npv_cushion': {'npv_corner_exact': 7.7, 'npv_corner_int': 8,
                          'npv_min_lanjut': 100, 't_max_pct_at_42jt': 14.8,
                          'vol_min_jt_at_t20': 55.1},
    'rev_thn3': 703, 'rev_thn3_exact': 703.5, 'rev_thn1': 450,
    'vol_thn3_jt': 93.8, 'unit_contrib_thn1': 2001,
}
with open('canonical-numbers-v10.json', 'w') as f:
    json.dump(canon, f, indent=2, ensure_ascii=False)
print('OK - canonical-numbers-v10.json tersimpan')
