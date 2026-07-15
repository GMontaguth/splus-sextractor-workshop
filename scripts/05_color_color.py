#!/usr/bin/env python3
"""
The deliverable.

Make the same colour-colour diagram TWICE — once from the dual-mode
catalogs, once from the band-by-band catalogs.

Nothing crashed. Both catalogs look perfectly respectable.
One of them has colours that mean nothing.

Run:  python3 scripts/05_color_color.py
"""
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import SkyCoord
import astropy.units as u

BANDS = ['U', 'G', 'R']
MAG   = 'MAG_APER'          # <-- fixed aperture. NOT MAG_AUTO. Think about why.
ERR   = 'MAGERR_APER'

with fits.open('cat/dual_R.cat') as h:
    HDU = 2 if len(h) > 2 else 1


# ---------------------------------------------------------------------
# A) DUAL MODE — the rows already correspond, one to one.
#
# Every band was measured through the SAME aperture at the SAME position,
# defined once on the detection image. So row i in cat/dual_U.cat is the
# SAME SOURCE as row i in cat/dual_R.cat.
#
# No cross-matching needed. That is the whole point.
# ---------------------------------------------------------------------
dual = {b: Table.read(f'cat/dual_{b}.cat', format='fits', hdu=HDU) for b in BANDS}

n = len(dual['R'])
assert all(len(dual[b]) == n for b in BANDS), \
    "Dual-mode catalogs have different lengths — something is wrong."

ok_d = np.ones(n, dtype=bool)
for b in BANDS:
    ok_d &= (dual[b]['FLAGS'] == 0) & (dual[b][ERR] < 0.2)

ug_d = dual['U'][MAG][ok_d] - dual['G'][MAG][ok_d]
gr_d = dual['G'][MAG][ok_d] - dual['R'][MAG][ok_d]
sm_d = dual['R']['SPREAD_MODEL'][ok_d] if 'SPREAD_MODEL' in dual['R'].colnames else None


# ---------------------------------------------------------------------
# B) BAND BY BAND — you have to cross-match, and that is the problem.
#
# The catalogs have DIFFERENT lengths. Different sources. Different
# apertures. You have to guess which row corresponds to which.
# ---------------------------------------------------------------------
sing = {b: Table.read(f'cat/single_{b}.cat', format='fits', hdu=HDU) for b in BANDS}

print()
print('=' * 62)
print(' How many sources did each method give you?')
print('=' * 62)
print()
print(f'  dual mode:   {len(dual["R"]):6d}  (same rows in every band, by construction)')
for b in BANDS:
    print(f'  single {b}:    {len(sing[b]):6d}')
print()
print('  The single-band catalogs have DIFFERENT lengths.')
print('  Different sources were detected in each band.')
print('  Ask yourself: which sources did u miss, and why?')
print()

ref = sing['R']
c_ref = SkyCoord(ref['ALPHA_J2000'], ref['DELTA_J2000'])

mags, ok_s = {'R': np.asarray(ref[MAG])}, (ref['FLAGS'] == 0) & (ref[ERR] < 0.2)
for b in ['U', 'G']:
    c = SkyCoord(sing[b]['ALPHA_J2000'], sing[b]['DELTA_J2000'])
    idx, d2d, _ = c_ref.match_to_catalog_sky(c)
    matched = d2d < 1.0 * u.arcsec
    mags[b] = np.asarray(sing[b][MAG][idx])
    ok_s &= matched & (sing[b]['FLAGS'][idx] == 0) & (sing[b][ERR][idx] < 0.2)
    print(f'  {b}: {matched.sum()} of {len(ref)} r-sources found a counterpart '
          f'within 1"')

ug_s = mags['U'][ok_s] - mags['G'][ok_s]
gr_s = mags['G'][ok_s] - mags['R'][ok_s]
print()


# ---------------------------------------------------------------------
# The figure
# ---------------------------------------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(13, 5.8), sharex=True, sharey=True)

if sm_d is not None:
    star = np.abs(sm_d) < 0.003
    ax[0].scatter(gr_d[~star], ug_d[~star], s=2, alpha=0.2, c='tab:blue',
                  label=f'galaxy  ({(~star).sum()})')
    ax[0].scatter(gr_d[star], ug_d[star], s=2, alpha=0.4, c='tab:red',
                  label=f'star  ({star.sum()})')
    ax[0].legend(markerscale=6, loc='upper left')
else:
    ax[0].scatter(gr_d, ug_d, s=2, alpha=0.25, c='k')
    print('  (No SPREAD_MODEL column — run PSFEx and the second SExtractor')
    print('   pass if you want the points coloured by star/galaxy.)')
    print()

ax[0].set_title(f'DUAL MODE  —  detect on r, measure through the\n'
                f'same aperture in every band     (n = {ok_d.sum()})',
                fontsize=11)

ax[1].scatter(gr_s, ug_s, s=2, alpha=0.25, c='k')
ax[1].set_title(f'BAND BY BAND  —  each band draws its own\n'
                f'aperture, then cross-match     (n = {ok_s.sum()})',
                fontsize=11)

for a in ax:
    a.set_xlabel('(g $-$ r)')
    a.set_xlim(-0.8, 2.2)
    a.set_ylim(-0.5, 3.5)
    a.grid(alpha=0.15)
ax[0].set_ylabel('(u $-$ g)')

plt.tight_layout()
plt.savefig('color_color.png', dpi=130)

print('=' * 62)
print(' Wrote color_color.png')
print('=' * 62)
print()
print('  Compare the two panels.')
print()
print('  The stellar locus is TIGHTER in one of them.')
print()
print('  That extra scatter in the other panel is NOT photometric noise.')
print('  It is your apertures disagreeing with each other.')
print()
print('  The Kron ellipse is adaptive — its size depends on the shape')
print('  measured in THAT image. Worse seeing in u -> the source looks')
print('  fatter -> the ellipse comes out bigger -> more flux.')
print()
print('  Your colour now has a bias that has nothing to do with the star.')
print()
print('  Nothing crashed. Nothing warned you. Both catalogs open fine')
print('  in TOPCAT.')
print()
print('  One of them just has colours that mean nothing.')
print()
