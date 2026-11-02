# Documentação técnica

Complementa o [README](../README.md) com o que não cabe nele: contratos da API, o método geográfico, os limites do modelo, as correções feitas na auditoria e a metodologia de benchmark. A teoria de cada algoritmo fica em `lab/catalog.py` e aparece na seção **Teoria** da aplicação.

## 1. Camadas

| Camada | Arquivos | Responsabilidade |
|---|---|---|
| Algoritmos do radar | `radar/closest_pair.py`, `radar/brute_force.py`, `radar/result.py` | Par mais próximo D&C (com trilha e árvore) e força bruta; não conhecem aeronaves. |
| Geometria | `radar/geo.py`, `radar/geodesic.py` | Haversine, corda 3D, plano tangente, par geodésico exato e pares abaixo de um raio. |
| Domínio do radar | `radar/bands.py`, `radar/generator.py` | Faixas de altitude, varredura e resumo; simulação por seed e leitura validada do snapshot. |
| Laboratório | `lab/` | Algoritmos D&C instrumentados, referências independentes, cenários, catálogo teórico, execução/benchmark e exercícios. |
| API | `app.py` | Validação de parâmetros, códigos HTTP e JSON; sem lógica algorítmica. |
| Interface | `templates/index.html`, `static/` | Página única, navegação por hash, módulos ES carregados sob demanda, sem build. |

O único estado compartilhado entre requisições é o `threading.Lock` que impede dois benchmarks/comparações simultâneos.

## 2. API

Todas as rotas devolvem JSON. Erros têm a forma `{"error": "mensagem"}` e nunca incluem stack trace. O modo debug só liga com `FLASK_DEBUG=1`.

| Método e rota | Parâmetros | Resposta | Erros |
|---|---|---|---|
| `GET /api/health` | — | `status`; snapshot: `available`, `records`, `captured_at_local` | — |
| `GET /api/scan` | `source` (`sim`\|`opensky`), `n` 2–3000, `seed` 0–2³¹−1, `minutes` 0–240, `threshold_nm` 0,5–20, `band_ft` 500\|1000\|2000, `all_pairs` 0\|1 | `source`, `model`, `aircraft[]` (com `id` e `flight_level`), `bands[]`, `summary` | 400; 503 snapshot indisponível |
| `GET /api/steps` | os de tráfego + `band` (FL) opcional | trilha do par mais próximo na faixa (até 64 aeronaves), `bands`, `sampled` | 400 |
| `GET /api/visualizer/cases` | — | casos didáticos | — |
| `POST /api/visualizer` | `{case, n, seed}` ou `{points: [[x, y], …]}` (2–64 pontos finitos, \|c\| ≤ 10⁶) | `points`, `steps`, `tree`, `result`, `verification`, `pseudocode` | 400 |
| `GET /api/lab/catalog` | — | teoria, pseudocódigo, cenários, pivôs e limites | — |
| `POST /api/lab/run` | `{algorithm, seed, scenario, n}` ou `{algorithm, seed, values}`; `params.pivot`, `params.k` | `output`, `metrics`, `steps` (n ≤ 64), `verification`, `kadane` | 400 |
| `GET /api/compare` | `scenario`, `n` 2–1000, `seed`, `repeats` 1–7 | uma linha por algoritmo | 400; 429 |
| `GET /api/benchmark` | `algorithm`, `scenario`, `sizes` (até 8), `repeats` 1–7, `seed`, `pivot`, `warmup` | `rows[]` com mediana/mín/máx/desvio e amostras, `environment` | 400; 429 |
| `GET /api/exercises/new` | `type`, `seed` | enunciado sem gabarito | 400 |
| `POST /api/exercises/check` | `{type, seed, answer}` | `correct`, `expected`, `explanation` | 400 |

Corpo limitado a 256 KB (413). Rota inexistente em `/api/` devolve 404 em JSON; método errado, 405.

**Faixa (`bands[]`):** `flight_level`, `aircraft_count`, `pair`, `distance_km`/`distance_nm` (círculo máximo), `alert` (par mínimo abaixo do limiar), `comparisons` (cálculos de distância do D&C no plano), `candidate_pairs` (pares conferidos na certificação), `projection_corrected` e, com `all_pairs=1`, `close_pairs`, `close_pairs_candidates`, `close_pairs_truncated` (máx. 500 pares por faixa).

**Etapas do par mais próximo (`steps[]`):** `kind` (`divide`\|`base`\|`combine`), `line` (linha do pseudocódigo), `node` (índice em `tree`), `depth`, `size`, `members`, `middle_x`, `strip`, `compared` (pares cuja distância foi calculada na etapa), `delta` = min(δ esq., δ dir.), `left`/`right`/`best` (melhores pares **locais** do subproblema) e `comparisons_total`. As etapas do laboratório têm `kind`, `line`, `text` e os campos de cada algoritmo; a trilha para em 5.000 etapas e marca `truncated`.

## 3. Par geodésico exato

A versão anterior escolhia o par numa projeção equirretangular de origem fixa (−15°, −52°), que distorce distâncias leste-oeste longe dessa latitude (≈ +15% a 33°S). Os testes reproduzem dois erros dela: um caso construído a 33°S e a simulação seed 1, n = 1500, FL280 (12,508 km relatados × 12,470 km reais).

