<!-- LANGUAGE -->
**English** · [Español](README.es.md) · [Português](README.pt.md)

---

# Building Astronomical Catalogs with Source Extractor

**Hands-on Activity 2 — S-PLUS School**
Gissel Montaguth

---

## What you will do today

You will build a photometric catalog of a real S-PLUS field, in two bands, and you
will use it to separate stars from galaxies.

But that is not really the point. The point is this:

> **A catalog is not the truth. It is a measurement, and it contains decisions.**

Every parameter you set today is a decision. By the end of this session I want you to
be able to say, for each one: *what did I choose, and why?*

**I am not giving you the configuration files.** You are going to build them. That is
most of what this session is.

---

## 0 · Get the data

Clone the repository (code + configs), then download the images from the
**Release** (they are too large for git).

```bash
git clone https://github.com/GMontaguth/splus-sextractor-workshop.git
cd splus-sextractor-workshop
mkdir -p data
```

Download the four FITS files, either with the script or by hand:

```bash
# either — run the helper
bash scripts/00_get_data.sh

# or — download them one by one
BASE=https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data
cd data
wget $BASE/HYDRA_D_0003_G.fits
wget $BASE/HYDRA_D_0003_G.weight.fits
wget $BASE/HYDRA_D_0003_R.fits
wget $BASE/HYDRA_D_0003_R.weight.fits
cd ..
```

You can also just click them in the browser:
[G](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_G.fits) ·
[G weight](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_G.weight.fits) ·
[R](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_R.fits) ·
[R weight](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_R.weight.fits)

These are 2000 × 2000 cutouts from S-PLUS iDR6, **already uncompressed** (the S-PLUS
frames ship tile-compressed, which SExtractor 2.25 cannot read — that has been handled
for you).

### The zero points

You will need these when you measure magnitudes. **They are NOT a single number** — in
iDR6 the ZP is a spatial model that varies across the field. Below is the median and the
scatter of that variation:

| band | median ZP | std (spatial scatter) |
|---|---|---|
| `g` | 22.920 | 0.012 |
| `r` | 22.784 | 0.013 |

Use the median as your `MAG_ZEROPOINT`. But **look at that `std` column and think.** It
tells you how much the ZP wanders across the field. Is the median a safe approximation?
Be able to defend your answer.

> SExtractor does **not** compute zero points. It only applies them:
> `MAG = -2.5 log10(FLUX) + MAG_ZEROPOINT`. That number came from a calibration pipeline
> that ran long before you.

**Check that everything is there before you go any further:**

```bash
bash scripts/00_check_setup.sh
```

---

## 1 · Find the defaults

Before you can change a parameter, you have to know it exists.

### Where SExtractor keeps its defaults

SExtractor can print its own defaults. Two flags:

```bash
sex -d           # the short list — the parameters you normally touch
sex -dd          # the FULL list — everything, with comments
```

Try both. Notice how much bigger `-dd` is.

**Save yourself a copy:**

```bash
mkdir -p config
sex -d  > config/default.sex
sex -dd > config/default.sex.full     # keep this as a reference
```

Open `config/default.sex.full` and read it. Do not skim it — *read it*. You will spend
the rest of the day inside this file.

### The other three files

SExtractor needs three more files, and they ship with the installation. **Find them.**

```bash
# if you installed via apt:
dpkg -L source-extractor | grep -E "\.param|\.conv|\.nnw"

# if you compiled from source, used conda, or loaded a module, try:
find / -name "default.nnw" 2>/dev/null
find / -name "*.conv" 2>/dev/null | head
```

Copy what you need into `config/`:

```bash
cp <path>/default.nnw          config/
cp <path>/gauss_2.0_5x5.conv   config/
cp <path>/gauss_2.5_5x5.conv   config/     # you may want this one later
```

**What each file is for:**

| File | What it is | Do you edit it? |
|---|---|---|
| `default.sex` | run parameters | **always** |
| `default.param` | **which columns you want in the output** | **always** |
| `*.conv` | the filtering kernel | you *choose* one, you don't edit it |
| `default.nnw` | the trained neural net behind `CLASS_STAR` | never |

### One thing you must add by hand: the weight map

The weight-map parameters are sometimes **not** in the default `default.sex`. Open the
file and add this block, so SExtractor knows to use the weight image:

```
#------------------------------- Weighting -----------------------------------
WEIGHT_TYPE      MAP_WEIGHT
WEIGHT_IMAGE     data/HYDRA_D_0003_R.weight.fits
```

