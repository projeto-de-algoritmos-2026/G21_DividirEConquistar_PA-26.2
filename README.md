<div align="center">

# ✈️ Radar de Conflitos Aéreos

**Projeto de Algoritmos — Módulo Dividir e Conquistar — PA 26.2**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Flask](https://img.shields.io/badge/flask-3-black)
![Testes](https://img.shields.io/badge/testes-55%20passing-success)

Repositório: `projeto-de-algoritmos-2026/G21_DividirEConquistar_PA-26.2`

</div>

---

## 🎯 Objetivo

Aplicar o algoritmo do **Par de Pontos mais Próximos** (tópico 3.4 da disciplina) a um problema real: o controle de tráfego aéreo. Duas aeronaves no mesmo nível de voo devem manter uma separação mínima horizontal, e este projeto usa 5 NM (9,26 km), valor típico de radar em rota. Verificar todos os pares custa O(n²). Com dividir e conquistar, cada varredura do radar custa O(n log n).

## 🚀 Funcionalidades

| Aba | Descrição |
|---|---|
| Radar | Mapa com as aeronaves, o par mais próximo de cada nível de voo e alertas abaixo de 5 NM. Usa simulação com seed ou um snapshot real da OpenSky Network |
| Passo a passo | Mostra a divisão, os casos base e a faixa central da combinação sobre o nível de voo mais movimentado |
| Benchmark | Compara dividir e conquistar com força bruta em tempo e número de comparações |

## 🧠 Como funciona

1. As aeronaves são agrupadas por **nível de voo** (FL), a cada 1.000 pés, porque aviões em níveis diferentes já estão separados verticalmente.
2. Latitude e longitude viram coordenadas (x, y) em km por uma projeção equirretangular.
3. Em cada nível, [`closest_pair`](radar/closest_pair.py) resolve o problema:
   - **Dividir:** ordena por x e parte os pontos na mediana.
   - **Conquistar:** resolve cada metade recursivamente, até 3 pontos ou menos, com δ sendo a menor distância já encontrada.
   - **Combinar:** só pontos a menos de δ da divisão podem formar um par melhor. Em ordem de y, cada um deles precisa ser comparado com no máximo 7 vizinhos.
4. A distância do par encontrado é recalculada com a fórmula de haversine, e abaixo de 5 NM o nível gera um alerta.

**Complexidade:** T(n) = 2T(n/2) + O(n), portanto O(n log n). A ordenação inicial por y é reaproveitada em toda a recursão, sem reordenar a cada nível.

## 📊 Resultados

Medidos em Python 3.14 com pontos uniformes, melhor tempo de 3 execuções:

| n | D&C (ms) | Força bruta (ms) | Comparações D&C | Comparações força bruta |
|---:|---:|---:|---:|---:|
| 250 | 0,72 | 4,97 | 143 | 31.125 |
| 500 | 2,05 | 21,01 | 276 | 124.750 |
| 1.000 | 4,13 | 85,14 | 547 | 499.500 |
| 2.000 | 9,16 | 340,84 | 1.084 | 1.999.000 |
| 4.000 | 20,97 | 1.374,77 | 2.165 | 7.998.000 |

Os tempos variam conforme a máquina. A contagem conta apenas cálculos de distância: a diferença de tempo é menor que a de comparações porque o D&C também gasta tempo ordenando e particionando.

## ⚠️ Limitações

- **Precisão da projeção:** a projeção é fiel perto da latitude 15°S. No extremo sul do país, distâncias leste-oeste ficam superestimadas em cerca de 16%, então o par escolhido pode não ser o mais próximo na esfera, embora a distância exibida seja a real.
- **Níveis de voo:** o arredondamento para FL deixa de fora aeronaves em subida ou descida perto do limite entre dois níveis.
- **Um par por nível:** o algoritmo devolve só o par mais próximo, então outros conflitos do mesmo nível não aparecem.
- **Snapshot real:** é uma captura de 154 aeronaves. Os alertas em níveis baixos, como FL020, não indicam incidentes: são aeronaves em área de terminal, onde a regra de 5 NM não se aplica, e as posições podem estar defasadas.
- **Simulação:** os voos seguem linhas retas entre aeroportos, e os alertas são gerados pelo acaso da simulação.

## ▶️ Como executar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse <http://127.0.0.1:5000>. O mapa precisa de internet para carregar os blocos do OpenStreetMap. Para rodar os testes:

```bash
pytest
```

## 🗂️ Estrutura

```
app.py                  rotas Flask e API
radar/closest_pair.py   dividir e conquistar, O(n log n)
radar/brute_force.py    força bruta, O(n²)
radar/bands.py          níveis de voo e alertas
radar/generator.py      simulação e snapshot
radar/geo.py            projeção e haversine
radar/benchmark.py      medição de desempenho
data/                   snapshot da OpenSky Network
static/, templates/     interface
tests/                  testes com pytest
```

## 🎥 Apresentação

Link do vídeo: *a adicionar*

## 👥 Dupla

| Nome | GitHub |
|---|---|
| Gustavo Costa | [@cwtshh](https://github.com/cwtshh) |
| Jesus Gabriel Carvalho Ventura | [@xGabrielCv](https://github.com/xGabrielCv) |

## 📚 Referências

- KLEINBERG, J.; TARDOS, É. *Algorithm Design*. Pearson, 2005. Seção 5.4.
- Dados de tráfego: [OpenSky Network](https://opensky-network.org).
