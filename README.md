<!-- LANGUAGE -->
**English** · [Español](README.es.md) · [Português](README.pt.md)

---

# Building Astronomical Catalogs with Source Extractor

**Hands-on Activity 2 — S-PLUS School**
Gissel Montaguth

---

## What you will do today

You will build a photometric catalog of a real S-PLUS field, in three bands, and you
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

Download the six FITS files, either with the script or by hand:

```bash
# either — run the helper
bash scripts/00_get_data.sh

# or — download them one by one
BASE=https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data
wget $BASE/HYDRA_D_0003_U.fits
wget $BASE/HYDRA_D_0003_U.weight.fits
wget $BASE/HYDRA_D_0003_G.fits
wget $BASE/HYDRA_D_0003_G.weight.fits
wget $BASE/HYDRA_D_0003_R.fits
wget $BASE/HYDRA_D_0003_R.weight.fits
cd ..
```

You can also just click them in the browser:
[U](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_U.fits) ·
[U weight](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_U.weight.fits) ·
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
| `u` | 20.054 | **0.035** |
| `g` | 22.920 | 0.012 |
| `r` | 22.784 | 0.013 |

Use the median as your `MAG_ZEROPOINT`. But **look at that `std` column and think.**
The scatter in `u` is almost three times the scatter in `g` and `r`. Is the median a
safe approximation in every band? Be able to defend your answer.

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

# if you compiled from source or used conda, try:
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
is the FWHM in pixels.** Pick the one closest to yours escoge el que mejor se adapte a l9os tres filtros.

Why? Convolution before detection is a **matched filter**: if the kernel has the shape
of the source you are looking for, you maximise the detection S/N. And for a point
source, the source you are looking for *is the PSF*.

Ahora abre el archivo y cambiamos los parametros deacurdo a lo que acabaste de encontrar para el filtro R que va se nuestro filtro estandar porque es el que mejor señal ruido tiene, puedes simplemente ir a la carpeta config y abrir el archivo o puedes escrivir el la terminal:


```
> gedit config/default.sex & 
```

Recuerden agregarle el camino a donde estan los archivos de configuracion como PARAMETERS_NAME, FILTER_NAME, STARNNW_NAME por ejemplo: STARNNW_NAM  config/default.nnw

---

## 3 · The zero point

You already saw the zero points in section 0. **The S-PLUS iDR6 zero point is not a
number — it is a spatial model that varies across the field.** The table gave you the
median and the scatter (`std`) of that variation.

Look at the `std` column again and pienda:

- Is a single median ZP good enough for what you are doing?
- Is the answer the same in `u` (std 0.035) as it is in `r` (std 0.013)?

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

Por ahora esas basicas funciona para crear un primer catalogo basico que luego vamos a usar pra buscar las PSFs de nuestras imagenes, pero ten encunta esto en el futuo para crear el catalogo oficial 

> Stuck on which columns exist? Run `sex -dd` — the full parameter list is in there,
> commented, with a one-line description of each. And `solutions/default.param` has a
> complete worked version if you need it.

---

## 5 · Your first run

Now edit `config/default.sex` with everything you worked out above, ademas como queremos ver que tambien funciona queremos ver como es la imagen del cielo y cuales son las funtes que esta identificamods vamos a pedsir dos imagenes de chequeo 
que son la imagen de segmentacuon y backgroup vamnos a pedirle a sextractor que dos de las dops uamghenes para esto busca el CHECKIMAGE_TYPE y coloca las dos obciones y en CHECKIMAGE_NAME va el nombre de las dos imagenes fits que queres.

ahora si podemos correr sextractor, este catalo que llamaremos r_first.cat, estos cataklogos simplemente son para explorar los parametros de sextractor, para corrrer escribimos esto en la termianal: 

```
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME cat/r_first.cat \
    -CATALOG_TYPE FITS_1.0 \
```

**Note:** anything in the config file can be overridden on the command line with
`-PARAM value`. This is not a convenience — it is what makes twelve bands tractable
with one config file.

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
ds9 data/HYDRA_D_0003_R.fits check/seg.fits check/bkg.fits \
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

Run **at least three combinations of your own choosing.** For example, a loose one:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DETECT_THRESH 1.5 -DETECT_MINAREA 3 \
    -CATALOG_NAME cat/thresh_loose.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME check/seg_loose.fits
```

and a strict one:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DETECT_THRESH 3.0 -DETECT_MINAREA 5 \
    -CATALOG_NAME cat/thresh_strict.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME check/seg_strict.fits
```

For each run, **read the last line SExtractor prints** — it tells you how many objects
were detected and how many survived. Write the numbers down.

Then look at the two segmentation maps side by side:

```bash
ds9 check/seg_loose.fits check/seg_strict.fits \
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
    -CATALOG_NAME cat/deb_aggressive.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME check/seg_aggressive.fits
```

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DEBLEND_MINCONT 0.1 \
    -CATALOG_NAME cat/deb_conservative.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME check/seg_conservative.fits
