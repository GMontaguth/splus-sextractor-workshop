#!/usr/bin/env bash
# Check that everything you need is present, BEFORE the session starts.
# Run this at home. If anything fails, tell me before Thursday.

echo "=============================================="
echo " S-PLUS SExtractor workshop — setup check"
echo "=============================================="
echo

FAIL=0

# ---- SExtractor -------------------------------------------------------
if command -v sex &> /dev/null; then
    echo "  [ok]   sex             $(sex -v 2>&1 | head -1)"
    SEX=sex
elif command -v source-extractor &> /dev/null; then
    echo "  [ok]   source-extractor  $(source-extractor -v 2>&1 | head -1)"
    echo "         NOTE: your binary is 'source-extractor', not 'sex'."
    echo "         Everywhere the README says 'sex', use 'source-extractor'."
    SEX=source-extractor
else
    echo "  [FAIL] SExtractor not found"
    echo "         → sudo apt install source-extractor"
    FAIL=1
fi

# ---- PSFEx ------------------------------------------------------------
if command -v psfex &> /dev/null; then
    echo "  [ok]   psfex           $(psfex -v 2>&1 | head -1)"
    if ldd "$(command -v psfex)" 2>/dev/null | grep -qi plplot; then
        echo "         PLPlot found — check-plots will work."
    else
        echo "         WARNING: no PLPlot. Check-plots may not be written."
    fi
else
    echo "  [FAIL] psfex not found"
    echo "         → sudo apt install psfex"
    FAIL=1
fi

# ---- DS9 --------------------------------------------------------------
if command -v ds9 &> /dev/null; then
    echo "  [ok]   ds9"
else
    echo "  [FAIL] ds9 not found"
    echo "         → sudo apt install saods9"
    echo "         (or conda install -c conda-forge ds9)"
    FAIL=1
fi

# ---- Python -----------------------------------------------------------
python3 - <<'PY'
mods = ['numpy', 'astropy', 'matplotlib']
missing = []
for m in mods:
    try:
        __import__(m)
        print(f"  [ok]   python: {m}")
    except ImportError:
        print(f"  [FAIL] python: {m} not installed")
        missing.append(m)
if missing:
    print(f"         → pip install {' '.join(missing)}")
PY

# ---- The support files SExtractor ships with --------------------------
echo
echo "----------------------------------------------"
echo " Where does SExtractor keep its default files?"
echo "----------------------------------------------"
FOUND=$(dpkg -L source-extractor 2>/dev/null | grep -E "default.nnw" | head -1)
if [ -n "$FOUND" ]; then
    echo "  Found in: $(dirname "$FOUND")"
    echo "  You will need to copy default.nnw and a *.conv kernel from there."
else
    echo "  Not installed via apt. Try:"
    echo "     find / -name 'default.nnw' 2>/dev/null"
fi

# ---- Data -------------------------------------------------------------
echo
echo "----------------------------------------------"
echo " Data"
echo "----------------------------------------------"
for b in U G R; do
    for suf in "" ".weight"; do
        f="data/HYDRA_D_0003_${b}${suf}.fits"
        if [ -f "$f" ]; then
            printf "  [ok]   %-40s %s\n" "$f" "$(du -h "$f" | cut -f1)"
        else
            echo "  [FAIL] missing: $f"
            echo "         → bash scripts/00_get_data.sh"
            FAIL=1
        fi
    done
done
echo "  [note] zero points are in the README (section 0), not a file."

echo
if [ $FAIL -eq 0 ]; then
    echo "=============================================="
    echo " Everything is in place. See you Thursday."
    echo "=============================================="
else
    echo "=============================================="
    echo " Something is missing. Fix it BEFORE the"
    echo " session — we will not have time in the room."
    echo "=============================================="
    exit 1
fi
