# -*- coding: utf-8 -*-
"""Recomendação de bairro baseada nas ESTIMATIVAS por bairro (custo + distância ao trabalho).
O ranking é DETERMINÍSTICO (não inventado) — a IA (ai.py) só narra por cima.

Para cada bairro do catálogo calcula o custo de vida estimado (cost_engine) e a
distância ao trabalho, e dá um score: cabe no orçamento + perto do trabalho."""
import config as C
import cost_engine as CE
import geo as G
from stats import bairro_stats

MAX_DIST_KM = 25.0


def _imovel_catalogo(bairro, coord, area):
    return {"id": bairro, "label": bairro, "bairro": bairro,
            "lat": coord["lat"], "lng": coord["lng"], "area_m2": area,
            "tipo": "Apartamento", "quartos": 2}


def avaliar_bairro(bairro, coord, perfil, trabalho=None):
    """trabalho: {lat,lng,nome} do trabalho do usuário (geocodificado). Se None, usa a
    Av. Paulista padrão (config.TRABALHO)."""
    imovel = _imovel_catalogo(bairro, coord, perfil["area"])
    stb = bairro_stats(bairro)

    if trabalho:                                    # trajeto REAL até o trabalho do usuário
        trj = G.trajeto(coord["lat"], coord["lng"], trabalho, perfil["modo"])
        dist = trj["distancia_km"]
        tempos = {perfil["modo"]: trj["tempo_min"]}
    else:                                           # fallback: Av. Paulista padrão
        gj = G.geo_do_imovel(imovel, perfil["modo"])
        dist = gj.get("distancia_trabalho_km") or MAX_DIST_KM
        tempos = gj.get("tempos_min", {})

    geo_info = {"distancia_trabalho_km": dist, "tempos_min": tempos}
    c = CE.montar_custo(imovel, stb, geo_info, pessoas=perfil["pessoas"],
                        modo=perfil["modo"], modo_op=perfil["modo_op"])

    total = c["total"]
    orc = perfil["orcamento"] or total
    budget_score = 1 - total / orc                 # >0 sobra no orçamento; <0 estourou
    dist_score = max(0.0, 1 - dist / MAX_DIST_KM)  # 1 = coladinho no trabalho
    score = 0.6 * budget_score + 0.4 * dist_score

    return {
        "bairro": bairro,
        "total": total, "total_lo": c["total_lo"], "total_hi": c["total_hi"],
        "valor_imovel": c["valor_imovel"],
        "dist_km": dist, "tempo_min": tempos.get(perfil["modo"]),
        "n_transacoes": c.get("n_transacoes"),
        "cabe_orcamento": total <= orc,
        "fonte": stb["fonte_preco"],
        "entorno": G.entorno_do_bairro(bairro),
        "itens": c["itens"],
        "score": round(score, 3),
    }


def recomendar(perfil, top=3):
    """perfil: {orcamento, area, pessoas, modo, modo_op, estilo?, trabalho_endereco?}.
    Geocodifica o trabalho UMA vez e ranqueia os bairros por custo + distância real a ele."""
    trabalho = None
    end = (perfil.get("trabalho_endereco") or "").strip()
    if end:
        trabalho = G.geocode(end)                  # {lat,lng,nome} ou None (cai no padrão)
    aval = [avaliar_bairro(b, coord, perfil, trabalho)
            for b, coord in C.BAIRROS_CATALOGO.items()]
    aval.sort(key=lambda x: x["score"], reverse=True)
    return aval[:top]
