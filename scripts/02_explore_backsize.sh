#!/usr/bin/env bash
# Explore BACK_SIZE.
#
# Same image. Same sources. One parameter changed.
# This produces three background models AND three catalogs, so you can
# look at the models AND measure what they did to your photometry.

set -e

SEX=$(command -v sex || command -v source-extractor)
[ -z "$SEX" ] && { echo "SExtractor not found."; exit 1; }

IMG=data/HYDRA_D_0003_R.fits
WHT=data/HYDRA_D_0003_R.weight.fits

mkdir -p cat check

# Put YOUR zero point here — read it out of data/zeropoints.txt
ZP=22.784

for BS in 32 64 256; do
    echo ">>> BACK_SIZE = $BS"
    $SEX $IMG -c config/default.sex \
        -CATALOG_NAME    cat/bs${BS}.cat \
        -CATALOG_TYPE    FITS_1.0 \
        -MAG_ZEROPOINT   $ZP \
        -WEIGHT_TYPE     MAP_WEIGHT \
        -WEIGHT_IMAGE    $WHT \
        -BACK_SIZE       $BS \
        -CHECKIMAGE_TYPE BACKGROUND \
        -CHECKIMAGE_NAME check/bkg_${BS}.fits
done

echo
echo "=============================================================="
echo " Now LOOK at them. With the scale LOCKED."
echo "=============================================================="
echo
echo "  ds9 check/bkg_32.fits check/bkg_64.fits check/bkg_256.fits \\"
echo "      -scale limits -0.02 0.05 \\"
echo "      -lock frame image -lock scale yes -lock colorbar yes -tile"
echo
echo " The locked scale is not cosmetic. If each frame auto-scales to its"
echo " own range, the comparison is a LIE — they will look similar because"
echo " each one has been stretched to fill the colour bar."
echo
echo " Questions:"
echo "   - At BACK_SIZE = 32, can you see your STARS inside the sky model?"
echo "   - Can you see the galaxy?"
echo "   - What is SExtractor about to subtract from what?"
echo
echo " Then measure the consequence:"
echo "   python3 scripts/03_compare_backsize.py"
echo