Without it, SExtractor assumes uniform noise, and your detections at the noisy borders
of the field are not what they claim to be.

### Where PSFEx keeps its defaults

Same idea:

```bash
psfex -d  > config/default.psfex
psfex -dd > config/default.psfex.full
```

Read it too. It is shorter, and about half of it is check-plot options.

---

## 2 · Read the header before you write the config

Half the parameters in `default.sex` are not free choices — they are facts about your
image. Go get them.

```bash
python3 scripts/01_read_header.py
```

This prints the keywords you need. Write down the four that matter:

| Header keyword | Goes into | Why |
|---|---|---|
| `FWHMMEAN` | `SEEING_FWHM` **and** your choice of `FILTER_NAME` | in arcsec |
| `SATURATE` | `SATUR_LEVEL` | **the default is 50000. Yours is not.** |
| `GAIN` | `GAIN` | |
| pixel scale | `PIXEL_SCALE` | S-PLUS: 0.55 ″/px |

> ⚠️ **`SATUR_LEVEL` is the one people get wrong.** If you leave it at the default,
> saturated stars are never flagged as saturated, and `FLAGS = 4` never appears in your
> catalog. You will not notice until it is too late.

**Convert the seeing to pixels yourself.** You need it to pick a kernel:

```
FWHM [px] = FWHMMEAN ["] / 0.55 ["/px]
```

Now look at the kernel names — `gauss_2.0_5x5.conv`, `gauss_2.5_5x5.conv`. **The number
is the FWHM in pixels.** Pick the one that best fits your two bands.

Why? Convolution before detection is a **matched filter**: if the kernel has the shape
of the source you are looking for, you maximise the detection S/N. And for a point
source, the source you are looking for *is the PSF*.

### Now put your values into `default.sex`

We will use **r as our reference band** — it is deep and has the best signal-to-noise,
so it is the one we detect on.

Open the config and set the values you just found. Either open `config/default.sex` in
your editor, or from the terminal:

```bash
gedit config/default.sex &
```

Set `SEEING_FWHM`, `SATUR_LEVEL`, `GAIN`, `PIXEL_SCALE` and your chosen `FILTER_NAME`.

**And remember to give the paths** to your configuration files — `PARAMETERS_NAME`,
`FILTER_NAME`, `STARNNW_NAME`. For example:

```
STARNNW_NAME     config/default.nnw
```

---

## 3 · The zero point

You already saw the zero points in section 0. **The S-PLUS iDR6 zero point is not a
number — it is a spatial model that varies across the field.** The table gave you the
median and the scatter (`std`) of that variation.

Look at the `std` column again and think:

- Is a single median ZP good enough for what you are doing?
- Is the scatter the same in every band?

Since this is a hands-on exercise to understand how the tool works, **for today we will
use the median zero point for each image.** But keep in mind that this is an
approximation — the real ZP varies across the field, and a science-grade measurement
would need to account for that.

> SExtractor does **not** compute zero points. It only applies them:
> `MAG = -2.5 log10(FLUX) + MAG_ZEROPOINT`.
> That number came from a calibration pipeline that ran long before you. Know where it
> came from.

---

## 4 · Write your `default.param`

This is the file everyone forgets, and it is the one that decides what you actually get.

> **If a column is not in `default.param`, it does not appear in your catalog — even
> though SExtractor computed it.** It is not a bug. You did not ask for it.

Look at the shipped `default.param`: everything is commented out with `#`. It is a menu,
not a config.

**The format is dead simple: one column name per line.** A `#` at the start of a line
comments it out. No commas, no quotes, no header. That's it.

So a minimal `config/default.param` looks like this:

```
NUMBER
X_IMAGE
Y_IMAGE
ALPHA_J2000
DELTA_J2000
MAG_AUTO
MAGERR_AUTO
FLUX_RADIUS
CLASS_STAR
FLAGS
```

That already runs. **Now build yours up from there.** You need, at minimum:

- an identifier and a position (pixel *and* sky) — the block above has these
- a magnitude **and** its error
- the shape (you will need `FLUX_RADIUS` — trust me)
- `FLAGS` ← **never leave this out**
- `CLASS_STAR`

**Decide which flux you want**, and be able to say why:

| | What it is | When |
|---|---|---|
| `MAG_ISO` | pixels above the threshold | **never for colours** — the threshold differs in every band |
| `MAG_APER` | fixed circular aperture | **the basis of multi-band photometry** |
| `MAG_AUTO` | Kron ellipse | total-flux proxy (~94% of a typical profile) |
| `MAG_PETRO` | Petrosian aperture | comparison with SDSS |

