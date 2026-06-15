# -*- coding: utf-8 -*-
"""Mostra colunas/estatísticas dos CSVs p/ você preencher os COLMAP em config.py.
Uso:  python inspect_csv.py data/transacoes_sp_2023.csv data/anuncios_sp.csv"""
import sys
import pandas as pd


def inspect(path):
    print("=" * 64)
    print(path)
    df = pd.read_csv(path)
    print("linhas x colunas:", df.shape)
    print("colunas:", df.columns.tolist())
    print("\n-- head --")
    print(df.head(3).to_string())
    print("\n-- describe --")
    print(df.describe(include="all").to_string()[:1800])


if __name__ == "__main__":
    alvos = sys.argv[1:] or ["data/transacoes_sp_2023.csv", "data/anuncios_sp.csv"]
    for p in alvos:
        try:
            inspect(p)
        except Exception as e:
            print("erro em", p, ":", e)
