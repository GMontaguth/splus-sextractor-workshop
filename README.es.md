<!-- LANGUAGE -->
[English](README.md) · **Español** · [Português](README.pt.md)

---

# Construyendo catálogos astronómicos con Source Extractor

**Actividad práctica 2 — Escuela S-PLUS**
Gissel Montaguth

---

## Lo que vas a hacer hoy

Vas a construir un catálogo fotométrico de un campo real de S-PLUS, en dos bandas, y lo
vas a usar para separar estrellas de galaxias.

Pero ese no es realmente el punto. El punto es este:

> **Un catálogo no es la verdad. Es una medición, y contiene decisiones.**

Cada parámetro que fijes hoy es una decisión. Al final de la sesión quiero que puedas
decir, para cada uno: *¿qué elegí, y por qué?*

**No te voy a dar los archivos de configuración.** Los vas a construir tú. Eso es la
mayor parte de esta sesión.

---

## Instalación

Si SExtractor y PSFEx ya están disponibles en tu máquina (o vía `module load` en un
cluster), sáltate esta sección. Si no, instálalos una vez antes de la sesión.

### Paso 1 — Librerías del sistema

```bash
sudo apt-get update
sudo apt-get install libcfitsio-dev                                # CFITSIO (lee FITS)
sudo apt-get install libatlas-base-dev libblas-dev liblapack-dev   # ATLAS
sudo apt-get install libfftw3-dev                                  # FFTW
sudo apt-get install libplplot-dev                                 # PLPlot (plots de PSFEx)
```

### Paso 2 — SExtractor

```bash
git clone https://github.com/astromatic/sextractor.git
cd sextractor
sh autogen.sh
./configure
make -j
sudo make install
```

Verifica:

```bash
sex --version
```

> **Si `./configure` se detiene con un error como** `CFITSIO include files not found` **(o
> lo mismo para FFTW, ATLAS, PLPlot):** falta la librería correspondiente del Paso 1.
> Instálala — para CFITSIO es `sudo apt-get install libcfitsio-dev` — y luego solo
> vuelve a correr los últimos tres comandos:
> ```bash
> ./configure
> make -j
> sudo make install
> ```
> No necesitas clonar de nuevo. Repite hasta que `./configure` termine sin errores.

**Alternativa (conda):**

```bash
conda install -c conda-forge astromatic-source-extractor
```

Ver https://anaconda.org/conda-forge/astromatic-source-extractor

### Paso 3 — PSFEx

```bash
git clone https://github.com/astromatic/psfex.git
cd psfex
sh autogen.sh
./configure
make -j
sudo make install
```

Verifica:

```bash
psfex --version
```

> Aplica la misma regla: si `./configure` se queja de una librería faltante, instálala y
> vuelve a correr `./configure`, `make -j`, `sudo make install`.

---

## 0 · Consigue los datos

Clona el repositorio (código + configs), y luego descarga las imágenes del
**Release** (son demasiado grandes para git).

```bash
git clone https://github.com/GMontaguth/splus-sextractor-workshop.git
cd splus-sextractor-workshop
mkdir -p data
```

Descarga los cuatro archivos FITS, con el script o a mano:

```bash
# o bien — corre el ayudante
bash scripts/00_get_data.sh

# o bien — descárgalos uno por uno
BASE=https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data
cd data
wget $BASE/HYDRA_D_0003_G.fits
wget $BASE/HYDRA_D_0003_G.weight.fits
wget $BASE/HYDRA_D_0003_R.fits
wget $BASE/HYDRA_D_0003_R.weight.fits
cd ..
```

También puedes hacer clic desde el navegador:
[G](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_G.fits) ·
[G weight](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_G.weight.fits) ·
[R](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_R.fits) ·
[R weight](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_R.weight.fits)

Son cutouts de 2000 × 2000 de S-PLUS iDR6, **ya descomprimidos** (los frames de S-PLUS
vienen comprimidos con tile-compression, que SExtractor 2.25 no lee — eso ya está
resuelto para ti).

### Los zero points

Los vas a necesitar para medir magnitudes. **No son un solo número** — en iDR6 el ZP es
un modelo espacial que varía a través del campo. Abajo está la mediana y la dispersión de
esa variación:

