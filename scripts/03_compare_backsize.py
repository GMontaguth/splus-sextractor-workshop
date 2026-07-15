#!/usr/bin/env python3
"""
The background models look completely different. But what did that
actually DO to your photometry?

Do not guess. Measure.

Run:  python3 scripts/03_compare_backsize.py
"""
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import SkyCoord
import astropy.units as u

REF = 64                       # the run we compare against
ALT = {32: 'tab:red', 256: 'tab:blue'}

with fits.open(f'cat/bs{REF}.cat') as h:
    HDU = 2 if len(h) > 2 else 1

cats = {bs: Table.read(f'cat/bs{bs}.cat', format='fits', hdu=HDU)
        for bs in [32, REF, 256]}

ref = cats[REF]
# The columns already carry a 'deg' unit from the FITS header.
c_ref = SkyCoord(ref['ALPHA_J2000'], ref['DELTA_J2000'])

fig, ax = plt.subplots(1, 2, figsize=(13, 5))

print()
print('=' * 66)
print(f' What BACK_SIZE did to your photometry (relative to {REF})')
print('=' * 66)
print()

for bs, col in ALT.items():
    cat = cats[bs]
    c   = SkyCoord(cat['ALPHA_J2000'], cat['DELTA_J2000'])
    idx, d2d, _ = c_ref.match_to_catalog_sky(c)

    # TIGHT match. Same image, same detections -> the positions should agree
    # to well under a pixel. A loose radius mismatches neighbours in a
    # crowded field and injects fake scatter that has nothing to do with
    # BACK_SIZE.
    # Also cut on S/N: the faint end dominates the scatter and tells you
    # nothing about the systematic you are chasing.
    ok = ((d2d < 0.3 * u.arcsec)
          & (ref['FLAGS'] == 0) & (cat['FLAGS'][idx] == 0)
          & (ref['MAGERR_AUTO'] < 0.1) & (cat['MAGERR_AUTO'][idx] < 0.1))

    m_ref = np.asarray(ref['MAG_AUTO'][ok])
    dm    = np.asarray(cat['MAG_AUTO'][idx][ok]) - m_ref

    ax[0].scatter(m_ref, dm, s=2, alpha=0.2, c=col,
                  label=f'BACK_SIZE {bs}  (n={ok.sum()})')

    bins = np.arange(np.floor(m_ref.min()), 22, 0.5)
    ctr, med, q16, q84 = [], [], [], []
    for i in range(len(bins) - 1):
        sel = (m_ref >= bins[i]) & (m_ref < bins[i + 1])
        if sel.sum() > 10:
            ctr.append(0.5 * (bins[i] + bins[i + 1]))
            med.append(np.median(dm[sel]))
            q16.append(np.percentile(dm[sel], 16))
            q84.append(np.percentile(dm[sel], 84))
    ax[1].plot(ctr, med, 'o-', c=col, label=f'BACK_SIZE {bs}')
    ax[1].fill_between(ctr, q16, q84, color=col, alpha=0.15)

    bright = np.argsort(m_ref)[:100]
    mad = 1.4826 * np.median(np.abs(dm - np.median(dm)))
    print(f'  BACK_SIZE {bs:3d}:')
    print(f'     median dmag, all         = {np.median(dm):+.4f}')
    print(f'     median dmag, brightest   = {np.median(dm[bright]):+.4f}')
    print(f'     scatter (MAD)            =  {mad:.4f}')
    print(f'     matched                  =  {ok.sum()}')
    print()

for a in ax:
    a.axhline(0, color='k', lw=0.8, ls='--')
    a.set_xlabel(f'MAG_AUTO   (BACK_SIZE = {REF})')
    a.legend(markerscale=5)

ax[0].set_ylabel('$\\Delta$ MAG_AUTO')
ax[0].set_ylim(-0.08, 0.08)
ax[0].set_title('Same image. Same sources.\nOnly BACK_SIZE changed.')
ax[1].set_ylabel('median  $\\Delta$ MAG_AUTO')
ax[1].set_ylim(-0.03, 0.03)
ax[1].set_title('Systematic shift vs. brightness\n(band = 16-84 percentile)')

plt.tight_layout()
plt.savefig('backsize_photometry.png', dpi=130)
print('  Wrote backsize_photometry.png')
print()
print('=' * 66)
print(' Look at the RIGHT panel and answer these:')
print('=' * 66)
print()
print('   1. Do the two curves CROSS? At roughly what magnitude?')
print()
print('   2. At the BRIGHT end, which BACK_SIZE makes sources FAINTER?')
print('      Why? (Hint: what did you see inside the background model?)')
print()
print('   3. At the FAINT end, the sign flips. Why?')
print()
print('   4. How big is the effect, in magnitudes? Is it big enough to')
print('      matter for what you are doing?')
print()
print('   Question 4 is the important one. The background models looked')
print('   completely different. That does NOT automatically mean the')
print('   consequence is large.')
print()
print('   You only know because you measured it.')
print()
