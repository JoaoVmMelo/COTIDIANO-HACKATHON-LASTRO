# -*- coding: utf-8 -*-
"""Agrega o dataset de ALUGUÉIS por BAIRRO -> cache/bairros.json, com INTERVALO DE CONFIANÇA.
Rode após salvar o CSV em data/ e conferir ALUGUEIS_COLMAP em config.py:  python build_bairros.py

Fonte: amostra de anúncios de aluguel de SP (rent) + encargos (total - rent = condomínio + IPTU).
Por bairro calcula, a partir do aluguel/m²:
  - aluguel_m2_medio   : mediana (valor central robusto)
  - preco_m2_venda     : preço de VENDA derivado (aluguel/m² ÷ yield) p/ o modo "comprar"
  - preco_m2_ci_lo/hi  : IC 95% da MÉDIA (média ± 1,96·erro-padrão) -> rigor estatístico
  - preco_m2_p10/p90   : faixa de mercado (onde caem 80% dos aluguéis)
  - n_transacoes       : tamanho da amostra (credibilidade)
  - condominio_medio   : mediana de (total - rent) = condomínio + IPTU reais
"""
import json
import os
import numpy as np
import pandas as pd
import config as C


def main():
    if not os.path.exists(C.ALUGUEIS_CSV):
        print("!! CSV não encontrado:", C.ALUGUEIS_CSV)
        print("   Salve o dataset de aluguéis em data/ e ajuste ALUGUEIS_CSV no config.py.")
        return

    cm = C.ALUGUEIS_COLMAP
    # usecols: lê SÓ as 4 colunas que importam -> arquivo grande (32MB+) entra leve e rápido.
    df = pd.read_csv(C.ALUGUEIS_CSV,
                     usecols=[cm["bairro"], cm["area"], cm["aluguel"], cm["total"]])
    df = df.dropna()
    df.columns = ["bairro", "area", "aluguel", "total"]

    # limpeza básica
    df = df[(df["area"] > 10) & (df["aluguel"] > 0) & (df["total"] >= df["aluguel"])]
    df["aluguel_m2"] = df["aluguel"] / df["area"]
    df["encargos"] = df["total"] - df["aluguel"]          # condomínio + IPTU reais

    # remove outliers de aluguel/m² (1% das pontas)
    lo, hi = df["aluguel_m2"].quantile([0.01, 0.99])
    df = df[(df["aluguel_m2"] >= lo) & (df["aluguel_m2"] <= hi)]

    yld = C.YIELD_ALUGUEL_MES                              # p/ derivar preço de venda
    stats = {}
    for b, g in df.groupby("bairro"):
        s = g["aluguel_m2"]
        n = len(s)
        if n < 5:
            continue  # amostra pequena demais p/ confiar
        mean, std = s.mean(), s.std(ddof=1)
        ci = 1.96 * std / np.sqrt(n)                       # IC 95% da média
        # central = MÉDIA (coerente com o IC da média -> o central sempre cai DENTRO do IC)
        stats[str(b)] = {
            "aluguel_m2_medio": round(float(mean), 2),
            "preco_m2_venda": round(float(mean) / yld),
            "preco_m2_ci_lo": round(float(mean - ci) / yld),
            "preco_m2_ci_hi": round(float(mean + ci) / yld),
            "preco_m2_p10": round(float(s.quantile(0.10)) / yld),
            "preco_m2_p90": round(float(s.quantile(0.90)) / yld),
            "n_transacoes": int(n),
            "condominio_medio": round(float(g["encargos"].median())),
        }

    os.makedirs("cache", exist_ok=True)
    with open("cache/bairros.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"OK -> cache/bairros.json ({len(stats)} bairros com IC, de {len(df)} aluguéis)")

    # confere se os bairros-demo entraram (e com qual grafia)
    print("\nBairros do demo:")
    for im in C.DEMO_IMOVEIS:
        b = im["bairro"]
        if b in stats:
            d = stats[b]
            print(f"  ✓ {b}: aluguel/m² R$ {d['aluguel_m2_medio']}  "
                  f"(n={d['n_transacoes']}, condomínio+IPTU R$ {d['condominio_medio']})")
        else:
            print(f"  ✗ {b}: NÃO encontrado — confira a grafia em DEMO_IMOVEIS/config.py")


if __name__ == "__main__":
    main()