| banda | ZP mediano | std (dispersión espacial) |
|---|---|---|
| `g` | 22.920 | 0.012 |
| `r` | 22.784 | 0.013 |

Usa la mediana como tu `MAG_ZEROPOINT`. Pero **mira esa columna `std` y piensa.** Te dice
cuánto se mueve el ZP a través del campo. ¿La mediana es una aproximación segura? Ten
claro por qué.

> SExtractor **no** calcula zero points. Solo los aplica:
> `MAG = -2.5 log10(FLUX) + MAG_ZEROPOINT`. Ese número vino de un pipeline de calibración
> que corrió mucho antes que tú.

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

# si compilaste, usaste conda, o cargaste un módulo, prueba:
find / -name "default.nnw" 2>/dev/null
find / -name "*.conv" 2>/dev/null | head
```

Copia lo que necesites a `config/`:

```bash
cp <ruta>/default.nnw          config/
cp <ruta>/gauss_2.0_5x5.conv   config/
cp <ruta>/gauss_2.5_5x5.conv   config/     # puede que lo quieras después
```

**Para qué sirve cada archivo:**

| Archivo | Qué es | ¿Lo editas? |
|---|---|---|
| `default.sex` | parámetros de ejecución | **siempre** |
| `default.param` | **qué columnas quieres en la salida** | **siempre** |
| `*.conv` | el kernel de filtrado | lo *eliges*, no lo editas |
| `default.nnw` | la red neuronal entrenada de `CLASS_STAR` | nunca |

### Algo que debes agregar a mano: la imagen de peso

Los parámetros de la imagen de peso a veces **no** vienen en el `default.sex`. Abre el
archivo y agrega este bloque, para que SExtractor use la imagen de peso:

```
#------------------------------- Weighting -----------------------------------
WEIGHT_TYPE      MAP_WEIGHT
WEIGHT_IMAGE     data/HYDRA_D_0003_R.weight.fits
```

Sin él, SExtractor asume ruido uniforme, y tus detecciones en los bordes ruidosos del
campo no son lo que dicen ser.

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
tu imagen. Ve a buscarlos en el **header**.

Ya sabes usar DS9, así que úsalo: abre la imagen y ve a
**File → Display Header** (o el botón `Header` de la barra). Recorre los keywords y
encuentra los cuatro que importan. Puedes buscar el nombre del keyword en el texto del
header.

```bash
ds9 data/HYDRA_D_0003_R.fits &
# luego: File → Display Header
```

¿Prefieres la terminal? Cualquiera de estos imprime el header sin abrir un visor:

```bash
# con astropy
python3 -c "from astropy.io import fits; fits.open('data/HYDRA_D_0003_R.fits').info(); print(repr(fits.getheader('data/HYDRA_D_0003_R.fits')))"

