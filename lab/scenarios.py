"""Cenários de entrada reproduzíveis (vetores e pontos), todos determinísticos por seed."""
import math
import random

ARRAY_SCENARIOS = {
    "aleatorio": "Inteiros uniformes em [−99, 99]",
    "ordenado": "Já em ordem crescente",
    "invertido": "Em ordem decrescente",
    "quase_ordenado": "Ordenado com ~5% de trocas aleatórias",
    "duplicados": "Só valores de 0 a 4 (muitas repetições)",
    "iguais": "Todos os elementos iguais",
    "concentrado": "Normal arredondada com média 0 e desvio 5",
    "todos_negativos": "Inteiros em [−99, −1]",
}

POINT_SCENARIOS = {
    "aleatorio": "Pontos uniformes num quadrado de 5.000 km",
    "concentrado": "Cinco aglomerados gaussianos (desvio 40 km)",
    "mesmo_eixo": "Todos os pontos com o mesmo x",
    "grade": "Grade regular: muitos pares empatados",
    "duplicados": "Coordenadas inteiras pequenas, com pontos repetidos",
}


def make_array(scenario, n, seed):
    rng = random.Random(seed)
    if scenario not in ARRAY_SCENARIOS:
        raise ValueError(f"cenário desconhecido: {scenario}")
    if scenario == "duplicados":
        return [rng.randint(0, 4) for _ in range(n)]
    if scenario == "iguais":
        return [7] * n
    if scenario == "concentrado":
        return [round(rng.gauss(0, 5)) for _ in range(n)]
    if scenario == "todos_negativos":
        return [rng.randint(-99, -1) for _ in range(n)]
    values = [rng.randint(-99, 99) for _ in range(n)]
    if scenario == "ordenado":
        values.sort()
    elif scenario == "invertido":
        values.sort(reverse=True)
    elif scenario == "quase_ordenado":
        values.sort()
        for _ in range(n // 20 + 1):
            if n > 1:
                i, j = rng.randrange(n), rng.randrange(n)
                values[i], values[j] = values[j], values[i]
    return values


def make_points(scenario, n, seed):
    rng = random.Random(seed)
    if scenario not in POINT_SCENARIOS:
        raise ValueError(f"cenário desconhecido: {scenario}")
    if scenario == "concentrado":
        centers = [(rng.uniform(0, 5000), rng.uniform(0, 5000)) for _ in range(5)]
        points = []
        for _ in range(n):
            cx, cy = rng.choice(centers)
            points.append((rng.gauss(cx, 40), rng.gauss(cy, 40)))
        return points
    if scenario == "mesmo_eixo":
        return [(100.0, rng.uniform(0, 5000)) for _ in range(n)]
    if scenario == "grade":
        side = math.ceil(math.sqrt(n))
        return [(float(i % side) * 10, float(i // side) * 10) for i in range(n)]
    if scenario == "duplicados":
        span = max(2, int(math.sqrt(n)))
        return [(float(rng.randint(0, span)), float(rng.randint(0, span))) for _ in range(n)]
    return [(rng.uniform(0, 5000), rng.uniform(0, 5000)) for _ in range(n)]


# Casos didáticos do visualizador do par mais próximo.
VISUAL_CASES = {
    "dois_pontos": ("Dois pontos", "O menor caso possível: um único caso-base."),
    "cruzamento_mediana": ("Par cruzando a mediana", "O par mais próximo tem um ponto de cada lado da divisão."),
    "faixa_central": ("Par achado só na faixa", "Cada metade tem pares distantes; só a combinação acha o par."),
    "empates": ("Empates", "Grade regular: vários pares com a mesma distância mínima."),
    "duplicados": ("Pontos duplicados", "Dois pontos idênticos: distância zero."),
    "mesmo_eixo": ("Mesmo eixo x", "Todos os pontos alinhados na vertical: a divisão usa a posição na ordem, não só o x."),
    "nuvem": ("Nuvem aleatória", "Pontos uniformes gerados pela seed."),
}


def make_visual_case(case, n, seed):
    rng = random.Random(seed)
    if case == "dois_pontos":
        return [(10.0, 20.0), (60.0, 50.0)]
    if case == "cruzamento_mediana":
        return [(0, 0), (8, 90), (20, 40), (35, 80), (49, 50), (51, 52), (65, 10), (80, 70), (95, 30), (100, 95)]
    if case == "faixa_central":
        left = [(float(x), float(y)) for x, y in ((0, 0), (0, 40), (25, 20), (10, 70), (30, 95))]
        right = [(float(x), float(y)) for x, y in ((70, 0), (75, 45), (100, 20), (90, 70), (100, 100))]
        return left + right + [(48.0, 55.0), (52.0, 57.0)]
    if case == "empates":
        return [(float(x * 20), float(y * 20)) for x in range(4) for y in range(4)]
    if case == "duplicados":
        points = [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(max(n, 4) - 1)]
        return points + [points[len(points) // 2]]
    if case == "mesmo_eixo":
        return [(50.0, float(y)) for y in sorted(rng.sample(range(0, 200), max(n, 4)))]
    if case == "nuvem":
        return [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(max(n, 2))]
    raise ValueError(f"caso desconhecido: {case}")
