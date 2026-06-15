# -*- coding: utf-8 -*-
"""API + servidor do Cotidiano. Reaproveita recommend.py / ai.py / cost_engine.py.
Rode:  python -m uvicorn server:app --reload --port 8000
Depois abra http://localhost:8000"""
import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

import config as C
import recommend as R
import vida as V
import ai as AI

app = FastAPI(title="Cotidiano API")


def _perfil(d):
    """Normaliza o perfil vindo do front (garante tipos)."""
    return {
        "orcamento": int(d.get("orcamento", 4500)),
        "area": int(d.get("area", 60)),
        "pessoas": int(d.get("pessoas", 2)),
        "modo": d.get("modo", "transporte"),
        "modo_op": d.get("modo_op", "alugar"),
        "estilo": d.get("estilo", ""),
        "trabalho_endereco": d.get("trabalho_endereco", ""),
    }


@app.get("/api/config")
def api_config():
    return {
        "bairros": list(C.BAIRROS_CATALOGO.keys()),
        "online": bool(os.getenv("ANTHROPIC_API_KEY")),
        "modos": {"transporte": "Transporte público", "carro": "Carro",
                  "bike": "Bicicleta", "a_pe": "A pé"},
    }


@app.post("/api/recommend")
async def api_recommend(req: Request):
    perfil = _perfil(await req.json())
    return {"perfil": perfil, "recs": R.recomendar(perfil, top=3)}


@app.post("/api/simular")
async def api_simular(req: Request):
    body = await req.json()
    perfil = _perfil(body)
    bairro = body.get("bairro") or next(iter(C.BAIRROS_CATALOGO))
    coord = C.BAIRROS_CATALOGO.get(bairro, next(iter(C.BAIRROS_CATALOGO.values())))
    return R.avaliar_bairro(bairro, coord, perfil)


@app.post("/api/vida")
async def api_vida(req: Request):
    """Modo 'já tenho um local': questionário -> custo + trajetos reais + narrativa da IA."""
    body = await req.json()
    questionario = body.get("questionario", {})
    historico = body.get("historico", [])
    dados = V.montar_vida(questionario)
    resposta = AI.narrar_vida(historico, dados)
    return {"dados": dados, "resposta": resposta, "online": bool(os.getenv("ANTHROPIC_API_KEY"))}


@app.post("/api/chat")
async def api_chat(req: Request):
    body = await req.json()
    perfil = _perfil(body.get("perfil", {}))
    recs = body.get("recs", [])
    historico = body.get("historico", [])
    resposta = AI.responder(historico, perfil, recs)
    return {"resposta": resposta, "online": bool(os.getenv("ANTHROPIC_API_KEY"))}


@app.post("/api/relatorio")
async def api_relatorio(req: Request):
    """Gera o relatório completo do bairro (entrega do lead magnet)."""
    body = await req.json()
    dados = dict(body.get("dados", {}))
    perfil = body.get("perfil", {})
    for k in ("area", "pessoas", "modo_op", "situacoes"):
        if dados.get(k) is None and perfil.get(k) is not None:
            dados[k] = perfil[k]
    return {"relatorio": AI.gerar_relatorio(dados)}


@app.post("/api/lead")
async def api_lead(req: Request):
    d = await req.json()
    os.makedirs("cache", exist_ok=True)
    nome = str(d.get("nome", "")).replace('"', "'")
    contato = str(d.get("contato", "")).replace('"', "'")
    bairro = str(d.get("bairro", "")).replace('"', "'")
    with open("cache/leads.csv", "a", encoding="utf-8") as f:
        f.write(f'"{nome}","{contato}","{bairro}"\n')
    return {"ok": True}


# serve o front-end estático (web/index.html em "/")
app.mount("/", StaticFiles(directory="web", html=True), name="web")