# o, si tienes las utilidades FTOOLS / cfitsio
fold data/HYDRA_D_0003_R.fits | head
listhead data/HYDRA_D_0003_R.fits
```

> **Un detalle:** en estos archivos los datos (y los keywords útiles) pueden estar en la
> **extensión 1**, no en la 0. Si el header de la primera extensión se ve vacío, mira la
> siguiente — en DS9 usa el selector de extensión/HDU; en astropy es
> `fits.getheader('...', 1)`.

Anota los cuatro que importan:

| Keyword del header | Va en | Por qué |
|---|---|---|
| `FWHMMEAN` | `SEEING_FWHM` **y** tu elección de `FILTER_NAME` | en arcsec |
| `SATURATE` | `SATUR_LEVEL` | **el default es 50000. El tuyo no.** |
| `GAIN` | `GAIN` | electrones por cuenta |
| escala de píxel | `PIXEL_SCALE` | S-PLUS: 0.55 ″/px |

> ⚠️ **`SATUR_LEVEL` es el que la gente se equivoca.** Si lo dejas en el default, las
> estrellas saturadas nunca se flaguean como saturadas, y `FLAGS = 4` nunca aparece en
> tu catálogo. No te vas a dar cuenta hasta que sea tarde.

**Haz esto para cada banda — los valores no son los mismos.** El seeing en particular
cambia de `g` a `r`, así que vas a cambiar `SEEING_FWHM` (y quizá tu kernel) entre
ellas.

**Convierte el seeing a píxeles tú mismo.** Lo necesitas para elegir el kernel:

```
FWHM [px] = FWHMMEAN ["] / 0.55 ["/px]
```

Ahora mira los nombres de los kernels — `gauss_2.0_5x5.conv`, `gauss_2.5_5x5.conv`.
**El número es el FWHM en píxeles.** Elige el que mejor se adapte a tus dos bandas.

¿Por qué? La convolución antes de la detección es un **filtro adaptado (matched
filter)**: si el kernel tiene la forma de la fuente que buscas, maximizas el S/N de
detección. Y para una fuente puntual, la fuente que buscas *es la PSF*.

### Ahora pon tus valores en `default.sex`

Vamos a usar **r como nuestra banda de referencia** — es profunda y tiene la mejor
señal-ruido, así que es la que usamos para detectar.

Abre la config y pon los valores que acabas de encontrar. Puedes abrir
`config/default.sex` en tu editor, o desde la terminal:

```bash
gedit config/default.sex &
```

Fija `SEEING_FWHM`, `SATUR_LEVEL`, `GAIN`, `PIXEL_SCALE` y tu `FILTER_NAME` elegido.

**Y recuerda darle el camino** a tus archivos de configuración — `PARAMETERS_NAME`,
`FILTER_NAME`, `STARNNW_NAME`. Por ejemplo:

```
STARNNW_NAME     config/default.nnw
```

---

## 3 · El zero point

Ya viste los zero points en la sección 0. **El zero point de S-PLUS iDR6 no es un número
— es un modelo espacial que varía a través del campo.** La tabla te dio la mediana y la
dispersión (`std`) de esa variación.

Mira la columna `std` de nuevo y piensa:

- ¿Un solo ZP mediano es suficiente para lo que estás haciendo?
- ¿La dispersión es la misma en todas las bandas?

Como este es un ejercicio práctico para entender cómo funciona la herramienta, **por hoy
usaremos el zero point mediano para cada imagen.** Pero ten en cuenta que es una
aproximación — el ZP real varía a través del campo, y una medición de calidad científica
tendría que tomar eso en cuenta.

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

**El formato es simplísimo: un nombre de columna por línea.** Un `#` al inicio de la
línea la comenta. Sin comas, sin comillas, sin encabezado. Nada más.

Así, un `config/default.param` mínimo se ve así:

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

Eso ya corre. **Ahora constrúyelo desde ahí.** Necesitas, como mínimo:

- un identificador y una posición (píxel *y* cielo) — el bloque de arriba ya los tiene
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

Agrega las que elegiste a tu archivo, cada una en su propia línea (`MAG_APER`,
`MAGERR_APER`, etc.).

Para una salida vectorial como tres aperturas, la sintaxis es `MAG_APER(3)` — y **el
número entre paréntesis debe coincidir con cuántos valores pongas en
`PHOT_APERTURES`.**

`PHOT_APERTURES` es un **diámetro en píxeles**. Si quieres una apertura de 3″:
`3 / 0.55 = 5.45 px`.

Por ahora esas columnas básicas alcanzan para crear un primer catálogo — solo para
entender la herramienta y elegir tu mejor configuración. Ten en cuenta la lista más
completa para el futuro, cuando armes el catálogo *oficial*.

> ¿Atascado en qué columnas existen? Corre `sex -dp` — la lista completa de parámetros
> está ahí, comentada, con una descripción de una línea de cada una. Y
> `solutions/default.param` tiene una versión resuelta completa si la necesitas.

---

## 5 · Tu primera corrida

Ahora edita `config/default.sex` con todo lo que averiguaste arriba.

Además, como queremos ver que también funciona, queremos ver cómo es la imagen del cielo
y cuáles son las fuentes que estamos identificando. Vamos a pedir dos **imágenes de
chequeo**: la imagen de segmentación y el background. Busca `CHECKIMAGE_TYPE` y pon las
dos opciones ahí, y en `CHECKIMAGE_NAME` van los nombres de las dos imágenes FITS que
quieres.

Ahora sí podemos correr SExtractor. Este catálogo — que llamaremos `r_first.cat` — es
solo para explorar los parámetros. Escribe esto en la terminal:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME r_first.cat \
    -CATALOG_TYPE FITS_1.0
