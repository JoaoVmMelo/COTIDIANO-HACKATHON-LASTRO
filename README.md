# 🏙️ Cotidiano — quanto custaria sua vida nesse bairro?

Lead magnet para o mercado imobiliário (hackathon **Lastro / Laís**). A IA (a "Laís")
**estima** o custo de vida por bairro de São Paulo (moradia + condomínio + IPTU + contas +
transporte), recomenda um bairro ou descreve como seria a vida num local definido, e captura
o contato como **lead** ("isca": relatório completo do bairro).

> ⚠️ **Sobre os números:** são **estimativas de referência** a partir de uma *amostra de
> anúncios* públicos de SP — **não** são avaliação oficial. Cada valor vem com **intervalo de
> confiança de 95%** para deixar a incerteza explícita. A IA nunca inventa um número: só narra
> por cima do que o cálculo em Python produziu.

## Como rodar

```bash
pip install -r requirements.txt

# (opcional) gera as estimativas por bairro a partir da amostra de anúncios:
#   1. salve o CSV de aluguéis em data/alugueis_sp.csv
#   2. confira ALUGUEIS_COLMAP em config.py (python inspect_csv.py data/alugueis_sp.csv)
python build_bairros.py            # -> cache/bairros.json (estimativa + IC por bairro)

# (opcional) entorno real do OpenStreetMap p/ os bairros-demo:
python cache_geo.py                # -> cache/geo.json

# site (FastAPI + front HTML):
python -m uvicorn server:app --reload --port 8000   # abra http://localhost:8000
```

Sem o `build_bairros.py`, o app roda com valores-base de `config.py` (estimativa grosseira).

## Dois modos
- **Fale com a Laís** — você dá orçamento + estilo, a IA recomenda um bairro e conta como seria.
- **Já tenho um local** — questionário (trabalho/estudo/situações); calcula custo + trajetos
  (endereços geocodificados via Nominatim) e descreve seu dia a dia ali.

## Fontes de dado
- **Amostra de anúncios de aluguel de SP (Kaggle)** → estimativa de aluguel/m² e condomínio+IPTU por bairro
- **OpenStreetMap / Nominatim / OSRM** → distâncias e entorno (escola, mercado, ônibus)
- Contas/transporte/financiamento → premissas em `config.py` (ajustáveis)

## Arquivos
| Arquivo | Papel |
|---|---|
| `config.py` | catálogo de bairros, premissas de custo, mapeamento das colunas do CSV |
| `build_bairros.py` | agrega a amostra por bairro → `cache/bairros.json` (com IC) |
| `stats.py` | acesso às estimativas por bairro (amostra ou base) |
| `cost_engine.py` | fórmulas de custo (financiamento Price, IPTU, contas, transporte) |
| `recommend.py` | ranking determinístico de bairros (custo + distância) |
| `vida.py` | modo "já tenho um local": custo + trajetos + entorno |
| `geo.py` | distância/entorno/geocoding (cache ou estimativa) |
| `ai.py` | a "Laís" (Claude se houver `ANTHROPIC_API_KEY`; senão, texto-modelo) |
| `server.py` | API FastAPI + serve o front em `web/` |
| `app.py` | versão antiga em Streamlit (fallback) |