O método atual (`radar/geodesic.py`):

1. Projeta cada ponto, como vetor 3D na esfera de raio 6.371 km, ortogonalmente no plano tangente ao centro da faixa. Por ser projeção ortogonal, `d_plano ≤ corda_3D` para qualquer par.
2. Roda o par mais próximo D&C no plano, em O(n log n); a corda real r do par encontrado limita a menor corda por cima.
3. Todo par com corda < r tem `d_plano < r`; uma grade de lado r lista esses k candidatos em O(n + k) e a corda real decide.
4. O arco de círculo máximo cresce com a corda, então o par de menor corda é o par geodésico mais próximo.

O resultado é exato no modelo esférico em qualquer entrada. O custo extra O(n + k) depende da dispersão: em 3.000 pontos sobre um recorte do tamanho do Brasil, k = 1; em 3.000 pontos uniformes no globo inteiro, a projeção sobrepõe hemisférios opostos e k = 5.259 — ainda muito abaixo dos 4,5 milhões de pares da força bruta. A grade é hashing espacial, não dividir e conquistar; o mesmo vale para a listagem de todos os pares abaixo do limiar.

## 4. Limites do modelo

- O limiar horizontal (5 NM por padrão, 0,5–20) é um parâmetro do modelo; uma faixa abaixo dele indica só que dois pontos do modelo estão mais próximos que esse valor.
- Faixas verticais por arredondamento meio para cima (500, 1.000 ou 2.000 ft); aeronaves perto do limite entre duas faixas contam como separadas. Não há projeção de trajetória nem tolerância vertical contínua.
- Terra esférica; altitude e elipsoide não entram na distância horizontal.
- Snapshot: captura única (2026-11-01 19:28:52 UTC−03:00); posições podem estar defasadas e níveis baixos correspondem a áreas de terminal.
- Simulação: voos retos entre 11 aeroportos, ruído gaussiano, FL280–FL410.

## 5. Correções feitas na auditoria

| Problema | Correção |
|---|---|
| Par do plano equirretangular diferente do par na esfera | plano tangente + certificação por grade (seção 3) |
| `round()` arredondava empates para o par (36.500 ft → FL360, 37.500 ft → FL380) | `floor(x/largura + 0,5)` |
| A trilha mostrava o melhor par global como resultado do subproblema | cada chamada devolve o próprio melhor par; δ = min(esq., dir.) |
| `strip[pos + 1:]` copiava a faixa a cada ponto | laço por índice |
| NaN/∞ e pontos malformados aceitos | `validate_points` |
| Parâmetros inválidos corrigidos em silêncio; `debug=True` fixo | HTTP 400/413/429/503 coerentes; debug só com `FLASK_DEBUG=1` |
| Registro de passos copiava o vetor mesmo com a trilha desligada (Merge Sort 10× mais lento) | registro protegido por `if trace` |
| Resposta atrasada do radar reescrevia a URL de outra seção com `replaceState` | só reescreve enquanto o radar é a seção ativa |
| A reprodução do radar seguia buscando dados com a seção escondida | as seções param timers ao sair (`onHide`) |
| Execução cancelada no laboratório reabilitava o botão da execução mais nova | só a execução mais recente libera o estado de carregamento |

## 6. Metodologia de benchmark

- Mesma entrada (gerada pela seed) para D&C e referência em cada n; aquecimento descartado; ordem D&C/referência alternada a cada repetição.
- Relata mediana, mínimo, máximo, desvio-padrão e todas as amostras, com ambiente (Python, SO, CPU) e data do servidor.
- Operações contadas pelo próprio código, na mesma unidade dos dois lados: cálculos de distância, comparações entre elementos ou comparações entre somas.
- Limites: até 8 tamanhos e 7 repetições; n ≤ 20.000 (≤ 3.000 quando o algoritmo pode degradar para Θ(n²)); referências Θ(n²) só até n = 2.000; orçamento de 20 s; um benchmark por vez. O que não roda aparece como não executado, nunca com valor estimado.
- Tempo de parede inclui interpretador e alocação: compare inclinações no gráfico log-log, não valores absolutos entre máquinas.

## 7. Cenários em JSON

O Laboratório e o Visualizador exportam e importam a entrada da última execução. O arquivo é lido só no navegador (até 256 KB), validado com os mesmos limites do servidor e validado de novo pela API ao executar.

```json
{ "tipo": "radar-dc-cenario", "versao": 1, "modulo": "laboratorio",
  "algoritmo": "quickselect", "seed": 21, "parametros": { "pivot": "mediana_medianas", "k": 5 },
  "valores": [5, -2, 9, 1] }
```

```json
{ "tipo": "radar-dc-cenario", "versao": 1, "modulo": "visualizador", "pontos": [[0, 0], [3, 4], [10, 10]] }
```

`algoritmo` ∈ {`merge_sort`, `quick_sort`, `quickselect`, `inversions`, `max_subarray`}; `valores`: 1 a 2.000 inteiros com |v| ≤ 10⁹; `pontos`: 2 a 64 pares finitos com |c| ≤ 10⁶.
