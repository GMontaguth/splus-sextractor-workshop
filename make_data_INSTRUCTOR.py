#!/usr/bin/env python3
"""
FOR THE INSTRUCTOR — run this ONCE, before the workshop.

Builds the data assets to attach to the GitHub Release:
  - 2000x2000 cutouts in u, g, r  (+ weight maps), UNCOMPRESSED
  - zeropoints.txt, with the full spatial model summary

Then:
  gh release create v1.0-data data/*.fits data/zeropoints.txt \
     --title "Workshop data" --notes "S-PLUS iDR6 cutouts, HYDRA_D_0003"

NOTE: the students never run this. It is here so you can regenerate the
data, and so they can see where it came from if they are curious.
"""
import os
import numpy as np
import splusdata
from astropy.io import fits

FIELD = 'HYDRA_D_0003'
DR    = 'idr6'
BANDS = ['U', 'G', 'R']
SIZE  = 2000              # pixels. 2000 * 0.55" = 18 arcmin.

os.makedirs('data', exist_ok=True)
conn = splusdata.Core()

# ---------------------------------------------------------------------
# 1. Full frames -> cut the centre -> write UNCOMPRESSED
#
# The S-PLUS frames come as CompImageHDU (tile-compressed). SExtractor
# 2.25 will NOT read that. We decompress here so the students never hit
# it. (Worth mentioning in the lecture — it is a real gotcha.)
# ---------------------------------------------------------------------
for b in BANDS:
    for weight in (False, True):
        suf = '.weight' if weight else ''
        out = f'data/{FIELD}_{b}{suf}.fits'
        if os.path.exists(out):
            print(f'  [have]  {out}')
            continue

        print(f'  [get ]  {FIELD} {b} {"weight" if weight else "science"} ...')
        hdul = conn.field_frame(FIELD, b, weight=weight, data_release=DR)

        # Data may be in ext 0 or 1 — find it
        ext  = 1 if len(hdul) > 1 and hdul[1].data is not None else 0
        data = hdul[ext].data
        hdr  = hdul[ext].header

        ny, nx = data.shape
        y0, x0 = (ny - SIZE) // 2, (nx - SIZE) // 2
        cut = data[y0:y0+SIZE, x0:x0+SIZE]

        # Fix the WCS reference pixel for the cutout
        h = hdr.copy()
        if 'CRPIX1' in h: h['CRPIX1'] -= x0
        if 'CRPIX2' in h: h['CRPIX2'] -= y0
        h['NAXIS1'], h['NAXIS2'] = SIZE, SIZE

        fits.writeto(out, cut, h, overwrite=True)
        print(f'          -> {out}  ({os.path.getsize(out)/1e6:.0f} MB)')

# ---------------------------------------------------------------------
# 2. Zero points — and NOT just the median.
#
# In iDR6 the ZP is a SPATIAL MODEL. Give them the whole summary, so they
# have to decide for themselves whether a single number is good enough.
# ---------------------------------------------------------------------
lines = [
    "# S-PLUS iDR6 zero points — HYDRA_D_0003",
    "#",
    "# The zero point is NOT a single number. It is a spatial model that",
    "# varies across the field, on a 15x15 grid.",
    "#",
    "# 'median' is the global median. 'std' is the scatter of the spatial",
    "# correction. 'range' is max - min across the whole field.",
    "#",
    "# Using the median is an APPROXIMATION. Look at 'std' and decide",
    "# whether it is a safe one — and be able to defend your answer.",
    "#",
    "# Note that the answer is not the same in every band.",
    "#",
    f"# {'band':6s} {'median':>9s} {'std':>8s} {'range':>8s}",
]

print()
print(f'  {"band":6s} {"median":>9s} {"std":>8s} {"range":>8s}')
print('  ' + '-' * 34)
for b in BANDS:
    m = conn.get_zp_file(field=FIELD, band=b, data_release=DR)
    med = m['global_median']
    std = m['std_correction']
    rng = m['max_correction'] - m['min_correction']
    lines.append(f"  {b:6s} {med:9.4f} {std:8.4f} {rng:8.4f}")
    print(f'  {b:6s} {med:9.4f} {std:8.4f} {rng:8.4f}')

with open('data/zeropoints.txt', 'w') as f:
    f.write('\n'.join(lines) + '\n')

print()
print('  Wrote data/zeropoints.txt')
print()
print('  Now attach these to a GitHub Release:')
print('     gh release create v1.0-data data/*.fits data/zeropoints.txt \\')
print('        --title "Workshop data" --notes "S-PLUS iDR6, HYDRA_D_0003"')
print()

# ---------------------------------------------------------------------
# 3. Sanity check — how many sources will they get?
# ---------------------------------------------------------------------
print('  Before you publish: run SExtractor on the r cutout and count.')
print('  You want enough stars for PSFEx to fit a degree-2 polynomial —')
print('  roughly 60 minimum, and more is much better.')
print()
print('  If the cutout is too sparse, raise SIZE and regenerate.')
print()
