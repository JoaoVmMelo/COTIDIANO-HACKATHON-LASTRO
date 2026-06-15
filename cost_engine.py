# -*- coding: utf-8 -*-
"""Motor de custo de vida: transforma (imóvel + bairro + perfil + geo) em custo mensal.
Trabalha com FAIXA (intervalo de confiança), não só com um valor central."""
import config as C


def valor_imovel(area_m2, preco_m2):
    return area_m2 * preco_m2


def parcela_financiamento(valor):
    """Parcela pela Tabela Price. Retorna (parcela, entrada)."""
    entrada = valor * C.ENTRADA_PCT
    financiado = valor - entrada
    i = C.JUROS_ANUAL / 12
    n = C.PRAZO_MESES
    parcela = financiado * i / (1 - (1 + i) ** (-n))
    return round(parcela), round(entrada)


def aluguel_estimado(valor):
    return round(valor * C.YIELD_ALUGUEL_MES)


def iptu_mensal(valor):
    return round(valor * C.IPTU_ANUAL_PCT / 12)


def custo_transporte(dist_km, modo):
    if dist_km is None:
        return 0
    if modo == "transporte":
        return round(2 * C.TARIFA_TRANSPORTE * C.DIAS_UTEIS_MES)
    if modo == "carro":
        return round(dist_km * 2 * C.CUSTO_KM_CARRO * C.DIAS_UTEIS_MES)
    return 0  # bike / a_pe: custo zero


def _itens_para_valor(valor, condominio, contas, transporte, modo_op):
    """Monta os itens de custo para um dado valor de imóvel."""
    itens = {
        "Condomínio": condominio,
        "Contas (água/luz/gás/internet)": contas,
        "Transporte (trabalho)": transporte,
    }
    if modo_op == "comprar":
        parcela, _ = parcela_financiamento(valor)
        itens["Parcela do financiamento"] = parcela
        itens["IPTU"] = iptu_mensal(valor)
    else:  # alugar
        itens["Aluguel"] = aluguel_estimado(valor)
    return itens


def montar_custo(imovel, bairro_stats, geo, pessoas=2, modo="transporte", modo_op="alugar"):
    """Monta o custo mensal completo COM intervalo de confiança no valor e no total."""
    area = imovel["area_m2"]

    # valor do imóvel: central + faixa (IC 95% do preço/m²)
    valor = valor_imovel(area, bairro_stats["preco_m2_venda"])
    valor_lo = valor_imovel(area, bairro_stats["preco_m2_ci_lo"])
    valor_hi = valor_imovel(area, bairro_stats["preco_m2_ci_hi"])

    condominio = bairro_stats["condominio_medio"]
    contas = C.contas_base(area, pessoas)
    dist_km = geo.get("distancia_trabalho_km") if geo else None
    transporte = custo_transporte(dist_km, modo)

    itens = _itens_para_valor(valor, condominio, contas, transporte, modo_op)
    total = sum(itens.values())
    # total também vira faixa (recalcula os itens que dependem do valor)
    total_lo = sum(_itens_para_valor(valor_lo, condominio, contas, transporte, modo_op).values())
    total_hi = sum(_itens_para_valor(valor_hi, condominio, contas, transporte, modo_op).values())

    entrada = parcela_financiamento(valor)[1] if modo_op == "comprar" else None

    return {
        "itens": itens,
        "total": total,
        "total_lo": total_lo,
        "total_hi": total_hi,
        "valor_imovel": round(valor),
        "valor_lo": round(valor_lo),
        "valor_hi": round(valor_hi),
        "n_transacoes": bairro_stats.get("n_transacoes"),
        "entrada": entrada,
        "dist_trabalho_km": dist_km,
        "modo_op": modo_op,
    }
