<div align="center">

# ✈️ Radar de Conflitos Aéreos

### Laboratório de Algoritmos — Dividir e Conquistar

**Projeto de Algoritmos · PA 26.2**

![Status](https://img.shields.io/badge/status-funcional-brightgreen)
![Python](https://img.shields.io/badge/python-3.14%20(testado)-blue)
![Flask](https://img.shields.io/badge/flask-3.1-black)
![Algoritmos](https://img.shields.io/badge/algoritmos%20D%26C-6-blueviolet)
![Testes](https://img.shields.io/badge/testes-457%20%2B%2045%20e2e%20aprovados-success)
![Dados](https://img.shields.io/badge/dados-simula%C3%A7%C3%A3o%20%2B%20snapshot%20OpenSky-informational)

Repositório: [projeto-de-algoritmos-2026/G21_DividirEConquistar_PA-26.2](https://github.com/projeto-de-algoritmos-2026/G21_DividirEConquistar_PA-26.2)

</div>

---

## 🎯 Objetivos

- Aplicar o **par de pontos mais próximos** por dividir e conquistar a um caso de uso concreto: encontrar, em cada faixa de altitude, as duas aeronaves mais próximas de um radar simulado, em O(n log n) em vez de O(n²).
- Mostrar **dividir, conquistar e combinar** acontecendo de verdade: cada etapa exibida vem da execução real, com caso-base, recorrência, invariantes e comparações contadas.
- Estudar outros algoritmos clássicos de D&C — Merge Sort, Quick Sort, Quickselect, contagem de inversões e subarray de soma máxima — sempre conferidos com uma referência independente.
- Medir a diferença entre o modelo assintótico e o tempo real com benchmarks reproduzíveis, sem números fabricados.

---

## 📖 Sobre o projeto

O núcleo é um **radar simulado**. As aeronaves são agrupadas por faixa de altitude; em cada faixa, o par mais próximo é calculado por dividir e conquistar e comparado com um limiar horizontal configurável (5 NM por padrão). A fonte pode ser uma **simulação determinística** por seed ou um **snapshot histórico** da OpenSky Network guardado no repositório.

A versão anterior escolhia o par numa projeção plana de origem fixa e só depois media a distância na esfera, o que podia indicar o par errado (caso reproduzido nos testes: 12,508 km relatados contra 12,470 km reais). Agora o D&C roda no **plano tangente** de cada faixa e uma busca em grade **certifica o par geodésico exato** — detalhes em [docs/documentacao-tecnica.md](docs/documentacao-tecnica.md).

Ao redor do radar há um laboratório com visualizador recursivo, cinco outros algoritmos de D&C, comparação lado a lado, benchmarks, teoria e exercícios.

A fonte dos dados é sempre identificada na interface: **simulação determinística** ou **snapshot histórico** com a data da captura. Os limites do modelo (limiar como parâmetro, faixas verticais, Terra esférica) estão descritos objetivamente na [documentação técnica](docs/documentacao-tecnica.md#4-limites-do-modelo).

---

## 🚀 Funcionalidades

| Seção | O que faz |
|---|---|
| **Visão geral** | Estado do servidor e das fontes (snapshot com data de captura), indicadores de uma varredura real com os parâmetros padrão (faixas, menor separação, cálculos D&C × força bruta), atalhos para os oito módulos e roteiro de estudo |
| **Radar** | Mapa Leaflet; simulação (2–3.000 aeronaves, seed, minuto 0–240, reprodução/pausa/reinício e velocidade) ou snapshot histórico com data de captura; limiar de 0,5 a 20 NM; faixas de 500, 1.000 ou 2.000 ft; cenários prontos; filtros por callsign, empresa, faixa e estado; cartões de resumo (aeronaves, faixas analisadas, faixas abaixo do limiar, menor separação, tempo, cálculos de distância); tabela ordenável; seleção e destaque do par; listagem opcional de **todos** os pares abaixo do limiar; link compartilhável |
| **Visualizador** | Par mais próximo passo a passo: divisão pela mediana, casos-base, faixa central ±δ, pares comparados, melhor par **local** de cada chamada, árvore de recursão e pseudocódigo com a linha atual; 7 casos didáticos, pontos digitados ou uma faixa do radar; navegação por botões, barra, velocidade e teclado; cenário exportável/importável em JSON |
| **Laboratório** | Merge Sort, Quick Sort (3 pivôs), Quickselect (4 pivôs, inclusive mediana das medianas), contagem de inversões e subarray de soma máxima; 8 cenários por seed ou valores digitados; barras animadas, pseudocódigo, métricas reais e verificação; exportação e importação do cenário em JSON |
| **Comparação** | Os seis algoritmos contra suas referências na mesma entrada: tempo mediano, operações na mesma unidade e verificação |
| **Benchmarks** | Até 8 tamanhos e 7 repetições, aquecimento, ordem alternada, mediana/mín/máx/desvio, gráficos log-log de tempo e operações, ambiente e data; exportação CSV e JSON |
| **Teoria** | Para cada algoritmo: problema, dividir/conquistar/combinar, caso-base, recorrência, aplicação (ou não) do Teorema Mestre, corretude, limitações e complexidade |
| **Exercícios** | Inversões, soma máxima, k-ésimo menor e Teorema Mestre, gerados por seed e corrigidos no servidor |
| **Interface** | Tema escuro e claro, layout responsivo (testado em 1920, 1366, 768 e 390 px), navegação por teclado com foco visível, ARIA, anúncios para leitor de tela, `prefers-reduced-motion`, estados de carregamento/erro/vazio |

---

## 🧠 Algoritmos implementados

### Núcleo — dividir e conquistar

| Algoritmo | Recorrência | Complexidade | Arquivo |
|---|---|---|---|
| Par de pontos mais próximos | T(n) = 2T(n/2) + O(n) | Θ(n log n) | [radar/closest_pair.py](radar/closest_pair.py) |
| Merge Sort (estável) | T(n) = 2T(n/2) + Θ(n) | Θ(n log n) | [lab/sorting.py](lab/sorting.py) |
| Quick Sort (Lomuto) | partição equilibrada 2T(n/2) + Θ(n); pior caso T(n − 1) + Θ(n) | Θ(n log n) esperado; **Θ(n²) no pior caso** | [lab/sorting.py](lab/sorting.py) |
| Quickselect (três vias) | esperado T(n/2) + Θ(n); mediana das medianas T(n/5) + T(7n/10) + Θ(n) | Θ(n) esperado; Θ(n²) pior caso; Θ(n) garantido com mediana das medianas | [lab/selection.py](lab/selection.py) |
| Contagem de inversões | T(n) = 2T(n/2) + Θ(n) | Θ(n log n) | [lab/sorting.py](lab/sorting.py) |
| Subarray de soma máxima | T(n) = 2T(n/2) + Θ(n) | Θ(n log n) | [lab/max_subarray.py](lab/max_subarray.py) |

### Auxiliares e referências (não são D&C)

| Algoritmo | Papel | Complexidade |
|---|---|---|
| Força bruta do par mais próximo | referência e verificação | Θ(n²) |
| Certificação geodésica por grade | garante o par exato na esfera após o D&C | O(n + k), k = candidatos |
| Pares abaixo do limiar por grade | lista todos os pares próximos de uma faixa | O(n + k) |
| Inserção | referência de ordenação e seleção, mesma unidade de comparações | Θ(n²) no pior caso |
| Inversões e subarray por força bruta | referência | Θ(n²) |
| Kadane | comparação extra para o subarray (programação dinâmica) | Θ(n) |

---

## 🏗️ Arquitetura

Flask serve uma página única e uma API JSON. Algoritmos puros não conhecem HTTP nem aeronaves; o domínio do radar usa o algoritmo do par mais próximo; a API só valida parâmetros e serializa. A interface usa módulos ES carregados sob demanda, sem etapa de build. Contratos dos endpoints, método geodésico, limites do modelo e metodologia em [docs/documentacao-tecnica.md](docs/documentacao-tecnica.md).

```
navegador (HTML/CSS/JS + Leaflet)
        │  fetch JSON, cancelável
        ▼
app.py ── validação, códigos HTTP, limites
   ├── radar/  bands → geodesic → closest_pair   (domínio do radar)
   │           generator (simulação e snapshot)
   └── lab/    runner → sorting, selection, max_subarray, references
               catalog (teoria), scenarios, exercises
```

### Estrutura de diretórios

```
.
├── app.py                      API Flask e rotas
├── requirements.txt            dependências de execução
├── requirements-dev.txt        + Playwright para testes de interface
├── pytest.ini
├── data/
│   └── opensky_snapshot.json   snapshot histórico (154 aeronaves)
├── radar/
│   ├── closest_pair.py         par mais próximo D&C, trilha e árvore
│   ├── brute_force.py          referência Θ(n²)
│   ├── geo.py                  haversine, corda 3D, plano tangente
│   ├── geodesic.py             par geodésico exato e pares abaixo do limiar
│   ├── bands.py                faixas de altitude e varredura
│   ├── generator.py            simulação por seed e leitura do snapshot
│   └── result.py
├── lab/
│   ├── sorting.py              Merge Sort, inversões, Quick Sort
│   ├── selection.py            Quickselect
│   ├── max_subarray.py         subarray de soma máxima
│   ├── references.py           referências independentes
│   ├── scenarios.py            cenários de vetores e pontos
│   ├── catalog.py              teoria e pseudocódigo
│   ├── runner.py               execução, verificação, comparação e benchmark
│   ├── exercises.py            exercícios com correção
│   └── metrics.py              contadores e trilha
├── templates/index.html
├── static/
│   ├── css/style.css
│   └── js/                     app, core, catalog, chart, overview, radar,
│                               visualizer, lab, compare, benchmark, theory, exercises
├── tests/                      pytest (unidade, propriedades, API)
│   └── e2e/                    Playwright: conftest, test_ui, test_regressions
└── docs/
    └── documentacao-tecnica.md API, método geodésico, limites e benchmark
```

---

## ⚙️ Instalação

**Pré-requisitos:** Python 3 (testado com 3.14.7), Git e um navegador moderno.

```bash
git clone https://github.com/projeto-de-algoritmos-2026/G21_DividirEConquistar_PA-26.2.git
cd G21_DividirEConquistar_PA-26.2
```

Ambiente virtual no **Windows (PowerShell)**:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

No **Linux/macOS**:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para os testes de interface (opcional): `pip install -r requirements-dev.txt`. Os testes usam o Chromium do Playwright ou, na falta dele, Chrome/Edge instalados; para Firefox e WebKit, `python -m playwright install firefox webkit`.

---

## ▶️ Execução

```bash
python app.py
```

Acesse <http://127.0.0.1:5000>. O modo debug fica desligado; para ligá-lo em desenvolvimento use `FLASK_DEBUG=1 python app.py` (no PowerShell: `$env:FLASK_DEBUG="1"; python app.py`).

Precisa de internet apenas para o mapa (Leaflet pelo unpkg e blocos do OpenStreetMap). Sem internet, o radar mostra um aviso no lugar do mapa e cartões, filtros, tabela e todas as outras seções continuam funcionando.

Testes:

```bash
pytest            # 457 testes de unidade, propriedades e API
pytest -m e2e     # 45 testes de interface com navegador real (E2E_BROWSER=firefox|webkit para outros motores)
```

---

## 📦 Dataset

**Snapshot histórico** — [data/opensky_snapshot.json](data/opensky_snapshot.json)

| Campo | Valor |
|---|---|
| Origem declarada no arquivo | `OpenSky Network /api/states/all` |
| Captura (`captured_at`) | 2026-11-01 22:28:52 UTC (19:28:52 em UTC−03:00) |
| Registros | 154 aeronaves, 0 descartadas pela validação |
| Campos | `callsign`, `lat`, `lon`, `altitude_ft`, `heading`, `speed_kt` |
| Faixas de 1.000 ft | 44 no total, 33 com duas ou mais aeronaves |
| Abaixo de 5 NM | 2 faixas; a menor separação é 0,45 NM em FL020, área de terminal onde esse limiar não se aplica |

É uma captura única, não atualizada e **não é tempo real**. Registros sem coordenadas ou altitude finitas são descartados e contados.

**Simulação** — [radar/generator.py](radar/generator.py): voos em linha reta entre 11 aeroportos brasileiros, prefixos GLO/TAM/AZU/PTB, níveis FL280–FL410, 420–480 kt e ruído gaussiano de 0,06° na posição. A mesma `(n, seed, minuto)` gera sempre o mesmo tráfego; mudar só o minuto move os mesmos voos. Os cenários do laboratório e dos benchmarks também são gerados por seed ([lab/scenarios.py](lab/scenarios.py)).

---

## 📊 Benchmarks

**Metodologia:** a mesma entrada (seed 21, cenário aleatório) para D&C e referência; aquecimento descartado; ordem alternada a cada repetição; mediana de 5 repetições; operações contadas pelo próprio código, na mesma unidade dos dois lados. Referências Θ(n²) só rodam até n = 2.000; acima disso aparecem como não executadas.

**Ambiente da medição:** CPython 3.14.7, Windows 11 (build 26300), AMD64 Family 26 Model 68, 12 CPUs lógicas, 2026-11-02 09:37 (UTC−03:00). Os tempos mudam de máquina para máquina; as contagens de operações não.

Par de pontos mais próximos (cálculos de distância):

| n | D&C (ms) | Força bruta (ms) | Operações D&C | Operações força bruta |
|---:|---:|---:|---:|---:|
| 250 | 0,43 | 2,79 | 260 | 31.125 |
| 500 | 1,28 | 11,53 | 569 | 124.750 |
| 1.000 | 2,49 | 42,85 | 1.126 | 499.500 |
| 2.000 | 6,31 | 169,82 | 2.302 | 1.999.000 |
| 8.000 | 25,09 | não executada | 9.323 | — |

Demais algoritmos em n = 2.000:

| Algoritmo | D&C (ms) | Referência | Ref. (ms) | Operações D&C | Operações ref. | Unidade |
|---|---:|---|---:|---:|---:|---|
| Merge Sort | 3,80 | Inserção | 45,53 | 19.382 | 1.008.796 | comparações |
| Contagem de inversões | 3,95 | Força bruta | 70,54 | 19.382 | 1.999.000 | comparações |
| Subarray de soma máxima | 3,49 | Força bruta | 81,37 | 25.950 | 2.001.000 | comparações de somas |
| Quickselect (pivô aleatório, k = mediana) | 0,70 | Inserção + índice | 48,06 | 10.664 | 1.008.796 | comparações |

Quick Sort em n = 2.000 mostra a dependência do pivô e da entrada: 28.059 comparações com pivô = último em dados aleatórios, contra 1.999.000 (= n(n − 1)/2) com todos os valores iguais, porque a partição de Lomuto manda os iguais para um só lado. O pior caso Θ(n²) com entrada estritamente ordenada é verificado por contagem exata nos testes.

**Limites de execução:** até 8 tamanhos e 7 repetições por pedido; n ≤ 20.000 (≤ 3.000 quando o próprio algoritmo pode degradar para Θ(n²)); orçamento de 20 s por benchmark; um benchmark ou comparação por vez (HTTP 429 para o segundo).

---

## 🎥 Apresentação

<div align="center">
  
  <a href="https://youtu.be/-T7vTaze_fE" target="_blank">
    <img src="https://img.shields.io/badge/YouTube-Apresenta%C3%A7%C3%A3o-red?style=for-the-badge&logo=youtube&logoColor=white" alt="Apresentação no YouTube">
  </a>
</div>

<div align="center">
  <h2>👩‍💻 Contribuidores</h2>
</div>

<table align="center">
  <tr>
    <td align="center">
      <a href="https://github.com/xGabrielCv">
        <img src="https://github.com/xGabrielCv.png" width="90" alt="Jésus Gabriel Carvalho Ventura"/><br>
        <sub><b>Jésus Gabriel Carvalho Ventura</b></sub>
      </a><br>
      <sub>Matrícula: 211062956</sub><br>
      <sub><a href="mailto:jgabrielcv1903@gmail.com">jgabrielcv1903@gmail.com</a></sub>
    </td>
    <td align="center">
      <a href="https://github.com/cwtshh">
        <img src="https://github.com/cwtshh.png" width="90" alt="Gustavo Costa"/><br>
        <sub><b>Gustavo Costa</b></sub>
      </a><br>
      <sub>Matrícula: 211061814</sub><br>
      <sub><a href="mailto:gucosta1719@gmail.com">gucosta1719@gmail.com</a></sub>
    </td>
  </tr>
</table>
