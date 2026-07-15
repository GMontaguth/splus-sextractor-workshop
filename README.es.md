<!-- LANGUAGE -->
[English](README.md) · **Español** · [Português](README.pt.md)

---

# Construyendo catálogos astronómicos con Source Extractor

**Actividad práctica 2 — Escuela S-PLUS**
Gissel Montaguth

---

## Lo que vas a hacer hoy

Vas a construir un catálogo fotométrico de un campo real de S-PLUS, en tres bandas, y
lo vas a usar para separar estrellas de galaxias.

Pero ese no es realmente el punto. El punto es este:

> **Un catálogo no es la verdad. Es una medición, y contiene decisiones.**

Cada parámetro que fijes hoy es una decisión. Al final de la sesión quiero que puedas
decir, para cada uno: *¿qué elegí, y por qué?*

**No te voy a dar los archivos de configuración.** Los vas a construir tú. Eso es la
mayor parte de esta sesión.

---

## 0 · Consigue los datos

Clona el repositorio (código + configs), y luego descarga las imágenes del
**Release** (son demasiado grandes para git).

```bash
git clone https://github.com/GMontaguth/splus-sextractor-workshop.git
cd splus-sextractor-workshop
mkdir -p data && cd data
```

Descarga los seis archivos FITS, con el script o a mano:

```bash
# o bien — corre el ayudante
bash scripts/00_get_data.sh

# o bien — descárgalos uno por uno
BASE=https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data
wget $BASE/HYDRA_D_0003_U.fits
wget $BASE/HYDRA_D_0003_U.weight.fits
wget $BASE/HYDRA_D_0003_G.fits
wget $BASE/HYDRA_D_0003_G.weight.fits
wget $BASE/HYDRA_D_0003_R.fits
wget $BASE/HYDRA_D_0003_R.weight.fits
cd ..
```

También puedes hacer clic desde el navegador:
[U](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_U.fits) ·
[U weight](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_U.weight.fits) ·
[G](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_G.fits) ·
[G weight](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_G.weight.fits) ·
[R](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_R.fits) ·
[R weight](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_R.weight.fits)

Son cutouts de 2000 × 2000 de S-PLUS iDR6, **ya descomprimidos** (los frames de S-PLUS
vienen comprimidos con tile-compression, que SExtractor 2.25 no lee — eso ya está
resuelto para ti).

### Los zero points

Los vas a necesitar para medir magnitudes. **No son un solo número** — en iDR6 el ZP es
un modelo espacial que varía a través del tile. Abajo está la mediana y la dispersión de
esa variación:

| banda | ZP mediano | std (dispersión espacial) |
|---|---|---|
| `u` | 20.054 | **0.035** |
| `g` | 22.920 | 0.012 |
| `r` | 22.784 | 0.013 |

Usa la mediana como tu `MAG_ZEROPOINT`. Pero **mira esa columna `std` y piensa.** La
dispersión en `u` es casi tres veces la de `g` y `r`. ¿La mediana es una aproximación
segura en todas las bandas? Ten claro por qué.

> SExtractor **no** calcula zero points. Solo los aplica:
> `MAG = -2.5 log10(FLUX) + MAG_ZEROPOINT`. Ese número vino de un pipeline de
> calibración que corrió mucho antes que tú.

**Verifica que todo esté antes de seguir:**

```bash
bash scripts/00_check_setup.sh
```

---

## 1 · Encuentra los valores por defecto

Antes de cambiar un parámetro, tienes que saber que existe.

### Dónde guarda SExtractor sus valores por defecto

SExtractor puede imprimir sus propios valores por defecto. Dos flags:

```bash
sex -d           # la lista corta — los parámetros que normalmente tocas
sex -dd          # la lista COMPLETA — todo, con comentarios
```

Prueba las dos. Fíjate cuánto más grande es `-dd`.

**Guárdate una copia:**

```bash
mkdir -p config
sex -d  > config/default.sex
sex -dd > config/default.sex.full     # guárdalo como referencia
```