Add the ones you chose to your file, each on its own line (`MAG_APER`, `MAGERR_APER`,
and so on).

For a vector output like three apertures, the syntax is `MAG_APER(3)` — and **the number
in the parentheses must match how many values you put in `PHOT_APERTURES`.**

`PHOT_APERTURES` is a **diameter in pixels**. If you want a 3″ aperture:
`3 / 0.55 = 5.45 px`.

For now, those basic columns are enough to build a first catalog — just to understand
the tool and choose your best configuration. Keep the fuller list in mind for later,
when you build the *official* catalog.

> Stuck on which columns exist? Run `sex -dd` — the full parameter list is in there,
> commented, with a one-line description of each. And `solutions/default.param` has a
> complete worked version if you need it.

---

## 5 · Your first run

Now edit `config/default.sex` with everything you worked out above.

We also want to *see* whether it worked — what the sky model looks like and which
sources it identified. So we will ask for two **check-images**: the segmentation map and
the background. Find `CHECKIMAGE_TYPE` and put both options there, and in
`CHECKIMAGE_NAME` put the two FITS filenames you want.

Now we can run SExtractor. This catalog — which we will call `r_first.cat` — is only for
exploring the parameters. Type this in the terminal:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME r_first.cat \
    -CATALOG_TYPE FITS_1.0
```

**Note:** anything in the config file can be overridden on the command line with
`-PARAM value`. This is not a convenience — it is what makes many bands tractable with
one config file.

### Did it work?

Look at what SExtractor printed:

```
(M+D) Background: ...   RMS: ...   / Threshold: ...
      Objects: detected N / sextracted M
```

**Check the arithmetic yourself:** is `Threshold` equal to `DETECT_THRESH × RMS`? It
should be. That is the moment where "1.5 sigma" becomes a concrete number of counts.

### Now LOOK at it. This is not optional.

```bash
ds9 data/HYDRA_D_0003_R.fits seg.fits bkg.fits \
    -zscale -lock frame image -lock scale yes -tile
```

**Three things to find:**

1. **The borders of the segmentation map.** Are they clean? If they are, your weight map
   is doing its job. Comment out `WEIGHT_IMAGE`, run again, and look at the difference.
2. **The background model.** Is it flat? (It is not.) Can you see the halos of the
   bright stars *inside* your sky model?
3. **Zoom into a bright, saturated star in the segmentation map.** Count the objects.

That last one is worth sitting with. Come find me when you see it.

---

## 6 · Exploration — this is the actual exercise

The point of this session is not to produce *a* catalog. It is to understand that
different parameters produce **different catalogs of the same sky**.

You run these by hand. Type the command, change one parameter, run it again, and
compare. Everything in the config can be overridden on the command line — so you never
have to edit a file to try a value.

### 6a · `DETECT_THRESH` and `DETECT_MINAREA`

Run **at least three combinations of your own choosing.** You can change the values
directly in `default.sex`, or pass them on the command line to override the config file.
For example, a loose one:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DETECT_THRESH 1.5 -DETECT_MINAREA 3 \
    -CATALOG_NAME thresh_loose.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME seg_loose.fits
```

and a strict one:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DETECT_THRESH 3.0 -DETECT_MINAREA 5 \
    -CATALOG_NAME thresh_strict.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME seg_strict.fits
```

For each run, **read the last line SExtractor prints** — it tells you how many objects
were detected and how many survived. Write the numbers down.

Then look at the two segmentation maps side by side:

```bash
ds9 seg_loose.fits seg_strict.fits \
    -lock frame image -tile
```

**There is no correct answer.** Hunting a transient counterpart? You want completeness.
Measuring a luminosity function? Spurious sources at the faint end will destroy you.

**The tool does not decide for you.**

### 6b · `DEBLEND_MINCONT`

Find the largest, most extended galaxy in your cutout (open the image in DS9 and look).
Run the same field twice, changing only `DEBLEND_MINCONT`:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DEBLEND_MINCONT 0.0001 \
    -CATALOG_NAME deb_aggressive.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME seg_aggressive.fits
```

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DEBLEND_MINCONT 0.1 \
    -CATALOG_NAME deb_conservative.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME seg_conservative.fits
