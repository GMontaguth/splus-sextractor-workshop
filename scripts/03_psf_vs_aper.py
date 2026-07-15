#!/usr/bin/env python3
"""
OPTIONAL — if you finished early.

Why does PSF photometry exist at all? Here is the answer, measured.

For STARS, MAG_PSF and MAG_APER should agree — a star IS the PSF, so
fitting it and integrating a fixed aperture around it give the same flux.

...except when a star has a NEIGHBOUR. The fixed aperture happily collects
the neighbour's flux too, so MAG_APER comes out too BRIGHT. The PSF fit
knows the shape of a star and is not fooled.

That is the entire reason PSF photometry exists: crowded fields.

Run:  python3 scripts/06_psf_vs_aper.py
Needs: the pass-2 catalog (final.param, run with -PSF_NAME).
"""
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import SkyCoord
import astropy.units as u

CAT = 'cat/r_final.cat'      # <-- your pass-2 catalog (the one with SPREAD_MODEL)

with fits.open(CAT) as h:
    HDU = 2 if len(h) > 2 else 1
c = Table.read(CAT, format='fits', hdu=HDU)

need = ['MAG_PSF', 'MAG_APER', 'SPREAD_MODEL', 'FLAGS', 'MAGERR_AUTO',
        'ALPHA_J2000', 'DELTA_J2000']
missing = [k for k in need if k not in c.colnames]
if missing:
    print(f'Your catalog is missing: {missing}')
    print('Did you run the SECOND pass, with -PSF_NAME and final.param?')
    raise SystemExit(1)

# Keep clean STARS only. MAG_PSF is meaningless for galaxies.
star = (np.abs(c['SPREAD_MODEL']) < 0.003) & (c['FLAGS'] == 0) \
       & (c['MAGERR_AUTO'] < 0.1)
s = c[star]
print(f'{len(s)} clean stars')

# For each star, distance to its nearest OTHER star.
# Crowding = a close neighbour.
coo = SkyCoord(s['ALPHA_J2000'], s['DELTA_J2000'])
idx, d2d, _ = coo.match_to_catalog_sky(coo, nthneighbor=2)   # 2nd = nearest OTHER
nn_arcsec = d2d.arcsec

dm = np.asarray(s['MAG_APER'] - s['MAG_PSF'])    # aper - psf
# aperture brighter (contaminated) -> MAG_APER smaller -> dm negative

fig, ax = plt.subplots(1, 2, figsize=(13, 5))

# (a) the difference vs how crowded the star is
ax[0].scatter(nn_arcsec, dm, s=4, alpha=0.3, c='k')
ax[0].axhline(0, color='r', ls='--', lw=1)
ax[0].set_xlim(0, 20)
ax[0].set_ylim(-0.3, 0.3)
ax[0].set_xlabel('distance to nearest neighbour ["]')
ax[0].set_ylabel('MAG_APER $-$ MAG_PSF')
ax[0].set_title('Isolated stars agree.\nCrowded stars: the aperture is contaminated.')

# (b) same thing, binned
bins = np.linspace(0, 20, 11)
ctr = 0.5*(bins[1:]+bins[:-1])
med = [np.median(dm[(nn_arcsec>=bins[i])&(nn_arcsec<bins[i+1])])
       if np.sum((nn_arcsec>=bins[i])&(nn_arcsec<bins[i+1]))>5 else np.nan
       for i in range(len(bins)-1)]
ax[1].plot(ctr, med, 'o-', c='tab:red')
ax[1].axhline(0, color='k', ls='--', lw=0.8)
ax[1].set_xlabel('distance to nearest neighbour ["]')
ax[1].set_ylabel('median  MAG_APER $-$ MAG_PSF')
ax[1].set_title('The closer the neighbour,\nthe more the aperture over-counts')

plt.tight_layout()
plt.savefig('psf_vs_aper.png', dpi=130)
print('Wrote psf_vs_aper.png')
print()
print('  Read the left panel from right to left:')
print('    - Far from any neighbour  -> MAG_APER = MAG_PSF. They agree.')
print('    - Close to a neighbour    -> MAG_APER is BRIGHTER (dm < 0).')
print('      The fixed aperture ate the neighbour. The PSF fit did not.')
print()
print('  That is why PSF photometry exists. Not for isolated stars —')
print('  for crowded ones.')