Abre `config/default.sex.full` y léelo. No lo ojees — *léelo*. Vas a pasar el resto del
día dentro de este archivo.

### Los otros tres archivos

SExtractor necesita tres archivos más, y vienen con la instalación. **Encuéntralos.**

```bash
# si instalaste con apt:
dpkg -L source-extractor | grep -E "\.param|\.conv|\.nnw"

# si compilaste o usaste conda, prueba:
find / -name "default.nnw" 2>/dev/null
find / -name "*.conv" 2>/dev/null | head
```

Copia lo que necesites a `config/`:

```bash
cp <ruta>/default.nnw          config/
cp <ruta>/gauss_2.0_5x5.conv   config/
cp <ruta>/gauss_4.0_7x7.conv   config/     # puede que lo quieras después
```

**Para qué sirve cada archivo:**

| Archivo | Qué es | ¿Lo editas? |
|---|---|---|
| `default.sex` | parámetros de ejecución | **siempre** |
| `default.param` | **qué columnas quieres en la salida** | **siempre** |
| `*.conv` | el kernel de filtrado | lo *eliges*, no lo editas |
| `default.nnw` | la red neuronal entrenada de `CLASS_STAR` | nunca |

### Dónde guarda PSFEx sus valores por defecto

Misma idea:

```bash
psfex -d  > config/default.psfex
psfex -dd > config/default.psfex.full
```

Léelo también. Es más corto, y la mitad son opciones de check-plots.

---

## 2 · Lee el header antes de escribir la config

La mitad de los parámetros de `default.sex` no son elecciones libres — son hechos sobre
tu imagen. Ve a buscarlos.

```bash
python3 scripts/01_read_header.py
```

Esto imprime los keywords que necesitas. Anota los cuatro que importan:

| Keyword del header | Va en | Por qué |
|---|---|---|
| `FWHMMEAN` | `SEEING_FWHM` **y** tu elección de `FILTER_NAME` | en arcsec |
| `SATURATE` | `SATUR_LEVEL` | **el default es 50000. El tuyo no.** |
| `GAIN` | `GAIN` | |
| escala de píxel | `PIXEL_SCALE` | S-PLUS: 0.55 ″/px |

> ⚠️ **`SATUR_LEVEL` es el que la gente se equivoca.** Si lo dejas en el default, las
> estrellas saturadas nunca se flaguean como saturadas, y `FLAGS = 4` nunca aparece en
> tu catálogo. No te vas a dar cuenta hasta que sea tarde.

**Convierte el seeing a píxeles tú mismo.** Lo necesitas para elegir el kernel:

```
FWHM [px] = FWHMMEAN ["] / 0.55 ["/px]
```

Ahora mira los nombres de los kernels — `gauss_2.0_5x5.conv`, `gauss_4.0_7x7.conv`.
**El número es el FWHM en píxeles.** Elige el más cercano al tuyo.

¿Por qué? La convolución antes de la detección es un **filtro adaptado (matched
filter)**: si el kernel tiene la forma de la fuente que buscas, maximizas el S/N de
detección. Y para una fuente puntual, la fuente que buscas *es la PSF*.

---

## 3 · El zero point

Ya viste los zero points en la sección 0. **El zero point de S-PLUS iDR6 no es un número
— es un modelo espacial que varía a través del tile.** La tabla te dio la mediana y la
dispersión (`std`) de esa variación.

Mira la columna `std` de nuevo y decide:

- ¿Un solo ZP mediano es suficiente para lo que estás haciendo?
- ¿La respuesta es la misma en `u` (std 0.035) que en `r` (std 0.013)?

**Sea lo que decidas, tienes que poder defenderlo.** Anótalo.

> SExtractor **no** calcula zero points. Solo los aplica:
> `MAG = -2.5 log10(FLUX) + MAG_ZEROPOINT`.
> Ese número vino de un pipeline de calibración que corrió mucho antes que tú. Sabe de
> dónde salió.

---

## 4 · Escribe tu `default.param`