```

Look at the segmentation map around that galaxy both times. Zoom in.

Does it fragment? **Should it?** (That depends entirely on what you are trying to
measure — which is the whole point.)

---

## 7 · PSFEx

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

Look at `psfex -dd` and find `PHOTFLUX_KEY`. **Whatever you name in your `.param` must
match what PSFEx expects to read.** If they disagree, PSFEx dies with an unhelpful error.

### 7b · Pass 1

Two things make this run different from your science run:

- `-CATALOG_TYPE FITS_LDAC` — **mandatory.** PSFEx reads nothing else.
- a **higher** `DETECT_THRESH` — this is not the science run. For fitting a PSF you want
  *good stars*, not completeness. Try 5σ.

Also: if your `.param` says `FLUX_APER(1)`, then `PHOT_APERTURES` must have **exactly
one** value.

Your catalog will be large. That is the `VIGNET` cutouts. Expected.

### 7c · Run PSFEx

Edit `config/default.psfex`. The parameters that matter:

| | What it controls | Think about |
|---|---|---|
| `PSF_SIZE` | model size in pixels | **must be smaller than your VIGNET** |
| `PSFVAR_DEGREES` | polynomial degree of the spatial variation | 0 = constant PSF (fast, and false). 2 = sensible. 4 = overfits unless you have many stars |
| `SAMPLE_FWHMRANGE` | which FWHM counts as a star | **in PIXELS.** Does your seeing fall inside it? |
| `SAMPLE_MINSNR` | how faint a star can be | faint stars → noisy PSF |
| `SAMPLE_MAXELLIP` | how elongated | this is your anti-galaxy filter |
| `SAMPLE_FLAGMASK` | which FLAGS to reject | **a saturated star has a flat core. If it gets in, your PSF is a lie.** |

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

---

## 8 · Three bands — and the mistake you are about to make

Now do `u`, `g`, `r`.

### The wrong way (do it anyway — you need to see it break)

Run SExtractor **three times, independently**, once per band. Each band detects and
measures on its own. Use the zero point for that band (from the table in section 0):

```bash
sex data/HYDRA_D_0003_U.fits -c config/default.sex \
    -CATALOG_NAME cat/single_U.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT <ZP_U> \
    -WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE data/HYDRA_D_0003_U.weight.fits
```

Repeat for `G` and `R`, changing the band letter and the zero point each time.
Then you have to cross-match the three catalogs by position and compute colours — which
is exactly the problem.

### The right way: dual-image mode

The syntax is two images separated by a **comma, no space**:

```bash
sex detection.fits,measurement.fits -c config/default.sex
```

Sources are **detected** on the first image, **measured** on the second.

Detect on `r` — it is deep and has the best seeing. Then measure through *those same
apertures*, at *those same positions*, in all three bands. So you run it three times, and
the **first** image is always `r`:

```bash
# detect on R, measure on U
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_U.fits -c config/default.sex \
    -CATALOG_NAME cat/dual_U.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT <ZP_U> \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_U.weight.fits
```

```bash
# detect on R, measure on G
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_G.fits -c config/default.sex \
    -CATALOG_NAME cat/dual_G.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT <ZP_G> \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_G.weight.fits
```

```bash
# detect on R, measure on R (yes, R on itself)
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME cat/dual_R.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT <ZP_R> \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_R.weight.fits
```

Note that in dual mode `WEIGHT_TYPE` and `WEIGHT_IMAGE` each take **two**
comma-separated values — one for the detection image, one for the measurement image.

Because every band was detected on `r`, **row *i* is the same source in all three
catalogs.** No cross-matching needed. That is the point.

### Why this is the whole game

The Kron aperture is **adaptive** — its size depends on the shape measured *in that
image*. The seeing in `u` is worse, so the source looks fatter, so **the ellipse comes
out bigger**. More area, more flux. Your colour now has a bias that has nothing to do
with the star.

And it is worse than that: a faint source detected in `r` may **not be detected at all**
in `u`. Two sources cleanly separated in `r` may be **a single blob** in `u`.
There is nothing to cross-match.

**Same aperture, same position, every band. Without that, there is no colour.**

---

## 9 · The deliverable

Make the colour–colour diagram — `(u−g)` vs `(g−r)` — **twice**: once from your
dual-mode catalogs, once from the band-by-band catalogs. This one script reads both sets
and plots them side by side:

```bash
python3 scripts/02_color_color.py
```

Colour the points by `SPREAD_MODEL`.

**Look at the two diagrams.** The stellar locus is wider in one of them. That extra
scatter is not photometric noise. **It is your apertures disagreeing with each other.**

Nothing crashed. Both catalogs look perfectly respectable in TOPCAT.

One of them just has colours that mean nothing.

---

## 10 · Optional — if you finished early

You made your colour–colour diagram with `MAG_APER`, not `MAG_PSF`. That was
deliberate: `MAG_PSF` is only valid for **point sources**, and your diagram has
galaxies in it. Fitting a PSF to a galaxy gives you a meaningless number.

So when *is* `MAG_PSF` worth the trouble? This experiment answers that, on stars.

```bash
python3 scripts/03_psf_vs_aper.py
```

For an **isolated** star, `MAG_APER` and `MAG_PSF` agree — a star *is* the PSF, so
integrating a fixed aperture and fitting the PSF give the same flux.

For a star with a close **neighbour**, they diverge. The fixed aperture happily
collects the neighbour's light too, so `MAG_APER` comes out too bright. The PSF fit
knows what a star is shaped like and is not fooled.

**That is the entire reason PSF photometry exists: crowded fields.** Not for the
isolated stars — for the crowded ones.

---

## What to hand in

1. **Your `default.sex`**, with a short justification for each parameter you changed
   from the default. *"Why did you pick that `BACK_SIZE`?"* is a fair question.

2. **Your final catalog** (`.fits`), with the three bands measured through identical
   apertures.

3. **Two figures:**
   - the colour–colour diagram, coloured by `SPREAD_MODEL`
   - one diagnostic of your own choosing that convinced you something was working (or
     wasn't)

4. **Two sentences on what went wrong and how you diagnosed it.**

**Point 4 is the one I actually grade.** Everything else can be produced by copying
commands. Point 4 cannot.

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