```

Look at the segmentation map around that galaxy both times. Zoom in.

Does it fragment? **Should it?** (That depends entirely on what you are trying to
measure — which is the whole point.)

---

Once you have found the parameters you are happy with for these, set them **directly in
`default.sex`**, so you do not have to keep passing them on the command line for the rest
of the tutorial.

## 7 · PSFEx

As we discussed in the lecture, a good PSF is fundamental to separating an extended
source from a point source — and it also gives you a good PSF aperture for measuring the
magnitudes of stars. For star/galaxy separation, you have two options:

`CLASS_STAR` is a neural network. It works — until the S/N drops, and then it collapses
toward 0.5. It stops knowing, and it does not tell you.

`SPREAD_MODEL` does not collapse. But it needs to know what a star looks like **at that
exact position, in that exact image**. That is what PSFEx builds.

### PSFEx does not read your image. It reads a SExtractor catalog.

Which means the workflow is:

```
SExtractor (pass 1)  →  prepsfex.cat   (FITS_LDAC, with VIGNET)
        ↓
PSFEx                →  *.psf
        ↓
SExtractor (pass 2)  →  final catalog with SPREAD_MODEL
```

### 7a · Write `prepsfex.param`

**This is a different `.param` from your science one.** It is short. It must contain:

```
VIGNET(35,35)
```

**`VIGNET` is the whole reason this pass exists.** It tells SExtractor to save a pixel
cutout around every source — because PSFEx never opens your image, so the pixels have to
travel *inside the catalog*.

You also need: positions, `FLUX_RADIUS`, one aperture flux and its error, `ELONGATION`,
`SNR_WIN`, and `FLAGS`.

> **Important:** the aperture you choose must be a **FIXED aperture, not Kron** — you
> want something that does not depend on the measured morphology. For example, a 3″
> aperture.

Look at `psfex -dd` and find `PHOTFLUX_KEY`. **Whatever you name in your `.param` must
match what PSFEx expects to read.** If they disagree, PSFEx dies with an unhelpful error
(usually a segmentation fault).

Then run SExtractor to produce the catalog PSFEx will work from — call it, for example,
`prepsfex.cat`.

### 7b · Pass 1

Two things make this run different from your science run:

- `-CATALOG_TYPE FITS_LDAC` — **mandatory.** PSFEx reads nothing else. (If you forget
  this, PSFEx crashes with a segmentation fault and no useful message.)
- a **higher** `DETECT_THRESH` — this is not the science run. For fitting a PSF you want
  *good stars*, not completeness. Try 5σ.

Also: if your `.param` says `FLUX_APER(1)`, then `PHOT_APERTURES` must have **exactly
one** value.

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME prepsfex.cat -CATALOG_TYPE FITS_LDAC \
    -PARAMETERS_NAME config/prepsfex.param \
    -DETECT_THRESH 5.0 -ANALYSIS_THRESH 5.0 -PHOT_APERTURES 10
```

Your catalog will be large. That is the `VIGNET` cutouts. Expected.

**Check that it really came out as LDAC** before you feed it to PSFEx:

```bash
python3 -c "from astropy.io import fits; print([h.name for h in fits.open('prepsfex.cat')])"
```

You want to see `LDAC_IMHEAD` and `LDAC_OBJECTS`. If you see a plain `OBJECTS`, the
`-CATALOG_TYPE FITS_LDAC` did not take — that is the #1 cause of the segfault.

### 7c · Run PSFEx

Edit `config/default.psfex`. The parameters that matter:

| | What it controls | Think about |
|---|---|---|
| `PSF_SIZE` | model size in pixels | **must be smaller than your VIGNET** |
| `PSFVAR_DEGREES` | polynomial degree of the spatial variation | 0 = constant PSF (fast, and false). 2 = sensible. 4 = overfits unless you have many stars |
| `SAMPLE_FWHMRANGE` | which FWHM counts as a star | **in PIXELS.** Does your seeing fall inside it? |
| `SAMPLE_MINSNR` | how faint a star can be | faint stars → noisy PSF |
| `SAMPLE_MAXELLIP` | how elongated | this is your anti-galaxy filter |

```bash
psfex prepsfex.cat -c config/default.psfex
```

### 7d · Read the output. Do not skip this.

PSFEx prints a line like:

```
accepted/total   samp.   chi2/dof   FWHM   ellip.   resi.
```

**Judge your own PSF:**

- **`chi2/dof`** — should be near 1. If it is 3, your model does not describe your data.
- **`FWHM`** — does it match the header? (It should.)
- **`ellip.`** — near 0 means round. A large value means a tracking or flexure problem.
- **`accepted`** — you need roughly 10 stars per polynomial term. Degree 2 in (x,y) has
  6 terms → **you want 60+ stars**. Do you have them?

