<!-- LANGUAGE -->
[English](README.md) · [Español](README.es.md) · **Português**

---

# Construindo catálogos astronômicos com o Source Extractor

**Atividade prática 2 — Escola S-PLUS**
Gissel Montaguth

---

## O que você vai fazer hoje

Você vai construir um catálogo fotométrico de um campo real do S-PLUS, em três bandas, e
vai usá-lo para separar estrelas de galáxias.

Mas esse não é bem o ponto. O ponto é este:

> **Um catálogo não é a verdade. É uma medição, e contém decisões.**

Cada parâmetro que você definir hoje é uma decisão. Ao final da sessão eu quero que você
consiga dizer, para cada um: *o que escolhi, e por quê?*

**Eu não vou te dar os arquivos de configuração.** Você vai construí-los. É essa a maior
parte da sessão.

---

## 0 · Pegue os dados

As imagens estão anexadas ao **Release** do GitHub, não ao repositório (são grandes
demais para o git).

```bash
git clone <REPO_URL>
cd splus-sextractor-workshop

# baixa os cutouts (~100 MB)
bash scripts/00_get_data.sh
```

Você deve terminar com, em `data/`:

```
HYDRA_D_0003_U.fits          HYDRA_D_0003_U.weight.fits
HYDRA_D_0003_G.fits          HYDRA_D_0003_G.weight.fits
HYDRA_D_0003_R.fits          HYDRA_D_0003_R.weight.fits
zeropoints.txt
```

São cutouts de 2000 × 2000 do S-PLUS iDR6, já descomprimidos.

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

# se compilou ou usou conda, tente:
find / -name "default.nnw" 2>/dev/null
find / -name "*.conv" 2>/dev/null | head
```

Copie o que precisar para `config/`:

```bash
cp <caminho>/default.nnw          config/
cp <caminho>/gauss_2.0_5x5.conv   config/
cp <caminho>/gauss_4.0_7x7.conv   config/     # talvez você queira depois
```

**Para que serve cada arquivo:**

| Arquivo | O que é | Você edita? |
|---|---|---|
| `default.sex` | parâmetros de execução | **sempre** |
| `default.param` | **quais colunas você quer na saída** | **sempre** |
| `*.conv` | o kernel de filtragem | você *escolhe* um, não edita |
| `default.nnw` | a rede neural treinada do `CLASS_STAR` | nunca |

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

Agora olhe os nomes dos kernels — `gauss_2.0_5x5.conv`, `gauss_4.0_7x7.conv`. **O número
é o FWHM em pixels.** Escolha o mais próximo do seu.

Por quê? A convolução antes da detecção é um **filtro casado (matched filter)**: se o
kernel tem a forma da fonte que você procura, você maximiza o S/N de detecção. E para uma
fonte pontual, a fonte que você procura *é a PSF*.

---

## 3 · O zero point

Abra `data/zeropoints.txt`.

Você vai ver que cada banda tem mais de um número. **O zero point do S-PLUS iDR6 não é um
número — é um modelo espacial que varia ao longo do tile.**

Olhe `std` e `range` de cada banda. Depois decida:

- Um único ZP mediano é suficiente para o que você está fazendo?
- A resposta é a mesma em `u` e em `r`?

**Seja o que você decidir, você precisa conseguir defender.** Anote.

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

**Escreva o seu.** Você precisa, no mínimo:

- um identificador e uma posição (pixel *e* céu)
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

Para uma saída vetorial como três aberturas, a sintaxe é `MAG_APER(3)` — e **o número
entre parênteses tem que bater com quantos valores você pôs em `PHOT_APERTURES`.**

`PHOT_APERTURES` é um **diâmetro em pixels**. Se você quer uma abertura de 3″:
`3 / 0,55 = 5,45 px`.

---

## 5 · Sua primeira execução

Agora edite `config/default.sex` com tudo que você descobriu, e rode:

```bash
sex data/HYDRA_D_0003_R.fits -c config/default.sex \
    -CATALOG_NAME cat/r_first.cat \
    -CATALOG_TYPE FITS_1.0 \
    -CHECKIMAGE_TYPE SEGMENTATION,BACKGROUND \
    -CHECKIMAGE_NAME check/seg.fits,check/bkg.fits
```

**Nota:** qualquer coisa no arquivo de config pode ser sobrescrita na linha de comando
com `-PARAM valor`. Não é uma comodidade — é o que torna viável rodar doze bandas com uma
única config.

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
ds9 data/HYDRA_D_0003_R.fits check/seg.fits check/bkg.fits \
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

### 6a · `BACK_SIZE`

```bash
bash scripts/02_explore_backsize.sh
```

Isso roda a mesma imagem com `BACK_SIZE` = 32, 64, 256 e salva os modelos de fundo.
Olhe-os **com a escala travada** (isso importa — com auto-escala a comparação é mentira):

```bash
ds9 check/bkg_32.fits check/bkg_64.fits check/bkg_256.fits \
    -scale limits -0.02 0.05 -lock frame image -lock scale yes -tile
