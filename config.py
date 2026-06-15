# -*- coding: utf-8 -*-
"""Configuração central do Cotidiano — simulador de custo de vida por bairro (SP)."""
import os


def _load_dotenv(path=".env"):
    """Carrega variáveis de um .env local (gitignored) p/ os.environ, se o arquivo existir.
    Sem dependência externa — assim a ANTHROPIC_API_KEY pode ficar no .env, fora do código."""
    if not os.path.exists(path):
        return
    for linha in open(path, encoding="utf-8"):
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_load_dotenv()  # roda no import (config é importado antes de tudo) -> chave disponível p/ ai.py

# --- Endereço de "trabalho" usado na simulação de trajeto ---
TRABALHO = {
    "label": "Av. Paulista (trabalho)",
    "endereco": "Avenida Paulista, 1000, São Paulo",
    "lat": -23.5614,
    "lng": -46.6560,
}

# --- Imóveis-demo (a simulação usa bairro + área; coords p/ trajeto) ---
DEMO_IMOVEIS = [
    {"id": "vila_madalena", "label": "Apto Vila Madalena (caro, central)",
     "endereco": "Rua Harmonia, 200, Vila Madalena, São Paulo",
     "bairro": "Vila Madalena", "lat": -23.5547, "lng": -46.6896,
     "area_m2": 70, "tipo": "Apartamento", "quartos": 2},
    {"id": "butanta", "label": "Apto Butantã (mais barato, afastado)",
     "endereco": "Avenida Vital Brasil, 100, Butantã, São Paulo",
     "bairro": "Butantã", "lat": -23.5710, "lng": -46.7080,
     "area_m2": 70, "tipo": "Apartamento", "quartos": 2},
    {"id": "moema", "label": "Apto Moema (familiar, alto padrão)",
     "endereco": "Alameda dos Anapurus, 100, Moema, São Paulo",
     "bairro": "Moema", "lat": -23.6005, "lng": -46.6650,
     "area_m2": 70, "tipo": "Apartamento", "quartos": 2},
]

# --- Premissas de custo (ajuste à vontade) ---
ENTRADA_PCT = 0.20          # entrada no financiamento
JUROS_ANUAL = 0.105         # juros do financiamento (a.a.)
PRAZO_MESES = 360           # 30 anos
YIELD_ALUGUEL_MES = 0.004   # aluguel ~ 0,4% do valor/mês
IPTU_ANUAL_PCT = 0.006      # IPTU ~ 0,6% do valor de mercado/ano

# contas básicas (R$/mês): água + luz + gás + internet
def contas_base(area_m2, pessoas):
    base = 250 + 35 * pessoas       # luz/água/gás escalam com nº de pessoas
    internet = 110
    extra_area = 0.6 * area_m2      # imóvel maior gasta mais
    return round(base + internet + extra_area)

# transporte
TARIFA_TRANSPORTE = 4.40    # R$ por viagem (ônibus/metrô)
CUSTO_KM_CARRO = 0.90       # R$/km (combustível + desgaste)
DIAS_UTEIS_MES = 22

# velocidades p/ estimar tempo a partir da distância real (km/h)
VELOCIDADE_KMH = {"a_pe": 5, "bike": 15, "carro": 24, "transporte": 16}
ESPERA_TRANSPORTE_MIN = 6

# --- Estatística por bairro: TEMPORÁRIA até build_bairros.py rodar nos CSVs ---
# preco_m2_venda em R$/m² ; condominio_medio em R$/mês
BAIRRO_STATS_TEMP = {
    "Vila Madalena": {"preco_m2_venda": 11000, "condominio_medio": 900},
    "Butantã":       {"preco_m2_venda": 7600,  "condominio_medio": 600},
    "Moema":         {"preco_m2_venda": 11800, "condominio_medio": 1200},
    "Pinheiros":     {"preco_m2_venda": 12400, "condominio_medio": 1000},
    "Vila Mariana":  {"preco_m2_venda": 10300, "condominio_medio": 800},
}

# --- Catálogo de bairros que a IA pode recomendar (centro aprox. p/ distância) ---
# Stats reais vêm do cache/bairros.json; aqui só guardamos as coordenadas.
BAIRROS_CATALOGO = {
    "Vila Madalena": {"lat": -23.5547, "lng": -46.6896},
    "Pinheiros":     {"lat": -23.5670, "lng": -46.7020},
    "Perdizes":      {"lat": -23.5380, "lng": -46.6770},
    "Moema":         {"lat": -23.6005, "lng": -46.6650},
    "Itaim Bibi":    {"lat": -23.5850, "lng": -46.6770},
    "Vila Mariana":  {"lat": -23.5890, "lng": -46.6340},
    "Bela Vista":    {"lat": -23.5580, "lng": -46.6450},
    "Butantã":       {"lat": -23.5710, "lng": -46.7080},
    "Tatuapé":       {"lat": -23.5400, "lng": -46.5760},
    "Santana":       {"lat": -23.5020, "lng": -46.6250},
    "Brooklin":      {"lat": -23.6160, "lng": -46.6900},
    "Saúde":         {"lat": -23.6180, "lng": -46.6390},
}

# --- Dataset de ALUGUÉIS de SP (amostra de anúncios; fonte das estimativas de custo) ---
# Colunas reais do CSV: address, district, area, bedrooms, garage, type, rent, total
#   rent  = aluguel mensal real
#   total = aluguel + condomínio + IPTU  ->  (total - rent) = encargos reais
# Salve o CSV nesse caminho (ou ajuste o caminho abaixo):
ALUGUEIS_CSV = "data/alugueis_sp.csv"
ALUGUEIS_COLMAP = {
    "bairro":  "district",
    "area":    "area",
    "aluguel": "rent",
    "total":   "total",
}

# --- Dataset de VENDAS de SP (opcional: dá preço de COMPRA real) ---
# Salve o CSV em data/vendas_sp.csv e rode inspect_csv.py p/ preencher as colunas.
# Precisamos de 3: bairro/distrito, preço de venda, área (m²).
VENDAS_CSV = "data/vendas_sp.csv"
VENDAS_COLMAP = {
    "bairro": "???",   # ex.: "district" / "neighborhood" / "Bairro"
    "valor":  "???",   # preço de venda do imóvel
    "area":   "???",   # área (m²)
}
