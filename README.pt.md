<!-- LANGUAGE -->
[English](README.md) · [Español](README.es.md) · **Português**

---

# Construindo catálogos astronômicos com o Source Extractor

**Atividade prática 2 — Escola S-PLUS**
Gissel Montaguth

---

## O que você vai fazer hoje

Você vai construir um catálogo fotométrico de um campo real do S-PLUS, em duas bandas, e
vai usá-lo para separar estrelas de galáxias.

Mas esse não é bem o ponto. O ponto é este:

> **Um catálogo não é a verdade. É uma medição, e contém decisões.**

Cada parâmetro que você definir hoje é uma decisão. Ao final da sessão eu quero que você
consiga dizer, para cada um: *o que escolhi, e por quê?*

**Eu não vou te dar os arquivos de configuração.** Você vai construí-los. É essa a maior
parte da sessão.

---

## Instalação

Se o SExtractor e o PSFEx já estão disponíveis na sua máquina (ou via `module load` num
cluster), pule esta seção. Caso contrário, instale-os uma vez antes da sessão.

### Passo 1 — Bibliotecas do sistema

```bash
sudo apt-get update
sudo apt-get install libcfitsio-dev                                # CFITSIO (lê FITS)
sudo apt-get install libatlas-base-dev libblas-dev liblapack-dev   # ATLAS
sudo apt-get install libfftw3-dev                                  # FFTW
sudo apt-get install libplplot-dev                                 # PLPlot (plots do PSFEx)
```

### Passo 2 — SExtractor

```bash
git clone https://github.com/astromatic/sextractor.git
cd sextractor
sh autogen.sh
./configure
make -j
sudo make install
```

Verifique:

```bash
sex --version
```

> **Se o `./configure` parar com um erro como** `CFITSIO include files not found` **(ou o
> mesmo para FFTW, ATLAS, PLPlot):** falta a biblioteca correspondente do Passo 1.
> Instale-a — para o CFITSIO é `sudo apt-get install libcfitsio-dev` — e depois é só
> rodar de novo os três últimos comandos:
> ```bash
> ./configure
> make -j
> sudo make install
> ```
> Você não precisa clonar de novo. Repita até o `./configure` terminar sem erros.

**Alternativa (conda):**

```bash
conda install -c conda-forge astromatic-source-extractor
```

Veja https://anaconda.org/conda-forge/astromatic-source-extractor

### Passo 3 — PSFEx

```bash
git clone https://github.com/astromatic/psfex.git
cd psfex
sh autogen.sh
./configure
make -j
sudo make install
```

Verifique:

```bash
psfex --version
```

> A mesma regra vale: se o `./configure` reclamar de uma biblioteca faltando, instale-a e
> rode de novo `./configure`, `make -j`, `sudo make install`.

---

## 0 · Pegue os dados

Clone o repositório (código + configs), e depois baixe as imagens do
**Release** (são grandes demais para o git).

```bash
git clone https://github.com/GMontaguth/splus-sextractor-workshop.git
cd splus-sextractor-workshop
mkdir -p data
```

Baixe os quatro arquivos FITS, com o script ou à mão:

```bash
# ou — rode o auxiliar
bash scripts/00_get_data.sh

# ou — baixe um por um
BASE=https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data
cd data
wget $BASE/HYDRA_D_0003_G.fits
wget $BASE/HYDRA_D_0003_G.weight.fits
wget $BASE/HYDRA_D_0003_R.fits
wget $BASE/HYDRA_D_0003_R.weight.fits
cd ..
```