Este es el archivo que todos olvidan, y es el que decide qué obtienes realmente.

> **Si una columna no está en `default.param`, no aparece en tu catálogo — aunque
> SExtractor la haya calculado.** No es un bug. No la pediste.

Mira el `default.param` que viene: todo está comentado con `#`. Es un menú, no una
config.

**Escribe el tuyo.** Necesitas, como mínimo:

- un identificador y una posición (píxel *y* cielo)
- una magnitud **y** su error
- la forma (vas a necesitar `FLUX_RADIUS` — confía)
- `FLAGS` ← **nunca lo dejes fuera**
- `CLASS_STAR`

**Decide qué flujo quieres**, y ten claro por qué:

| | Qué es | Cuándo |
|---|---|---|
| `MAG_ISO` | píxeles sobre el umbral | **nunca para colores** — el umbral difiere en cada banda |
| `MAG_APER` | apertura circular fija | **la base de la fotometría multibanda** |
| `MAG_AUTO` | elipse de Kron | proxy de flujo total (~94% de un perfil típico) |
| `MAG_PETRO` | apertura de Petrosian | comparación con SDSS |

Para una salida vectorial como tres aperturas, la sintaxis es `MAG_APER(3)` — y **el
número entre paréntesis debe coincidir con cuántos valores pongas en
`PHOT_APERTURES`.**

`PHOT_APERTURES` es un **diámetro en píxeles**. Si quieres una apertura de 3″:
`3 / 0.55 = 5.45 px`.

---

## 5 · Tu primera corrida

Ahora edita `config/default.sex` con todo lo que averiguaste, y corre:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME cat/r_first.cat \
    -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION,BACKGROUND \
    -CHECKIMAGE_NAME check/seg.fits,check/bkg.fits
```

**Nota:** cualquier cosa en el archivo de config se puede sobrescribir por línea de
comandos con `-PARAM valor`. No es una comodidad — es lo que hace manejable correr doce
bandas con una sola config.

### ¿Funcionó?

Mira lo que imprimió SExtractor:

```
(M+D) Background: ...   RMS: ...   / Threshold: ...
      Objects: detected N / sextracted M
```

**Verifica la aritmética tú mismo:** ¿es `Threshold` igual a `DETECT_THRESH × RMS`?
Debería. Ese es el momento en que "1.5 sigma" se vuelve un número concreto de cuentas.

### Ahora MÍRALO. Esto no es opcional.

```bash
ds9 data/HYDRA_D_0003_R.fits check/seg.fits check/bkg.fits \
    -zscale -lock frame image -lock scale yes -tile
```

**Tres cosas que buscar:**

1. **Los bordes del segmentation map.** ¿Están limpios? Si lo están, tu weight map está
   haciendo su trabajo. Comenta `WEIGHT_IMAGE`, corre de nuevo, y mira la diferencia.
2. **El modelo de fondo.** ¿Es plano? (No lo es.) ¿Puedes ver los halos de las estrellas
   brillantes *dentro* de tu modelo de cielo?
3. **Haz zoom en una estrella brillante y saturada en el segmentation map.** Cuenta los
   objetos.

Esa última vale la pena. Ven a buscarme cuando la veas.

---

## 6 · Exploración — este es el ejercicio de verdad

El punto de esta sesión no es producir *un* catálogo. Es entender que distintos
parámetros producen **distintos catálogos del mismo cielo**.

Estos los corres a mano. Escribe el comando, cambia un parámetro, córrelo de nuevo, y
compara. Todo en la config se puede sobrescribir por línea de comandos — así que nunca
tienes que editar un archivo para probar un valor.

### 6a · `DETECT_THRESH` y `DETECT_MINAREA`

Corre **al menos tres combinaciones que elijas tú.** Por ejemplo, una laxa:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DETECT_THRESH 1.5 -DETECT_MINAREA 3 \
    -CATALOG_NAME cat/thresh_loose.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME check/seg_loose.fits
```

