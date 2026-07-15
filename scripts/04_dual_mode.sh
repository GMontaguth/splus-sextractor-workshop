#!/usr/bin/env bash
# Three bands, TWO ways.
#
#   A) Dual-image mode  — detect on r, measure through those apertures
#   B) Band by band     — each band detects and measures on its own
#
# You are going to make the same colour-colour diagram from both.
# One of them is going to be wrong.

set -e

SEX=$(command -v sex || command -v source-extractor)
[ -z "$SEX" ] && { echo "SExtractor not found."; exit 1; }

F=HYDRA_D_0003
DET=R                       # detection band: deep, best seeing

mkdir -p cat check

# --- Zero points -------------------------------------------------------
# Read these out of data/zeropoints.txt yourself.
# They are NOT the same in every band. And in iDR6 they are not even a
# single number per band — check the 'std' column before you accept these.
declare -A ZP
ZP[U]=00.000      # <-- FILL THIS IN
ZP[G]=00.000      # <-- FILL THIS IN
ZP[R]=00.000      # <-- FILL THIS IN

for b in U G R; do
    if [ "${ZP[$b]}" == "00.000" ]; then
        echo "ERROR: you have not set the zero point for band $b."
        echo "       Open data/zeropoints.txt and edit this script."
        exit 1
    fi
done

# =======================================================================
#  A)  DUAL-IMAGE MODE  —  the right way
# =======================================================================
#
#   sex  detection.fits,measurement.fits
#
#   Sources are DETECTED on the first image, MEASURED on the second.
#   r defines WHERE the sources are and WHAT APERTURE to use.
#   The other bands only measure through that same aperture.
#
#   Same aperture. Same position. Every band.
#   Without that, there is no colour.
#
echo "======================================================"
echo " A) DUAL-IMAGE MODE  (detect on $DET)"
echo "======================================================"

for b in U G R; do
    echo ">>> detect on $DET, measure on $b"
    $SEX data/${F}_${DET}.fits,data/${F}_${b}.fits \
        -c config/default.sex \
        -CATALOG_NAME  cat/dual_${b}.cat \
        -CATALOG_TYPE  FITS_1.0 \
        -MAG_ZEROPOINT ${ZP[$b]} \
        -WEIGHT_TYPE   MAP_WEIGHT,MAP_WEIGHT \
        -WEIGHT_IMAGE  data/${F}_${DET}.weight.fits,data/${F}_${b}.weight.fits
done

# =======================================================================
#  B)  BAND BY BAND  —  the mistake
# =======================================================================
#
#   Each band detects on its own and draws its OWN aperture.
#
#   The Kron ellipse is ADAPTIVE — its size depends on the shape measured
#   in THAT image. The seeing in u is worse, so the source looks fatter,
#   so the ellipse comes out BIGGER. More area, more flux.
#
#   Your colour now has a bias that has nothing to do with the star.
#
#   And it is worse: a faint source detected in r may not be detected at
#   all in u. Two sources separated in r may be one blob in u.
#   There is nothing to cross-match.
#
echo
echo "======================================================"
echo " B) BAND BY BAND  (each band on its own)"
echo "======================================================"

for b in U G R; do
    echo ">>> detect AND measure on $b"
    $SEX data/${F}_${b}.fits \
        -c config/default.sex \
        -CATALOG_NAME  cat/single_${b}.cat \
        -CATALOG_TYPE  FITS_1.0 \
        -MAG_ZEROPOINT ${ZP[$b]} \
        -WEIGHT_TYPE   MAP_WEIGHT \
        -WEIGHT_IMAGE  data/${F}_${b}.weight.fits
done

echo
echo "======================================================"
echo " Done. Now make the colour-colour diagram BOTH ways:"
echo
echo "   python3 scripts/05_color_color.py"
echo
echo " Note how many sources each method gives you."
echo " They will not be the same number. Ask yourself why."
echo "======================================================"
