#!/usr/bin/env bash
# Download the images from the GitHub Release.
#
# The FITS files are attached to the Release, not committed to the repo —
# they are ~100 MB, which is too much for git.

set -e

# ---------------------------------------------------------------------
# Your repo and the release tag
# ---------------------------------------------------------------------
REPO="GMontaguth/splus-sextractor-workshop"
TAG="v1.0-data"
# ---------------------------------------------------------------------

BASE="https://github.com/${REPO}/releases/download/${TAG}"

mkdir -p data
cd data

FILES=(
    "HYDRA_D_0003_U.fits"
    "HYDRA_D_0003_U.weight.fits"
    "HYDRA_D_0003_G.fits"
    "HYDRA_D_0003_G.weight.fits"
    "HYDRA_D_0003_R.fits"
    "HYDRA_D_0003_R.weight.fits"
)

for f in "${FILES[@]}"; do
    if [ -f "$f" ]; then
        echo "  [have]  $f"
    else
        echo "  [get ]  $f"
        curl -fL --progress-bar -O "${BASE}/${f}"
    fi
done

cd ..
echo
echo "Done. Now check everything is in place:"
echo "   bash scripts/00_check_setup.sh"