```

**Nota:** cualquier cosa en el archivo de config se puede sobrescribir por línea de
comandos con `-PARAM valor`. No es una comodidad — es lo que hace manejable correr muchas
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
ds9 data/HYDRA_D_0003_R.fits seg.fits bkg.fits \
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

Corre **al menos tres combinaciones que elijas tú.** Para esto puedes cambiar los valores
directamente en `default.sex`, o indicar en la terminal los parámetros del archivo de
configuración que quieres cambiar. Por ejemplo, una laxa:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DETECT_THRESH 1.5 -DETECT_MINAREA 3 \
    -CATALOG_NAME thresh_loose.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME seg_loose.fits
```

y una estricta:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DETECT_THRESH 3.0 -DETECT_MINAREA 5 \
    -CATALOG_NAME thresh_strict.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME seg_strict.fits
```

Para cada corrida, **lee la última línea que imprime SExtractor** — te dice cuántos
objetos se detectaron y cuántos sobrevivieron. Anota los números.

Luego mira los dos segmentation maps lado a lado:

```bash
ds9 seg_loose.fits seg_strict.fits \
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
    -CATALOG_NAME deb_aggressive.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME seg_aggressive.fits
```

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DEBLEND_MINCONT 0.1 \
    -CATALOG_NAME deb_conservative.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME seg_conservative.fits
```

Mira el segmentation map alrededor de esa galaxia las dos veces. Haz zoom.

¿Se fragmenta? **¿Debería?** (Eso depende por completo de qué estés tratando de medir —
que es justamente el punto.)

---

Una vez que encuentres los parámetros con los que estás conforme para estos, ponlos
**directamente en `default.sex`**, para no tener que estar pasándolos por línea de
comandos en el resto del tutorial.

## 7 · PSFEx

Como mencionamos en el curso, la determinación de una buena PSF es fundamental para tener
una buena separación entre una fuente extendida y una puntual — además de permitir tener
una buena apertura PSF para medir la magnitud de las estrellas. Para la separación entre
estrella y galaxia tenemos estas dos opciones:

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

> **Importante:** la apertura que elijas debe ser una **apertura FIJA, no Kron** —
> quieres algo que no dependa de la morfología medida. Por ejemplo, una apertura de 3″.

Mira `psfex -dd` y encuentra `PHOTFLUX_KEY`. **Lo que nombres en tu `.param` debe
coincidir con lo que PSFEx espera leer.** Si no coinciden, PSFEx muere con un error poco
útil (normalmente un segmentation fault).

Luego corre SExtractor para producir el catálogo con el que va a funcionar PSFEx —
llámalo, por ejemplo, `prepsfex.cat`.

### 7b · Pasada 1

Dos cosas hacen esta corrida distinta de la científica:

- `-CATALOG_TYPE FITS_LDAC` — **obligatorio.** PSFEx no lee otra cosa. (Si lo olvidas,
  PSFEx crashea con un segmentation fault y sin mensaje útil.)
- un `DETECT_THRESH` **más alto** — esta no es la corrida científica. Para ajustar una
  PSF quieres *estrellas buenas*, no completitud. Prueba 5σ.

Además: si tu `.param` dice `FLUX_APER(1)`, entonces `PHOT_APERTURES` debe tener
**exactamente un** valor.

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME prepsfex.cat -CATALOG_TYPE FITS_LDAC \
    -PARAMETERS_NAME config/prepsfex.param \
    -DETECT_THRESH 5.0 -ANALYSIS_THRESH 5.0 -PHOT_APERTURES 10
