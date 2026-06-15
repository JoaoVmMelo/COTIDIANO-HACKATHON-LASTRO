# -*- coding: utf-8 -*-
"""Acesso às estatísticas por bairro, com intervalo de confiança.

Funde o dado REAL (cache/bairros.json, gerado por build_bairros.py) com os valores
TEMP de config.py. Se o real não tiver intervalo (ou antes de rodar os CSVs),
deriva uma faixa padrão a partir da mediana.
"""
import json
import os
import unicodedata
import config as C

CACHE = "cache/bairros.json"


def _norm(s):
    """Normaliza p/ comparar bairros ignorando acento/caixa/espaços."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.lower().strip()


def bairro_stats(bairro):
    temp = C.BAIRRO_STATS_TEMP.get(bairro, {"preco_m2_venda": 9000, "condominio_medio": 700})
    real = {}
    if os.path.exists(CACHE):
        try:
            data = json.load(open(CACHE, encoding="utf-8"))
            real = data.get(bairro)
            if real is None:                     # tenta achar ignorando acento/caixa
                alvo = _norm(bairro)
                real = next((v for k, v in data.items() if _norm(k) == alvo), {})
        except Exception:
            real = {}

    median = real.get("preco_m2_venda") or temp["preco_m2_venda"]
    condo = real.get("condominio_medio") or temp.get("condominio_medio", 700)

    return {
        "preco_m2_venda": median,
        # IC 95% da média (rigor estatístico — estreito). Padrão: ±2% se não houver real.
        "preco_m2_ci_lo": real.get("preco_m2_ci_lo", round(median * 0.98)),
        "preco_m2_ci_hi": real.get("preco_m2_ci_hi", round(median * 1.02)),
        # faixa de mercado (p10–p90 — ampla, onde caem as vendas). Padrão: ±20%.
        "preco_m2_p10": real.get("preco_m2_p10", round(median * 0.80)),
        "preco_m2_p90": real.get("preco_m2_p90", round(median * 1.20)),
        "n_transacoes": real.get("n_transacoes"),
        "condominio_medio": condo,
        "fonte_preco": "estimativa (amostra de anúncios)" if real.get("preco_m2_venda") else "estimativa base",
    }