Você também pode clicar pelo navegador:
[G](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_G.fits) ·
[G weight](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_G.weight.fits) ·
[R](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_R.fits) ·
[R weight](https://github.com/GMontaguth/splus-sextractor-workshop/releases/download/v1.0-data/HYDRA_D_0003_R.weight.fits)

São cutouts de 2000 × 2000 do S-PLUS iDR6, **já descomprimidos** (os frames do S-PLUS vêm
comprimidos com tile-compression, que o SExtractor 2.25 não lê — isso já foi resolvido
para você).

### Os zero points

Você vai precisar deles para medir magnitudes. **Não são um único número** — no iDR6 o ZP
é um modelo espacial que varia ao longo do campo. Abaixo estão a mediana e o espalhamento
dessa variação:

| banda | ZP mediano | std (espalhamento espacial) |
|---|---|---|
| `g` | 22.920 | 0.012 |
| `r` | 22.784 | 0.013 |

Use a mediana como seu `MAG_ZEROPOINT`. Mas **olhe essa coluna `std` e pense.** Ela te
diz o quanto o ZP varia ao longo do campo. A mediana é uma aproximação segura? Saiba dizer
por quê.

> O SExtractor **não** calcula zero points. Ele só os aplica:
> `MAG = -2.5 log10(FLUX) + MAG_ZEROPOINT`. Esse número veio de um pipeline de calibração
> que rodou muito antes de você.

**Confira que está tudo lá antes de continuar:**

```bash
bash scripts/00_check_setup.sh
```

---

## 1 · Encontre os valores padrão

Antes de mudar um parâmetro, você precisa saber que ele existe.

### Onde o SExtractor guarda seus valores padrão

O SExtractor pode imprimir seus próprios valores padrão. Duas flags:

```bash
sex -d           # a lista curta — os parâmetros que você normalmente mexe
sex -dd          # a lista COMPLETA — tudo, com comentários
```

Teste as duas. Repare o quanto `-dd` é maior.

**Guarde uma cópia:**

```bash
mkdir -p config
sex -d  > config/default.sex
sex -dd > config/default.sex.full     # guarde como referência
```

Abra `config/default.sex.full` e leia. Não passe o olho — *leia*. Você vai passar o resto
do dia dentro desse arquivo.

### Os outros três arquivos

O SExtractor precisa de mais três arquivos, e eles vêm com a instalação.
**Encontre-os.**

```bash
# se você instalou via apt:
dpkg -L source-extractor | grep -E "\.param|\.conv|\.nnw"

# se compilou, usou conda, ou carregou um módulo, tente:
find / -name "default.nnw" 2>/dev/null
find / -name "*.conv" 2>/dev/null | head
```

Copie o que precisar para `config/`:

```bash
cp <caminho>/default.nnw          config/
cp <caminho>/gauss_2.0_5x5.conv   config/
cp <caminho>/gauss_2.5_5x5.conv   config/     # talvez você queira depois
```

**Para que serve cada arquivo:**

| Arquivo | O que é | Você edita? |
|---|---|---|
| `default.sex` | parâmetros de execução | **sempre** |
| `default.param` | **quais colunas você quer na saída** | **sempre** |
| `*.conv` | o kernel de filtragem | você *escolhe* um, não edita |
| `default.nnw` | a rede neural treinada do `CLASS_STAR` | nunca |

### Uma coisa que você precisa adicionar à mão: o weight map

Os parâmetros do weight map às vezes **não** vêm no `default.sex`. Abra o arquivo e
adicione este bloco, para que o SExtractor use a imagem de peso:

```
#------------------------------- Weighting -----------------------------------
WEIGHT_TYPE      MAP_WEIGHT
WEIGHT_IMAGE     data/HYDRA_D_0003_R.weight.fits
```

Sem ele, o SExtractor assume ruído uniforme, e suas detecções nas bordas ruidosas do
campo não são o que dizem ser.

### Onde o PSFEx guarda seus valores padrão

Mesma ideia:

```bash
psfex -d  > config/default.psfex
psfex -dd > config/default.psfex.full
```

Leia também. É mais curto, e metade são opções de check-plots.

---

## 2 · Leia o header antes de escrever a config

Metade dos parâmetros de `default.sex` não são escolhas livres — são fatos sobre a sua
imagem. Vá buscá-los.

```bash
python3 scripts/01_read_header.py
```

Isso imprime os keywords de que você precisa. Anote os quatro que importam:

| Keyword do header | Vai em | Por quê |
|---|---|---|
| `FWHMMEAN` | `SEEING_FWHM` **e** sua escolha de `FILTER_NAME` | em arcsec |
| `SATURATE` | `SATUR_LEVEL` | **o padrão é 50000. O seu não é.** |
| `GAIN` | `GAIN` | |
| escala de pixel | `PIXEL_SCALE` | S-PLUS: 0,55 ″/px |

> ⚠️ **`SATUR_LEVEL` é o que as pessoas erram.** Se você deixar no padrão, estrelas
> saturadas nunca são marcadas como saturadas, e `FLAGS = 4` nunca aparece no seu
> catálogo. Você não vai perceber até ser tarde.

**Converta o seeing para pixels você mesmo.** Você precisa disso para escolher o kernel:

```
FWHM [px] = FWHMMEAN ["] / 0,55 ["/px]
```

Agora olhe os nomes dos kernels — `gauss_2.0_5x5.conv`, `gauss_2.5_5x5.conv`. **O número
é o FWHM em pixels.** Escolha o que melhor se ajusta às suas duas bandas.

Por quê? A convolução antes da detecção é um **filtro casado (matched filter)**: se o
kernel tem a forma da fonte que você procura, você maximiza o S/N de detecção. E para uma
fonte pontual, a fonte que você procura *é a PSF*.

### Agora coloque seus valores no `default.sex`

Vamos usar **r como nossa banda de referência** — é profunda e tem o melhor
sinal-ruído, então é a que usamos para detectar.

Abra a config e defina os valores que você acabou de encontrar. Você pode abrir
`config/default.sex` no seu editor, ou pelo terminal:

```bash
gedit config/default.sex &
```

Defina `SEEING_FWHM`, `SATUR_LEVEL`, `GAIN`, `PIXEL_SCALE` e o seu `FILTER_NAME`
escolhido.

**E lembre de dar o caminho** para seus arquivos de configuração — `PARAMETERS_NAME`,
`FILTER_NAME`, `STARNNW_NAME`. Por exemplo:

```
STARNNW_NAME     config/default.nnw
```

---

## 3 · O zero point

Você já viu os zero points na seção 0. **O zero point do S-PLUS iDR6 não é um número — é
um modelo espacial que varia ao longo do campo.** A tabela te deu a mediana e o
espalhamento (`std`) dessa variação.

Olhe a coluna `std` de novo e pense:

- Um único ZP mediano é suficiente para o que você está fazendo?
- O espalhamento é o mesmo em todas as bandas?

Como este é um exercício prático para entender como a ferramenta funciona, **por hoje
usaremos o zero point mediano para cada imagem.** Mas tenha em mente que isso é uma
aproximação — o ZP real varia ao longo do campo, e uma medição de qualidade científica
precisaria levar isso em conta.

> O SExtractor **não** calcula zero points. Ele só os aplica:
> `MAG = -2.5 log10(FLUX) + MAG_ZEROPOINT`.
> Esse número veio de um pipeline de calibração que rodou muito antes de você. Saiba de
> onde ele veio.

---

## 4 · Escreva seu `default.param`

Este é o arquivo que todo mundo esquece, e é o que decide o que você realmente recebe.

> **Se uma coluna não está no `default.param`, ela não aparece no seu catálogo — mesmo
> que o SExtractor a tenha calculado.** Não é um bug. Você não pediu.

Olhe o `default.param` que vem: está tudo comentado com `#`. É um cardápio, não uma
config.

**O formato é simplésimo: um nome de coluna por linha.** Um `#` no início da linha a
comenta. Sem vírgulas, sem aspas, sem cabeçalho. Só isso.

Então um `config/default.param` mínimo é assim:

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

Isso já roda. **Agora construa o seu a partir daí.** Você precisa, no mínimo:

- um identificador e uma posição (pixel *e* céu) — o bloco acima já os tem
- uma magnitude **e** seu erro
- a forma (você vai precisar de `FLUX_RADIUS` — confie)
- `FLAGS` ← **nunca deixe de fora**
- `CLASS_STAR`

**Decida qual fluxo você quer**, e saiba dizer por quê:

| | O que é | Quando |
|---|---|---|
| `MAG_ISO` | pixels acima do limiar | **nunca para cores** — o limiar difere em cada banda |
| `MAG_APER` | abertura circular fixa | **a base da fotometria multibanda** |
| `MAG_AUTO` | elipse de Kron | proxy de fluxo total (~94% de um perfil típico) |
| `MAG_PETRO` | abertura de Petrosian | comparação com o SDSS |

Adicione as que você escolheu ao seu arquivo, cada uma na sua própria linha (`MAG_APER`,
`MAGERR_APER`, e assim por diante).

Para uma saída vetorial como três aberturas, a sintaxe é `MAG_APER(3)` — e **o número
entre parênteses tem que bater com quantos valores você pôs em `PHOT_APERTURES`.**

`PHOT_APERTURES` é um **diâmetro em pixels**. Se você quer uma abertura de 3″:
`3 / 0,55 = 5,45 px`.

Por enquanto essas colunas básicas bastam para criar um primeiro catálogo — só para
entender a ferramenta e escolher sua melhor configuração. Tenha a lista mais completa em
mente para o futuro, quando você construir o catálogo *oficial*.

> Travado em quais colunas existem? Rode `sex -dd` — a lista completa de parâmetros está
> lá, comentada, com uma descrição de uma linha de cada uma. E `solutions/default.param`
> tem uma versão resolvida completa se você precisar.

---

## 5 · Sua primeira execução

Agora edite `config/default.sex` com tudo que você descobriu acima.

Além disso, como queremos ver que funciona, queremos ver como é a imagem do céu e quais
são as fontes que estamos identificando. Vamos pedir duas **imagens de checagem**: a
imagem de segmentação e o background. Procure `CHECKIMAGE_TYPE` e coloque as duas opções
ali, e em `CHECKIMAGE_NAME` vão os nomes das duas imagens FITS que você quer.

Agora podemos rodar o SExtractor. Este catálogo — que chamaremos de `r_first.cat` — é só
para explorar os parâmetros. Digite isto no terminal:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME r_first.cat \
    -CATALOG_TYPE FITS_1.0
```

**Nota:** qualquer coisa no arquivo de config pode ser sobrescrita na linha de comando
com `-PARAM valor`. Não é uma comodidade — é o que torna viável rodar muitas bandas com
uma única config.

### Funcionou?

Olhe o que o SExtractor imprimiu:

```
(M+D) Background: ...   RMS: ...   / Threshold: ...
      Objects: detected N / sextracted M
```

**Confira a aritmética você mesmo:** `Threshold` é igual a `DETECT_THRESH × RMS`?
Deveria ser. Esse é o momento em que "1,5 sigma" vira um número concreto de contagens.

### Agora OLHE. Isto não é opcional.

```bash
ds9 data/HYDRA_D_0003_R.fits seg.fits bkg.fits \
    -zscale -lock frame image -lock scale yes -tile
```

**Três coisas para procurar:**

1. **As bordas do segmentation map.** Estão limpas? Se estiverem, seu weight map está
   fazendo o trabalho dele. Comente `WEIGHT_IMAGE`, rode de novo, e veja a diferença.
2. **O modelo de fundo.** É plano? (Não é.) Você consegue ver os halos das estrelas
   brilhantes *dentro* do seu modelo de céu?
3. **Dê zoom numa estrela brilhante e saturada no segmentation map.** Conte os objetos.

Essa última vale a pena. Me chame quando você vir.

---

## 6 · Exploração — este é o exercício de verdade

O ponto desta sessão não é produzir *um* catálogo. É entender que parâmetros diferentes
produzem **catálogos diferentes do mesmo céu**.

Estes você roda à mão. Digite o comando, mude um parâmetro, rode de novo, e compare. Tudo
na config pode ser sobrescrito na linha de comando — então você nunca precisa editar um
arquivo para testar um valor.

### 6a · `DETECT_THRESH` e `DETECT_MINAREA`

Rode **pelo menos três combinações escolhidas por você.** Para isso você pode mudar os
valores diretamente no `default.sex`, ou indicar no terminal os parâmetros do arquivo de
configuração que você quer mudar. Por exemplo, uma frouxa:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DETECT_THRESH 1.5 -DETECT_MINAREA 3 \
    -CATALOG_NAME thresh_loose.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME seg_loose.fits
```

e uma estrita:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -DETECT_THRESH 3.0 -DETECT_MINAREA 5 \
    -CATALOG_NAME thresh_strict.cat -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION -CHECKIMAGE_NAME seg_strict.fits
```

Para cada execução, **leia a última linha que o SExtractor imprime** — ela te diz quantos
objetos foram detectados e quantos sobreviveram. Anote os números.

Depois olhe os dois segmentation maps lado a lado:

```bash
ds9 seg_loose.fits seg_strict.fits \
    -lock frame image -tile
```

**Não há resposta certa.** Procurando a contrapartida de um transiente? Você quer
completeza. Medindo uma função de luminosidade? Fontes espúrias no extremo fraco vão te
destruir.

**A ferramenta não decide por você.**

### 6b · `DEBLEND_MINCONT`

Encontre a galáxia maior e mais extensa do seu cutout (abra a imagem no DS9 e procure).
Rode o mesmo campo duas vezes, mudando só `DEBLEND_MINCONT`:

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

Olhe o segmentation map ao redor dessa galáxia nas duas vezes. Dê zoom.

Ela fragmenta? **Deveria?** (Isso depende inteiramente do que você está tentando medir —
que é justamente o ponto.)

---

Assim que você encontrar os parâmetros com os quais está satisfeito para estes, defina-os
**diretamente no `default.sex`**, para não ter que ficar passando-os na linha de comando
no resto do tutorial.

## 7 · PSFEx

Como mencionamos no curso, a determinação de uma boa PSF é fundamental para ter uma boa
separação entre uma fonte extensa e uma pontual — além de permitir ter uma boa abertura
PSF para medir a magnitude das estrelas. Para a separação entre estrela e galáxia temos
estas duas opções:

`CLASS_STAR` é uma rede neural. Funciona — até o S/N cair, e aí ela colapsa em direção a
0,5. Ela para de saber, e não te avisa.

`SPREAD_MODEL` não colapsa. Mas precisa saber como uma estrela se parece **naquela
posição exata, naquela imagem exata**. É isso que o PSFEx constrói.

### O PSFEx não lê a sua imagem. Ele lê um catálogo do SExtractor.

O que significa que o fluxo é:

```
SExtractor (passo 1)  →  prepsfex.cat   (FITS_LDAC, com VIGNET)
        ↓
PSFEx                 →  *.psf
        ↓
SExtractor (passo 2)  →  catálogo final com SPREAD_MODEL
```

### 7a · Escreva `prepsfex.param`

**Este é um `.param` diferente do científico.** É curto. Precisa conter:

```
VIGNET(35,35)
```

**`VIGNET` é a razão inteira de esse passo existir.** Ele diz ao SExtractor para salvar um
recorte de pixels ao redor de cada fonte — porque o PSFEx nunca abre a sua imagem, então
os pixels precisam viajar *dentro do catálogo*.

Você também precisa: posições, `FLUX_RADIUS`, um fluxo de abertura e seu erro,
`ELONGATION`, `SNR_WIN`, e `FLAGS`.

> **Importante:** a abertura que você escolher precisa ser uma **abertura FIXA, não
> Kron** — você quer algo que não dependa da morfologia medida. Por exemplo, uma abertura
> de 3″.

Olhe `psfex -dd` e encontre `PHOTFLUX_KEY`. **O que você nomear no seu `.param` tem que
bater com o que o PSFEx espera ler.** Se não baterem, o PSFEx morre com um erro pouco útil
(normalmente um segmentation fault).

Depois rode o SExtractor para produzir o catálogo com o qual o PSFEx vai funcionar —
chame-o, por exemplo, de `prepsfex.cat`.

### 7b · Passo 1

Duas coisas tornam esta execução diferente da científica:

- `-CATALOG_TYPE FITS_LDAC` — **obrigatório.** O PSFEx não lê outra coisa. (Se você
  esquecer, o PSFEx quebra com um segmentation fault e sem mensagem útil.)
- um `DETECT_THRESH` **mais alto** — este não é o run científico. Para ajustar uma PSF
  você quer *estrelas boas*, não completeza. Tente 5σ.

Além disso: se seu `.param` diz `FLUX_APER(1)`, então `PHOT_APERTURES` tem que ter
**exatamente um** valor.

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME prepsfex.cat -CATALOG_TYPE FITS_LDAC \
    -PARAMETERS_NAME config/prepsfex.param \
    -DETECT_THRESH 5.0 -ANALYSIS_THRESH 5.0 -PHOT_APERTURES 10
```

Seu catálogo vai ser grande. São os recortes do `VIGNET`. Esperado.

**Confira que ele realmente saiu como LDAC** antes de entregá-lo ao PSFEx:

```bash
python3 -c "from astropy.io import fits; print([h.name for h in fits.open('prepsfex.cat')])"
```

Você quer ver `LDAC_IMHEAD` e `LDAC_OBJECTS`. Se você vir um `OBJECTS` simples, o
`-CATALOG_TYPE FITS_LDAC` não pegou — essa é a causa #1 do segfault.

### 7c · Rode o PSFEx

Edite `config/default.psfex`. Os parâmetros que importam:

| | O que controla | Pense em |
|---|---|---|
| `PSF_SIZE` | tamanho do modelo em pixels | **tem que ser menor que o seu VIGNET** |
| `PSFVAR_DEGREES` | grau do polinômio da variação espacial | 0 = PSF constante (rápido, e falso). 2 = sensato. 4 = superajusta se você não tiver muitas estrelas |
| `SAMPLE_FWHMRANGE` | qual FWHM conta como estrela | **em PIXELS.** Seu seeing cai dentro? |
| `SAMPLE_MINSNR` | quão fraca uma estrela pode ser | estrelas fracas → PSF ruidosa |
| `SAMPLE_MAXELLIP` | quão alongada | este é o seu filtro anti-galáxias |

```bash
psfex prepsfex.cat -c config/default.psfex
```

### 7d · Leia a saída. Não pule.

O PSFEx imprime uma linha como:

```
accepted/total   samp.   chi2/dof   FWHM   ellip.   resi.
```

**Julgue a sua própria PSF:**

- **`chi2/dof`** — deve estar perto de 1. Se for 3, seu modelo não descreve seus dados.
- **`FWHM`** — bate com o header? (Deveria.)
- **`ellip.`** — perto de 0 significa redonda. Um valor grande é um problema de
  rastreamento ou flexão.
- **`accepted`** — você precisa de ~10 estrelas por termo do polinômio. Grau 2 em (x,y)
  tem 6 termos → **você quer 60+ estrelas**. Você as tem?

Depois olhe os check-plots. `CHECKPLOT_DEV` — tente `PNG` primeiro; se o seu PLPlot não
tiver, use `SVG` ou `PSC`.

**O que mais importa é `SAMPLES`** — as estrelas que o PSFEx realmente usou. Se houver
galáxias ali, sua PSF está contaminada. Volte e aperte `SAMPLE_MINSNR` e
`SAMPLE_MAXELLIP`.

> Uma PSF ruim te dá um `SPREAD_MODEL` ruim e um `MAG_PSF` ruim — **silenciosamente**.
> Nada quebra. Você só obtém respostas erradas.

### 7e · Passo 2

Copie seu `.param` científico, adicione `SPREAD_MODEL`, `SPREADERR_MODEL`, `MAG_PSF`,
`MAGERR_PSF`. Rode o SExtractor de novo com `-PSF_NAME <seu>.psf`.

**Isto vai ser lento.** Para cada fonte, o SExtractor agora avalia o polinômio para
construir a PSF naquela posição, e faz um ajuste iterativo. É por isso que custa o que
custa.

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

## 8 · Duas bandas — e o erro que você está prestes a cometer

Hora de um experimento rápido. Normalmente, quando queremos um catálogo que caracterize
estrelas e galáxias, a forma mais limpa é usar a PSF — mas como você acabou de ver, é
lenta. Então vamos fazer uma rodada rápida com **dois filtros**, para entender como se
trabalha quando você tem mais de uma banda, porque quase nunca trabalhamos com um único
filtro.

Há duas maneiras de gerar os catálogos: a maneira **errada** e a **certa**.

### O jeito errado (faça mesmo assim — você precisa ver quebrar)

Rode o SExtractor **duas vezes, independentes**, uma por banda. Cada banda detecta e mede
por conta própria. Para este experimento, a abertura `AUTO` sozinha basta — você pode
remover as outras aberturas. Use o zero point daquela banda (da tabela na seção 0):

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME single_R.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.784 \
    -WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits
```

Lembre que no `default.sex` escrevemos `GAIN`, `SATUR_LEVEL` e `SEEING_FWHM` para o filtro
**r** — então para **g** você tem que mudá-los:

```bash
sex data/HYDRA_D_0003_G.fits -c config/default.sex \
    -CATALOG_NAME single_G.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.920 \
    -GAIN <G_gain> \
    -SATUR_LEVEL <G_satur> \
    -SEEING_FWHM <G_seeing> \
    -WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE data/HYDRA_D_0003_G.weight.fits
```

Abra os dois catálogos no TOPCAT. O que você vê? São iguais?

### O jeito certo: modo dual

A sintaxe são duas imagens separadas por **vírgula, sem espaço**:

```bash
sex detection.fits,measurement.fits -c config/default.sex
```

As fontes são **detectadas** na primeira imagem, **medidas** na segunda.

Detecte em `r` — é profunda e tem o melhor seeing. Depois meça através *dessas mesmas
aberturas*, *nessas mesmas posições*, nas duas bandas. Então você roda duas vezes, e a
**primeira** imagem é sempre `r`:

```bash
# detecta em R, mede em G
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_G.fits -c config/default.sex \
    -CATALOG_NAME dual_G.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.920 \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_G.weight.fits
```

```bash
# detecta em R, mede em R (sim, R sobre si mesma)
sex data/HYDRA_D_0003_R.fits,data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME dual_R.cat -CATALOG_TYPE FITS_1.0 \
    -MAG_ZEROPOINT 22.784 \
    -WEIGHT_TYPE MAP_WEIGHT,MAP_WEIGHT \
    -WEIGHT_IMAGE data/HYDRA_D_0003_R.weight.fits,data/HYDRA_D_0003_R.weight.fits
```

No modo dual, `WEIGHT_TYPE` e `WEIGHT_IMAGE` recebem **dois** valores separados por
vírgula — um para a imagem de detecção, um para a de medição.

Como as duas bandas foram detectadas em `r`, **a linha *i* é a mesma fonte nos dois
catálogos.** Não precisa cross-matchear. Esse é o ponto.

### Por que isto é o jogo inteiro

A abertura de Kron é **adaptativa** — seu tamanho depende da forma medida *naquela
imagem*. O seeing em `g` é diferente, então a fonte pode parecer mais gorda, então **a
elipse sai de um tamanho diferente**. Mais área, mais fluxo. Sua cor agora tem um viés que
não tem nada a ver com a estrela.

E é pior: uma fonte fraca detectada em `r` pode **não ser detectada em `g`**. Duas fontes
separadas em `r` podem ser **um único blob** em `g`. Não há nada para cross-matchear.

**Mesma abertura, mesma posição, cada banda. Sem isso, não há cor.**

Abra os catálogos no TOPCAT de novo. O que você vê agora? São iguais?

---

## Se você travar

`solutions/` tem uma versão resolvida de cada passo. **Use se você estiver travado por
mais de dez minutos** — estar travado não é o exercício.

Mas pense primeiro. Os comandos são a parte fácil.

---

## Referência

- Manual do SExtractor — https://sextractor.readthedocs.io
- Manual do PSFEx — https://psfex.readthedocs.io
- Bertin & Arnouts 1996, A&AS 117, 393