```

Tu catálogo va a ser grande. Son los recortes de `VIGNET`. Esperado.

**Verifica que de verdad quedó como LDAC** antes de dárselo a PSFEx:

```bash
python3 -c "from astropy.io import fits; print([h.name for h in fits.open('prepsfex.cat')])"
```

Debes ver `LDAC_IMHEAD` y `LDAC_OBJECTS`. Si ves un `OBJECTS` a secas, el
`-CATALOG_TYPE FITS_LDAC` no se aplicó — esa es la causa #1 del segfault.

### 7c · Corre PSFEx

Edita `config/default.psfex`. Los parámetros que importan:

| | Qué controla | Piensa en |
|---|---|---|
| `PSF_SIZE` | tamaño del modelo en píxeles | **debe ser menor que tu VIGNET** |
| `PSFVAR_DEGREES` | grado del polinomio de variación espacial | 0 = PSF constante (rápido, y falso). 2 = sensato. 4 = sobreajusta si no tienes muchas estrellas |
| `SAMPLE_FWHMRANGE` | qué FWHM cuenta como estrella | **en PÍXELES.** ¿Tu seeing cae dentro? |
| `SAMPLE_MINSNR` | qué tan débil puede ser una estrella | estrellas débiles → PSF ruidosa |
| `SAMPLE_MAXELLIP` | qué tan alargada | este es tu filtro anti-galaxias |

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

## 8 · Dos bandas — y el error que estás a punto de cometer

Vamos a hacer un experimento rápido. Normalmente, cuando queremos un catálogo que
caracterice estrellas y galaxias, la forma más limpia es usar la PSF — pero como ya
vieron, es lenta. Así que vamos a hacer una corrida rápida con **dos filtros**, para
entender cómo se trabaja cuando tienes más de una banda, porque casi nunca trabajamos con
un solo filtro.

Hay dos maneras de generar los catálogos: la manera **incorrecta** y la **correcta**.

### La forma incorrecta (hazla igual — necesitas verla romperse)

Corre SExtractor **dos veces, independientes**, una por banda. Cada banda detecta y mide
por su cuenta. Para este experimento basta con la apertura `AUTO` — puedes eliminar las
otras aperturas. Usa el zero point de esa banda (de la tabla en la sección 0):

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME single_R.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.784 \
    -WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits
```

Recuerda que en `default.sex` escribimos `GAIN`, `SATUR_LEVEL` y `SEEING_FWHM` para el
filtro **r** — entonces para **g** hay que cambiarlos:

```bash
sex data/HYDRA_D_0003_G.fits -c config/default.sex \
    -CATALOG_NAME single_G.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.920 \
    -GAIN <G_gain> \
    -SATUR_LEVEL <G_satur> \
    -SEEING_FWHM <G_seeing> \
    -WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE data/HYDRA_D_0003_G.weight.fits
```

Abre los dos catálogos en TOPCAT. ¿Qué ves? ¿Son iguales?

### La forma correcta: modo dual

La sintaxis son dos imágenes separadas por **coma, sin espacio**:

```bash
sex detection.fits,measurement.fits -c config/default.sex
```

Las fuentes se **detectan** en la primera imagen, se **miden** en la segunda.

Detecta en `r` — es profunda y tiene el mejor seeing. Luego mide a través de *esas mismas
aperturas*, en *esas mismas posiciones*, en las dos bandas. Así que lo corres dos veces,
y la **primera** imagen siempre es `r`:

```bash
# detecta en R, mide en G
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_G.fits -c config/default.sex \
    -CATALOG_NAME dual_G.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.920 \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_G.weight.fits
```

```bash
# detecta en R, mide en R (sí, R sobre sí misma)
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME dual_R.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.784 \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_R.weight.fits
```

En modo dual, `WEIGHT_TYPE` y `WEIGHT_IMAGE` toman **dos** valores separados por coma —
uno para la imagen de detección, uno para la de medición.

Como las dos bandas se detectaron en `r`, **la fila *i* es la misma fuente en los dos
catálogos.** No hay que cross-matchear. Ese es el punto.

### Por qué esto es todo el juego

La apertura de Kron es **adaptativa** — su tamaño depende de la forma medida *en esa
imagen*. El seeing en `g` es distinto, así que la fuente puede verse más gorda, así que
**la elipse sale de un tamaño distinto**. Más área, más flujo. Tu color ahora tiene un
sesgo que no tiene nada que ver con la estrella.

Y es peor: una fuente débil detectada en `r` puede **no detectarse en `g`**. Dos fuentes
separadas en `r` pueden ser **un solo blob** en `g`. No hay nada que cross-matchear.

**Misma apertura, misma posición, cada banda. Sin eso, no hay color.**

Abre los catálogos en TOPCAT de nuevo. ¿Qué ves ahora? ¿Son iguales?

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
