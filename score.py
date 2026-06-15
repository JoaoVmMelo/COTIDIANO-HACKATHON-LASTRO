# -*- coding: utf-8 -*-
"""Score de Vida: transforma os dados do cenário (custo + trajetos + entorno + situações)
numa NOTA 0-100 de compatibilidade com o perfil da pessoa, com breakdown por dimensão.
Determinístico — a IA só narra o veredito por cima."""


def brl(v):
    return "R$ " + f"{round(v):,}".replace(",", ".")


def _clamp(x, lo=0, hi=100):
    return max(lo, min(hi, round(x)))


def compute_score(dados, orcamento=None):
    cnt = dados.get("entorno_count", {})
    perto = dados.get("perto", {})
    trajetos = dados.get("trajetos", [])
    sit = set(dados.get("situacoes", []))
    custo = dados.get("total")
    dims = []

    # --- Orçamento (só se informado) ---
    if orcamento and custo:
        ratio = custo / orcamento
        nota = _clamp((1.1 - ratio) / (1.1 - 0.7) * 100)
        det = (f"cabe no orçamento (sobra {brl(orcamento - custo)}/mês)" if custo <= orcamento
               else f"estoura {brl(custo - orcamento)}/mês do orçamento")
        dims.append({"chave": "orcamento", "label": "Orçamento", "nota": nota, "peso": 28, "detalhe": det})

    # --- Trajeto (só se há trabalho/estudo) ---
    if trajetos:
        tmax = max(t["tempo_min"] for t in trajetos)
        nota = _clamp((60 - tmax) / (60 - 15) * 100)
        dims.append({"chave": "trajeto", "label": "Trajetos", "nota": nota, "peso": 26,
                     "detalhe": f"~{tmax} min até o {trajetos[0]['rotulo'].lower()}"})

    # --- Conveniência: comércio essencial a pé ---
    essenciais = sum(cnt.get(k, 0) for k in ("padaria", "cafe", "mercado", "farmacia"))
    dims.append({"chave": "conveniencia", "label": "Comércio a pé", "nota": _clamp(essenciais * 9),
                 "peso": 16, "detalhe": f"{essenciais} padarias/cafés/mercados/farmácias por perto"})

    # --- Lazer & gastronomia (pesa mais p/ quem curte bar/noite) ---
    lazer = cnt.get("restaurante", 0) + cnt.get("cafe", 0) + cnt.get("parque", 0) + cnt.get("academia", 0)
    dims.append({"chave": "lazer", "label": "Lazer & gastronomia", "nota": _clamp(lazer * 3),
                 "peso": 16 if "bar" in sit else 10,
                 "detalhe": f"{cnt.get('restaurante', 0)} restaurantes, {cnt.get('cafe', 0)} cafés, "
                            f"{cnt.get('parque', 0)} parques"})

    # --- Pet-friendly (só se tem pet) ---
    if "pet" in sit:
        nota, partes = 0, []
        if cnt.get("petshop", 0):
            nota += 35; partes.append("petshop")
        if cnt.get("veterinario", 0):
            nota += 20; partes.append("veterinário")
        pq = perto.get("parque")
        if pq and pq["walk_min"] <= 8:
            nota += 45; partes.append(f"parque a {pq['walk_min']} min")
        elif cnt.get("parque", 0):
            nota += 25; partes.append("parque por perto")
        dims.append({"chave": "pet", "label": "Pet-friendly", "nota": _clamp(nota), "peso": 18,
                     "detalhe": ", ".join(partes) or "pouca estrutura pet por perto"})

    # --- Escolas (só se tem filhos) ---
    if "filhos" in sit:
        esc = cnt.get("escola", 0)
        e = perto.get("escola")
        det = f"{esc} escolas" + (f", a mais perto a {e['walk_min']} min" if e else "")
        dims.append({"chave": "familia", "label": "Escolas", "nota": _clamp(esc * 22),
                     "peso": 18, "detalhe": det})

    # --- Mobilidade (metrô) — pesa mais p/ quem vai de transporte público ---
    mt = perto.get("metro")
    if mt and mt["walk_min"] <= 10:
        nota, det = 100, f"metrô a {mt['walk_min']} min a pé"
    elif mt and mt["walk_min"] <= 16:
        nota, det = 70, f"metrô a {mt['walk_min']} min a pé"
    elif mt:
        nota, det = 40, f"metrô a {mt['walk_min']} min"
    else:
        nota, det = 20, "sem metrô no raio curto"
    peso = 14 if any(t["modo"] == "transporte" for t in trajetos) else 7
    dims.append({"chave": "transporte", "label": "Mobilidade (metrô)", "nota": nota,
                 "peso": peso, "detalhe": det})

    soma = sum(d["peso"] for d in dims)
    total = round(sum(d["nota"] * d["peso"] for d in dims) / soma) if soma else 0
    band = ("Combina muito com você" if total >= 80 else
            "Boa opção pra você" if total >= 62 else
            "Dá pra viver, com ressalvas" if total >= 45 else
            "Provavelmente não é o ideal")
    dims.sort(key=lambda d: -d["peso"])
    return {"total": total, "band": band, "dimensoes": dims}
