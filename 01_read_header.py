#!/usr/bin/env python3
"""
Read the headers. Half of your SExtractor config is not a free choice —
it is a fact about your image. Go and get it.

Run:  python3 scripts/01_read_header.py
"""
import sys
from astropy.io import fits

BANDS  = ['U', 'G', 'R']
FIELD  = 'HYDRA_D_0003'
PIXSCL = 0.55            # arcsec / pixel, S-PLUS

print()
print('=' * 74)
print(' What the image is telling you')
print('=' * 74)
print()

rows = {}
for b in BANDS:
    path = f'data/{FIELD}_{b}.fits'
    try:
        # The data may live in extension 0 or 1 — check.
        with fits.open(path) as h:
            ext = 1 if len(h) > 1 and h[1].data is not None else 0
            hdr = h[ext].header
    except FileNotFoundError:
        print(f'  Missing: {path}')
        print('  Run:  bash scripts/00_get_data.sh')
        sys.exit(1)

    rows[b] = {
        'nx':   hdr.get('NAXIS1'),
        'ny':   hdr.get('NAXIS2'),
        'fwhm': hdr.get('FWHMMEAN'),
        'satur':hdr.get('SATURATE'),
        'gain': hdr.get('GAIN'),
        'exp':  hdr.get('EXPTIME'),
        'ext':  ext,
    }

print(f'  {"band":6s} {"size":14s} {"FWHM [\"]":>10s} {"FWHM [px]":>10s} '
      f'{"SATURATE":>12s} {"GAIN":>10s}')
print('  ' + '-' * 70)
for b in BANDS:
    r = rows[b]
    fwhm_px = r['fwhm'] / PIXSCL if r['fwhm'] else float('nan')
    print(f'  {b:6s} {r["nx"]}x{r["ny"]:<8} {r["fwhm"]:>10.3f} {fwhm_px:>10.2f} '
          f'{r["satur"]:>12.1f} {r["gain"]:>10.1f}')

print()
print('=' * 74)
print(' What to do with this')
print('=' * 74)
print()
print('  SEEING_FWHM     ->  the FWHM in ARCSEC. Different in every band.')
print('  SATUR_LEVEL     ->  the SATURATE value. NOT the 50000 default.')
print('                      Get this wrong and saturated stars are never')
print('                      flagged. FLAGS=4 will never appear, and you')
print('                      will not notice.')
print('  GAIN            ->  from the header.')
print(f'  PIXEL_SCALE     ->  {PIXSCL}  (S-PLUS)')
print()
print('  FILTER_NAME     ->  look at the FWHM in PIXELS above, then look at')
print('                      the kernel names: gauss_2.0_5x5.conv, etc.')
print('                      The number in the name IS the FWHM in pixels.')
print('                      Pick the closest one.')
print()

# The point worth pausing on
u, r = rows['U']['fwhm'], rows['R']['fwhm']
if u and r:
    print('  ' + '-' * 70)
    print(f'  Notice: u has FWHM = {u:.2f}", r has FWHM = {r:.2f}".')
    print(f'          The u PSF is {100*(u/r - 1):.0f}% wider.')
    print()
    print('          Two sources cleanly separated in r can be a single')
    print('          merged blob in u. It is the same patch of sky — and the')
    print('          number of objects you see depends on the band.')
    print()
    print('          Remember that when you get to dual-image mode.')
print()