y una estricta:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DETECT_THRESH 3.0 -DETECT_MINAREA 5 \
    -CATALOG_NAME cat/thresh_strict.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME check/seg_strict.fits
```

Para cada corrida, **lee la última línea que imprime SExtractor** — te dice cuántos
objetos se detectaron y cuántos sobrevivieron. Anota los números.

Luego mira los dos segmentation maps lado a lado:

```bash
ds9 check/seg_loose.fits check/seg_strict.fits \
    -lock frame image -tile
```

**No hay respuesta correcta.** ¿Buscas la contraparte de un transiente? Quieres
completitud. ¿Mides una función de luminosidad? Las fuentes espurias en el extremo débil
te van a destruir.

**La herramienta no decide por ti.**

### 6b · `DEBLEND_MINCONT`

Encuentra la galaxia más grande y extendida de tu cutout (abre la imagen en DS9 y busca).
Corre el mismo campo dos veces, cambiando solo `DEBLEND_MINCONT`:

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

Mira el segmentation map alrededor de esa galaxia las dos veces. Haz zoom.

¿Se fragmenta? **¿Debería?** (Eso depende por completo de qué estés tratando de medir —
que es justamente el punto.)

---

## 7 · PSFEx

`CLASS_STAR` es una red neuronal. Funciona — hasta que el S/N baja, y ahí colapsa hacia
0.5. Deja de saber, y no te avisa.

`SPREAD_MODEL` no colapsa. Pero necesita saber cómo se ve una estrella **en esa posición
exacta, en esa imagen exacta**. Eso es lo que construye PSFEx.

### PSFEx no lee tu imagen. Lee un catálogo de SExtractor.

Lo que significa que el flujo es:

```
SExtractor (pasada 1)  →  prepsfex.cat   (FITS_LDAC, con VIGNET)
        ↓
PSFEx                  →  *.psf
        ↓