```

Depois meça a consequência:

```bash
python3 scripts/03_compare_backsize.py
```

**Perguntas para responder:**
- Qual valor coloca suas *estrelas* dentro do modelo de céu?
- Qual valor faz as fontes brilhantes saírem mais fracas, e por quê?
- As duas curvas se cruzam? Em que magnitude?
- **Quão grande é o efeito, em magnitudes?** É grande o suficiente para importar?

A última pergunta é a importante. Não chute. Meça.

### 6b · `DETECT_THRESH` e `DETECT_MINAREA`

Rode pelo menos três combinações escolhidas por você. Para cada uma, registre:
- quantos objetos foram detectados
- quantos sobrevivem a `FLAGS == 0`

Depois olhe os segmentation maps lado a lado.

**Não há resposta certa.** Procurando a contrapartida de um transiente? Você quer
completeza. Medindo uma função de luminosidade? Fontes espúrias no extremo fraco vão te
destruir.

**A ferramenta não decide por você.**

### 6c · `DEBLEND_MINCONT`

Encontre a galáxia maior e mais extensa do seu cutout. Rode com
`DEBLEND_MINCONT = 0.0001` e com `0.1`. Olhe o segmentation map nas duas vezes.

Ela fragmenta? Deveria?

---

## 7 · PSFEx

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

Olhe `psfex -dd` e encontre `PHOTFLUX_KEY`. **O que você nomear no seu `.param` tem que
bater com o que o PSFEx espera ler.** Se não baterem, o PSFEx morre com um erro pouco
útil.

### 7b · Passo 1

Duas coisas tornam esta execução diferente da científica:

- `-CATALOG_TYPE FITS_LDAC` — **obrigatório.** O PSFEx não lê outra coisa.
- um `DETECT_THRESH` **mais alto** — este não é o run científico. Para ajustar uma PSF
  você quer *estrelas boas*, não completeza. Tente 5σ.

Além disso: se seu `.param` diz `FLUX_APER(1)`, então `PHOT_APERTURES` tem que ter
**exatamente um** valor.

Seu catálogo vai ser grande. São os recortes do `VIGNET`. Esperado.

### 7c · Rode o PSFEx

Edite `config/default.psfex`. Os parâmetros que importam:

| | O que controla | Pense em |
|---|---|---|
| `PSF_SIZE` | tamanho do modelo em pixels | **tem que ser menor que o seu VIGNET** |
| `PSFVAR_DEGREES` | grau do polinômio da variação espacial | 0 = PSF constante (rápido, e falso). 2 = sensato. 4 = superajusta se você não tiver muitas estrelas |
| `SAMPLE_FWHMRANGE` | qual FWHM conta como estrela | **em PIXELS.** Seu seeing cai dentro? |
| `SAMPLE_MINSNR` | quão fraca uma estrela pode ser | estrelas fracas → PSF ruidosa |
| `SAMPLE_MAXELLIP` | quão alongada | este é o seu filtro anti-galáxias |
| `SAMPLE_FLAGMASK` | quais FLAGS rejeitar | **uma estrela saturada tem o núcleo achatado. Se entrar, sua PSF é mentira.** |

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

---

## 8 · Três bandas — e o erro que você está prestes a cometer

Agora faça `u`, `g`, `r`.

### O jeito errado (faça mesmo assim — você precisa ver quebrar)

Rode o SExtractor **três vezes, independentes**, uma por banda. Cross-match por posição.
Calcule cores.

### O jeito certo: modo dual

```bash
sex detection.fits,measurement.fits -c config/default.sex
```

As fontes são **detectadas** na primeira imagem, **medidas** na segunda.

Detecte em `r` — é profunda e tem o melhor seeing. Depois meça através *dessas mesmas
aberturas*, *nessas mesmas posições*, nas três bandas.

### Por que isto é o jogo inteiro

A abertura de Kron é **adaptativa** — seu tamanho depende da forma medida *naquela
imagem*. O seeing em `u` é pior, então a fonte parece mais gorda, então **a elipse sai
maior**. Mais área, mais fluxo. Sua cor agora tem um viés que não tem nada a ver com a
estrela.

E é pior: uma fonte fraca detectada em `r` pode **não ser detectada em `u`**. Duas fontes
separadas em `r` podem ser **um único blob** em `u`. Não há nada para cross-matchear.

**Mesma abertura, mesma posição, cada banda. Sem isso, não há cor.**

```bash
bash scripts/04_dual_mode.sh
```

---

## 9 · O entregável

Faça o diagrama cor-cor — `(u−g)` vs `(g−r)` — **duas vezes**: uma a partir do seu
catálogo de modo dual, outra a partir dos catálogos banda por banda.

```bash
python3 scripts/05_color_color.py
```

Colora os pontos por `SPREAD_MODEL`.

**Olhe os dois diagramas.** A sequência estelar é mais larga em um deles. Esse
espalhamento extra não é ruído fotométrico. **São as suas aberturas discordando entre
si.**

Nada quebrou. Os dois catálogos parecem perfeitamente respeitáveis no TOPCAT.

Um deles só tem cores que não significam nada.

---

## O que entregar

1. **Seu `default.sex`**, com uma justificativa curta para cada parâmetro que você mudou
   do padrão. *"Por que você escolheu esse `BACK_SIZE`?"* é uma pergunta justa.

2. **Seu catálogo final** (`.fits`), com as três bandas medidas através de aberturas
   idênticas.

3. **Duas figuras:**
   - o diagrama cor-cor, colorido por `SPREAD_MODEL`
   - um diagnóstico à sua escolha que te convenceu de que algo estava funcionando (ou
     não)

4. **Duas frases sobre o que deu errado e como você diagnosticou.**

**O ponto 4 é o que eu de fato avalio.** Todo o resto pode ser produzido copiando
comandos. O ponto 4 não.

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