Then look at the check-plots. `CHECKPLOT_DEV` — try `PNG` first; if your PLPlot build
does not have it, use `SVG` or `PSC`.

**The one that matters most is `SAMPLES`** — the stars PSFEx actually used. If there are
galaxies in there, your PSF is contaminated. Go back and tighten `SAMPLE_MINSNR` and
`SAMPLE_MAXELLIP`.

> A bad PSF gives you a bad `SPREAD_MODEL` and a bad `MAG_PSF` — **silently**. Nothing
> crashes. You just get wrong answers.

### 7e · Pass 2

Copy your science `.param`, add `SPREAD_MODEL`, `SPREADERR_MODEL`, `MAG_PSF`,
`MAGERR_PSF`. Run SExtractor again with `-PSF_NAME <your>.psf`.

**This will be slow.** For every source, SExtractor now evaluates the polynomial to build
the PSF at that position, then does an iterative fit. That is why it costs what it costs.

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME final.cat \
    -CATALOG_TYPE FITS_1.0 \
    -PARAMETERS_NAME config/final.param \
    -PSF_NAME prepsfex.psf \
    -FILTER_NAME config/gauss_2.0_5x5.conv \
    -STARNNW_NAME config/default.nnw \
    -WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits
```

---

## 8 · Two bands — and the mistake you are about to make

Time for a quick experiment. Normally, when we want a catalog that characterizes stars
and galaxies, the cleanest way is to use the PSF — but as you just saw, that is slow. So
we will do a fast run with **two filters**, to understand how you work when you have more
than one band, because we almost never work with a single filter.

There are two ways to build the catalogs: the **wrong** way and the **right** way.

### The wrong way (do it anyway — you need to see it break)

Run SExtractor **two times, independently**, once per band. Each band detects and
measures on its own. For this experiment, the `AUTO` aperture alone is enough — you can
drop the other apertures. Use the zero point for that band (from the table in section 0):

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME single_R.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.784 \
    -WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits
```

Remember that in `default.sex` we wrote `GAIN`, `SATUR_LEVEL` and `SEEING_FWHM` for the
**r** band — so for **g** you have to change them:

```bash
sex data/HYDRA_D_0003_G.fits -c config/default.sex \
    -CATALOG_NAME single_G.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.920 \
    -GAIN <G_gain> \
    -SATUR_LEVEL <G_satur> \
    -SEEING_FWHM <G_seeing> \
    -WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE data/HYDRA_D_0003_G.weight.fits
```

Open the two catalogs in TOPCAT. What do you see? Are they the same?

### The right way: dual-image mode

The syntax is two images separated by a **comma, no space**:

```bash
sex detection.fits,measurement.fits -c config/default.sex
```

Sources are **detected** on the first image, **measured** on the second.

Detect on `r` — it is deep and has the best seeing. Then measure through *those same
apertures*, at *those same positions*, in both bands. So you run it twice, and the
**first** image is always `r`:

```bash
# detect on R, measure on G
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_G.fits -c config/default.sex \
    -CATALOG_NAME dual_G.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.920 \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_G.weight.fits
```

```bash
# detect on R, measure on R (yes, R on itself)
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME dual_R.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.784 \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_R.weight.fits
```

Note that in dual mode `WEIGHT_TYPE` and `WEIGHT_IMAGE` each take **two**
comma-separated values — one for the detection image, one for the measurement image.

Because both bands were detected on `r`, **row *i* is the same source in both catalogs.**
No cross-matching needed. That is the point.

### Why this is the whole game

The Kron aperture is **adaptive** — its size depends on the shape measured *in that
image*. The seeing in `g` is different, so the source can look fatter, so **the ellipse
comes out a different size**. More area, more flux. Your colour now has a bias that has
nothing to do with the star.

And it is worse than that: a faint source detected in `r` may **not be detected at all**
in `g`. Two sources cleanly separated in `r` may be **a single blob** in `g`.
There is nothing to cross-match.

**Same aperture, same position, every band. Without that, there is no colour.**

Open the catalogs in TOPCAT again. What do you see now? Are they the same?

---

## If you get stuck

`solutions/` has a worked version of every step. **Use it if you are stuck for more than
ten minutes** — being stuck is not the exercise.

But do the thinking first. The commands are the easy part.

---

## Reference

- SExtractor manual — https://sextractor.readthedocs.io
- PSFEx manual — https://psfex.readthedocs.io
- Bertin & Arnouts 1996, A&AS 117, 393
