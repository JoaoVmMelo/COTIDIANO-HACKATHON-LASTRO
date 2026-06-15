# -*- coding: utf-8 -*-
"""FATIA VERTICAL: imprime o custo de vida (com intervalo de confiança) no terminal.
Roda sem dependências externas:  python run_demo.py"""
import config as C
import cost_engine as CE
import geo as G
from stats import bairro_stats


def brl(v):
    return f"R$ {v:,.0f}".replace(",", ".")


def main():
    for im in C.DEMO_IMOVEIS:
        st = bairro_stats(im["bairro"])
        gj = G.geo_do_imovel(im)
        c = CE.montar_custo(im, st, gj, pessoas=2, modo="transporte", modo_op="alugar")
        n = c["n_transacoes"]
        print("=" * 60)
        print(f"{im['label']}  |  {im['bairro']}  |  {im['area_m2']} m²")
        print(f"Valor do imóvel: {brl(c['valor_imovel'])}  "
              f"(IC 95%: {brl(c['valor_lo'])} – {brl(c['valor_hi'])}"
              f"{f', n={n} transações' if n else ''})")
        print(f"Preço/m²: {brl(st['preco_m2_venda'])}  [{st['fonte_preco']}]")
        print(f"Distância ao trabalho: {gj.get('distancia_trabalho_km')} km  "
              f"[{gj.get('fonte', '')}]")
        if gj.get("entorno"):
            cats = sorted({e["categoria"] for e in gj["entorno"]})
            print(f"Entorno real: {len(gj['entorno'])} pontos ({', '.join(cats)})")
        print("-- Custo mensal (alugando) --")
        for k, v in c["itens"].items():
            print(f"   {k:<34} {brl(v)}")
        print(f"   {'TOTAL / mês':<34} {brl(c['total'])}  "
              f"(entre {brl(c['total_lo'])} e {brl(c['total_hi'])})")
    print("=" * 60)


if __name__ == "__main__":
    main()
