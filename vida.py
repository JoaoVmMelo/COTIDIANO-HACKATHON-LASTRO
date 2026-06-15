# -*- coding: utf-8 -*-
"""Modo 'Já tenho um local': o bairro é dado, e calculamos COMO SERIA A VIDA ali —
custo estimado + trajetos (trabalho/estudo geocodificados) + entorno + situações.
A narrativa é feita pela IA (ai.narrar_vida); aqui só os números (estimativas)."""
import config as C
import cost_engine as CE
import geo as G
import score as SC
from stats import bairro_stats

DIAS_SEMANA_MES = 4.33
_DEMO_ID = {im["bairro"]: im["id"] for im in C.DEMO_IMOVEIS}


def _perto_por_categoria(lat, lng, entorno):
    """Para cada categoria, acha o local mais próximo da casa, com preferência:
    1º com nome E horário, 2º com nome, 3º qualquer. Retorna nome + horário + distância + min a pé."""
    slots = {}
    for e in entorno:
        d_km = G.haversine_km(lat, lng, e["lat"], e["lng"])
        cand = {"_d": d_km, "nome": e.get("nome", ""), "horario": e.get("horario", ""),
                "dist_m": int(round(d_km * 1000)),
                "walk_min": max(1, round(d_km / 5 * 60))}  # 5 km/h a pé
        s = slots.setdefault(e["categoria"], {"any": None, "named": None, "horario": None})

        def melhor(slot):  # mantém o mais próximo dentro do tier
            return slot is None or d_km < slot["_d"]

        if melhor(s["any"]):
            s["any"] = cand
        if cand["nome"] and melhor(s["named"]):
            s["named"] = cand
        if cand["nome"] and cand["horario"] and melhor(s["horario"]):
            s["horario"] = cand
    out = {}
    for cat, s in slots.items():
        b = s["horario"] or s["named"] or s["any"]
        out[cat] = {"nome": b["nome"], "horario": b["horario"],
                    "dist_m": b["dist_m"], "walk_min": b["walk_min"]}
    return out


def _transporte_mes(trj, dias_semana):
    if not trj:
        return 0
    dias_mes = round(dias_semana * DIAS_SEMANA_MES)
    modo, dist = trj["modo"], trj["distancia_km"]
    if modo == "transporte":
        return round(2 * C.TARIFA_TRANSPORTE * dias_mes)
    if modo == "carro":
        return round(dist * 2 * C.CUSTO_KM_CARRO * dias_mes)
    return 0  # bike / a pé: custo zero


def montar_vida(q):
    """q: questionário do front. Retorna dados estruturados (sem texto)."""
    local = q.get("local") or next(iter(C.BAIRROS_CATALOGO))
    coord = C.BAIRROS_CATALOGO.get(local) or next(iter(C.BAIRROS_CATALOGO.values()))
    area = int(q.get("area", 60))
    pessoas = int(q.get("pessoas", 2))
    modo_op = q.get("modo_op", "alugar")
    stb = bairro_stats(local)

    valor = CE.valor_imovel(area, stb["preco_m2_venda"])
    itens = {
        "Condomínio": stb["condominio_medio"],
        "Contas (água/luz/gás/internet)": C.contas_base(area, pessoas),
    }
    if modo_op == "comprar":
        itens["Parcela do financiamento"] = CE.parcela_financiamento(valor)[0]
        itens["IPTU"] = CE.iptu_mensal(valor)
    else:
        itens["Aluguel"] = CE.aluguel_estimado(valor)

    # ---- trajetos reais (trabalho / estudo) ----
    # (flag_no_questionário, prefixo_dos_campos, rótulo)
    DESTINOS = [("trabalha", "trabalho", "Trabalho"), ("estuda", "estudo", "Estudo")]
    trajetos, transporte, destinos = [], 0, []
    for flag, pref, rotulo in DESTINOS:
        if not q.get(flag):
            continue
        dest = G.resolver_local(q.get(f"{pref}_endereco"), q.get(f"{pref}_bairro"))
        trj = G.trajeto(coord["lat"], coord["lng"], dest, q.get(f"{pref}_modo", "transporte"))
        if trj and dest:
            trj["rotulo"] = rotulo
            trajetos.append(trj)
            destinos.append({"rotulo": rotulo, "lat": dest["lat"], "lng": dest["lng"],
                             "nome": dest["nome"]})
            transporte += _transporte_mes(trj, int(q.get(f"{pref}_dias", 5)))
    if transporte:
        itens["Transporte (trajetos)"] = transporte

    total = sum(itens.values())

    # base de locais reais do bairro (empresas, padarias, escolas, petshops, restaurantes...)
    entorno = G.entorno_do_bairro(local)
    entorno_cats = sorted({e["categoria"] for e in entorno})
    perto = _perto_por_categoria(coord["lat"], coord["lng"], entorno)
    entorno_count = {}
    for e in entorno:
        entorno_count[e["categoria"]] = entorno_count.get(e["categoria"], 0) + 1

    # lazer/comércio perto do TRABALHO (consulta ao vivo em volta do endereço do trabalho)
    trab = next((d for d in destinos if d["rotulo"] == "Trabalho"), None)
    entorno_trabalho = G.entorno_em(trab["lat"], trab["lng"]) if trab else []
    perto_trabalho = (_perto_por_categoria(trab["lat"], trab["lng"], entorno_trabalho)
                      if trab and entorno_trabalho else {})

    out = {
        "local": local, "area": area, "pessoas": pessoas, "modo_op": modo_op,
        "itens": itens, "total": total, "valor_imovel": round(valor),
        "aluguel_m2": round(stb["preco_m2_venda"] * C.YIELD_ALUGUEL_MES, 2),
        "n_transacoes": stb.get("n_transacoes"), "fonte_preco": stb["fonte_preco"],
        "trajetos": trajetos, "entorno_cats": entorno_cats,
        "perto": perto, "perto_trabalho": perto_trabalho, "entorno_count": entorno_count,
        "situacoes": q.get("situacoes", []),
        "mapa": {
            "home": {"lat": coord["lat"], "lng": coord["lng"], "nome": local},
            "destinos": destinos,
            "entorno": [{"lat": e["lat"], "lng": e["lng"], "categoria": e["categoria"],
                         "nome": e.get("nome", ""), "horario": e.get("horario", "")}
                        for e in (entorno + entorno_trabalho)],
        },
    }
    orcamento = int(q.get("orcamento") or 0) or None
    out["score"] = SC.compute_score(out, orcamento)
    return out