SExtractor (pasada 2)  →  catálogo final con SPREAD_MODEL
```

### 7a · Escribe `prepsfex.param`

**Este es un `.param` distinto del científico.** Es corto. Debe contener:

```
VIGNET(35,35)
```

**`VIGNET` es la razón entera de que esta pasada exista.** Le dice a SExtractor que
guarde un recorte de píxeles alrededor de cada fuente — porque PSFEx nunca abre tu
imagen, así que los píxeles tienen que viajar *dentro del catálogo*.

También necesitas: posiciones, `FLUX_RADIUS`, un flujo de apertura y su error,
`ELONGATION`, `SNR_WIN`, y `FLAGS`.

Mira `psfex -dd` y encuentra `PHOTFLUX_KEY`. **Lo que nombres en tu `.param` debe
coincidir con lo que PSFEx espera leer.** Si no coinciden, PSFEx muere con un error poco
útil.

### 7b · Pasada 1

Dos cosas hacen esta corrida distinta de la científica:

- `-CATALOG_TYPE FITS_LDAC` — **obligatorio.** PSFEx no lee otra cosa.
- un `DETECT_THRESH` **más alto** — esta no es la corrida científica. Para ajustar una
  PSF quieres *estrellas buenas*, no completitud. Prueba 5σ.

Además: si tu `.param` dice `FLUX_APER(1)`, entonces `PHOT_APERTURES` debe tener
**exactamente un** valor.

Tu catálogo va a ser grande. Son los recortes de `VIGNET`. Esperado.

### 7c · Corre PSFEx

Edita `config/default.psfex`. Los parámetros que importan:

| | Qué controla | Piensa en |
|---|---|---|
| `PSF_SIZE` | tamaño del modelo en píxeles | **debe ser menor que tu VIGNET** |
| `PSFVAR_DEGREES` | grado del polinomio de variación espacial | 0 = PSF constante (rápido, y falso). 2 = sensato. 4 = sobreajusta si no tienes muchas estrellas |
| `SAMPLE_FWHMRANGE` | qué FWHM cuenta como estrella | **en PÍXELES.** ¿Tu seeing cae dentro? |
| `SAMPLE_MINSNR` | qué tan débil puede ser una estrella | estrellas débiles → PSF ruidosa |
| `SAMPLE_MAXELLIP` | qué tan alargada | este es tu filtro anti-galaxias |
| `SAMPLE_FLAGMASK` | qué FLAGS rechazar | **una estrella saturada tiene el núcleo plano. Si entra, tu PSF es mentira.** |

```bash
psfex prepsfex.cat -c config/default.psfex
```

### 7d · Lee la salida. No te la saltes.

PSFEx imprime una línea como:

```
accepted/total   samp.   chi2/dof   FWHM   ellip.   resi.
```

**Juzga tu propia PSF:**

- **`chi2/dof`** — debe estar cerca de 1. Si es 3, tu modelo no describe tus datos.
- **`FWHM`** — ¿coincide con el header? (Debería.)
- **`ellip.`** — cerca de 0 significa redonda. Un valor grande es un problema de
  seguimiento o flexión.
- **`accepted`** — necesitas ~10 estrellas por término del polinomio. Grado 2 en (x,y)
  tiene 6 términos → **quieres 60+ estrellas**. ¿Las tienes?

Luego mira los check-plots. `CHECKPLOT_DEV` — prueba `PNG` primero; si tu PLPlot no lo
tiene, usa `SVG` o `PSC`.

**El que más importa es `SAMPLES`** — las estrellas que PSFEx usó realmente. Si hay
galaxias ahí, tu PSF está contaminada. Vuelve y aprieta `SAMPLE_MINSNR` y
`SAMPLE_MAXELLIP`.

> Una PSF mala te da un `SPREAD_MODEL` malo y un `MAG_PSF` malo — **silenciosamente**.
> Nada falla. Solo obtienes respuestas incorrectas.

### 7e · Pasada 2

Copia tu `.param` científico, agrega `SPREAD_MODEL`, `SPREADERR_MODEL`, `MAG_PSF`,
`MAGERR_PSF`. Corre SExtractor de nuevo con `-PSF_NAME <tu>.psf`.

**Esto va a ser lento.** Para cada fuente, SExtractor ahora evalúa el polinomio para
construir la PSF en esa posición, y hace un ajuste iterativo. Por eso cuesta lo que
cuesta.

---

## 8 · Tres bandas — y el error que estás a punto de cometer

Ahora haz `u`, `g`, `r`.

### La forma incorrecta (hazla igual — necesitas verla romperse)

Corre SExtractor **tres veces, independientes**, una por banda. Cada banda detecta y mide
por su cuenta. Usa el zero point de esa banda (de la tabla en la sección 0):

```bash
sex data/HYDRA_D_0003_U.fits -c config/default.sex \
    -CATALOG_NAME cat/single_U.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT <ZP_U> \
    -WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE data/HYDRA_D_0003_U.weight.fits
```

Repite para `G` y `R`, cambiando la letra de la banda y el zero point cada vez.
Luego tienes que cross-matchear los tres catálogos por posición y calcular colores — que
es justamente el problema.

### La forma correcta: modo dual

La sintaxis son dos imágenes separadas por **coma, sin espacio**:

```bash
sex detection.fits,measurement.fits -c config/default.sex
```

Las fuentes se **detectan** en la primera imagen, se **miden** en la segunda.

Detecta en `r` — es profunda y tiene el mejor seeing. Luego mide a través de *esas mismas
aperturas*, en *esas mismas posiciones*, en las tres bandas. Así que lo corres tres veces,
y la **primera** imagen siempre es `r`:

```bash
# detecta en R, mide en U
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_U.fits -c config/default.sex \
    -CATALOG_NAME cat/dual_U.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT <ZP_U> \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_U.weight.fits
```

```bash
# detecta en R, mide en G
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_G.fits -c config/default.sex \
    -CATALOG_NAME cat/dual_G.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT <ZP_G> \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_G.weight.fits
```

```bash
# detecta en R, mide en R (sí, R sobre sí misma)
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME cat/dual_R.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT <ZP_R> \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_R.weight.fits
```

En modo dual, `WEIGHT_TYPE` y `WEIGHT_IMAGE` toman **dos** valores separados por coma —
uno para la imagen de detección, uno para la de medición.

Como todas las bandas se detectaron en `r`, **la fila *i* es la misma fuente en los tres
catálogos.** No hay que cross-matchear. Ese es el punto.

### Por qué esto es todo el juego

La apertura de Kron es **adaptativa** — su tamaño depende de la forma medida *en esa
imagen*. El seeing en `u` es peor, así que la fuente se ve más gorda, así que **la elipse
sale más grande**. Más área, más flujo. Tu color ahora tiene un sesgo que no tiene nada
que ver con la estrella.

Y es peor: una fuente débil detectada en `r` puede **no detectarse en `u`**. Dos fuentes
separadas en `r` pueden ser **un solo blob** en `u`. No hay nada que cross-matchear.

**Misma apertura, misma posición, cada banda. Sin eso, no hay color.**

---

## 9 · El entregable

Haz el diagrama color-color — `(u−g)` vs `(g−r)` — **dos veces**: una desde tus catálogos
de modo dual, otra desde los catálogos banda por banda. Este script lee los dos conjuntos
y los grafica lado a lado:

```bash
python3 scripts/02_color_color.py
```

Colorea los puntos por `SPREAD_MODEL`.

**Mira los dos diagramas.** La secuencia estelar es más ancha en uno de ellos. Ese
scatter extra no es ruido fotométrico. **Son tus aperturas en desacuerdo entre sí.**

Nada falló. Los dos catálogos se ven perfectamente respetables en TOPCAT.

Uno de ellos solo tiene colores que no significan nada.

---

## 10 · Opcional — si terminaste temprano

Hiciste tu diagrama color-color con `MAG_APER`, no con `MAG_PSF`. Fue a propósito:
`MAG_PSF` solo es válido para **fuentes puntuales**, y tu diagrama tiene galaxias.
Ajustar una PSF a una galaxia da un número sin sentido.

Entonces, ¿*cuándo* vale la pena `MAG_PSF`? Este experimento lo responde, con
estrellas.

```bash
python3 scripts/03_psf_vs_aper.py
```

Para una estrella **aislada**, `MAG_APER` y `MAG_PSF` coinciden — una estrella *es* la
PSF, así que integrar una apertura fija y ajustar la PSF dan el mismo flujo.

Para una estrella con un **vecino** cercano, divergen. La apertura fija recoge también
la luz del vecino, así que `MAG_APER` sale demasiado brillante. El ajuste de PSF sabe
qué forma tiene una estrella y no se deja engañar.

**Esa es la razón entera de que exista la fotometría PSF: campos poblados.** No para las
estrellas aisladas — para las apiñadas.

---

## Qué entregar

1. **Tu `default.sex`**, con una justificación breve para cada parámetro que cambiaste
   del default. *"¿Por qué elegiste ese `BACK_SIZE`?"* es una pregunta justa.

2. **Tu catálogo final** (`.fits`), con las tres bandas medidas a través de aperturas
   idénticas.

3. **Dos figuras:**
   - el diagrama color-color, coloreado por `SPREAD_MODEL`
   - un diagnóstico de tu elección que te haya convencido de que algo funcionaba (o no)

4. **Dos frases sobre qué salió mal y cómo lo diagnosticaste.**

**El punto 4 es el que realmente califico.** Todo lo demás lo puede producir alguien
copiando comandos. El punto 4 no.

---

## Si te atascas

`solutions/` tiene una versión resuelta de cada paso. **Úsala si llevas más de diez
minutos atascado** — estar atascado no es el ejercicio.

Pero piensa primero. Los comandos son la parte fácil.

---

## Referencia

- Manual de SExtractor — https://sextractor.readthedocs.io
- Manual de PSFEx — https://psfex.readthedocs.io
- Bertin & Arnouts 1996, A&AS 117, 393
