# -*- coding: utf-8 -*-
"""Camada de IA: a 'Laís' conversa, recomenda UM bairro (com base nas ESTIMATIVAS
do recommend.py) e descreve como seria a vida da pessoa lá.

- Se a env ANTHROPIC_API_KEY estiver setada -> usa a API da Anthropic (Claude).
- Senão -> cai num texto-modelo construído das estimativas (o demo NUNCA quebra).
Configurável: COTIDIANO_MODEL (default claude-sonnet-4-6; pode usar claude-opus-4-8)."""
import os
import json
import config as C
import geo as G
import recommend as R

MODEL = os.getenv("COTIDIANO_MODEL", "claude-sonnet-4-6")
MODOS_VALIDOS = ["transporte", "carro", "bike", "a_pe"]


# ==================== Ferramentas (tool use) ====================
def _tools_def():
    """Ferramentas que a Laís pode chamar p/ RECALCULAR durante a conversa."""
    return [
        {
            "name": "recomendar_bairros",
            "description": "Recalcula o ranking de bairros quando o usuário muda orçamento, área, "
                           "nº de pessoas, transporte, alugar/comprar ou estilo. Use sempre que ele "
                           "disser 'e se...' sobre esses parâmetros. Retorna os 3 melhores com custo "
                           "estimado, distância e se cabe no orçamento.",
            "input_schema": {"type": "object", "properties": {
                "orcamento": {"type": "number", "description": "orçamento mensal em R$"},
                "area": {"type": "number"}, "pessoas": {"type": "integer"},
                "modo": {"type": "string", "enum": MODOS_VALIDOS},
                "modo_op": {"type": "string", "enum": ["alugar", "comprar"]},
                "estilo": {"type": "string"},
                "trabalho_endereco": {"type": "string",
                                      "description": "endereço do trabalho (ranqueia por distância real a ele)"}}},
        },
        {
            "name": "simular_bairro",
            "description": "Calcula o custo de vida estimado de UM bairro específico (quando o usuário "
                           "pergunta sobre um bairro pelo nome). Retorna a quebra de custo e a distância.",
            "input_schema": {"type": "object", "properties": {
                "bairro": {"type": "string"},
                "area": {"type": "number"}, "pessoas": {"type": "integer"},
                "modo": {"type": "string", "enum": MODOS_VALIDOS},
                "modo_op": {"type": "string", "enum": ["alugar", "comprar"]}},
                "required": ["bairro"]},
        },
        {
            "name": "calcular_trajeto",
            "description": "Distância e tempo estimados entre o local e um destino, num modo de "
                           "transporte. Use quando perguntarem 'e se eu fosse de bike/carro/a pé?' "
                           "ou derem um novo endereço de trabalho/estudo.",
            "input_schema": {"type": "object", "properties": {
                "local": {"type": "string", "description": "bairro de origem"},
                "destino_endereco": {"type": "string"},
                "destino_bairro": {"type": "string"},
                "modo": {"type": "string", "enum": MODOS_VALIDOS}},
                "required": ["modo"]},
        },
    ]


def _perfil_merge(ctx, args):
    p = dict(ctx)
    for k, v in (args or {}).items():
        if v is not None:
            p[k] = v
    return p


def _dispatch(name, args, ctx):
    """Executa a ferramenta chamada pela IA. Retorna dict JSON-serializável."""
    try:
        if name == "recomendar_bairros":
            recs = R.recomendar(_perfil_merge(ctx, args), top=3)
            return {"bairros": [{
                "bairro": r["bairro"], "custo_mes": r["total"],
                "faixa": [r["total_lo"], r["total_hi"]], "dist_km": r["dist_km"],
                "tempo_min": r["tempo_min"], "cabe_orcamento": r["cabe_orcamento"],
                "n_anuncios": r.get("n_transacoes")} for r in recs]}

        if name == "simular_bairro":
            bairro = (args or {}).get("bairro", "")
            coord = C.BAIRROS_CATALOGO.get(bairro)
            if not coord:
                return {"erro": f"'{bairro}' fora do catálogo.",
                        "bairros_validos": list(C.BAIRROS_CATALOGO)}
            r = R.avaliar_bairro(bairro, coord, _perfil_merge(ctx, args))
            return {"bairro": bairro, "custo_mes": r["total"], "faixa": [r["total_lo"], r["total_hi"]],
                    "valor_imovel": r["valor_imovel"], "dist_km": r["dist_km"],
                    "tempo_min": r["tempo_min"], "itens": r["itens"], "n_anuncios": r.get("n_transacoes")}

        if name == "calcular_trajeto":
            local = (args or {}).get("local") or ctx.get("local")
            coord = C.BAIRROS_CATALOGO.get(local)
            if not coord:
                return {"erro": f"local '{local}' desconhecido."}
            dest = G.resolver_local((args or {}).get("destino_endereco"),
                                    (args or {}).get("destino_bairro"))
            if not dest:
                return {"erro": "destino não informado ou não encontrado."}
            t = G.trajeto(coord["lat"], coord["lng"], dest, (args or {}).get("modo", "transporte"))
            return t or {"erro": "não foi possível calcular o trajeto."}

        return {"erro": f"ferramenta desconhecida: {name}"}
    except Exception as e:
        return {"erro": f"falha ao executar {name}: {e}"}


def _anthropic_agentic(historico, system, ctx):
    """Loop de tool use: a IA chama ferramentas, executamos, devolvemos, até a resposta final."""
    from anthropic import Anthropic
    client = Anthropic()
    messages = [{"role": m["role"], "content": m["content"]} for m in historico]
    tools = _tools_def()
    resp = None
    for _ in range(5):  # trava anti-loop
        resp = client.messages.create(model=MODEL, max_tokens=900, system=system,
                                       tools=tools, messages=messages)
        if resp.stop_reason != "tool_use":
            break
        messages.append({"role": "assistant", "content": resp.content})
        resultados = []
        for b in resp.content:
            if getattr(b, "type", "") == "tool_use":
                saida = _dispatch(b.name, b.input or {}, ctx)
                resultados.append({"type": "tool_result", "tool_use_id": b.id,
                                   "content": json.dumps(saida, ensure_ascii=False)})
        messages.append({"role": "user", "content": resultados})
    texto = "".join(b.text for b in (resp.content if resp else []) if getattr(b, "type", "") == "text")
    return texto or "Desculpe, não consegui calcular isso agora. Pode reformular?"


def brl(v):
    return f"R$ {v:,.0f}".replace(",", ".")


def _ctx_recomendacao(recs):
    linhas = []
    for i, r in enumerate(recs, 1):
        cabe = "cabe no orçamento" if r["cabe_orcamento"] else "ACIMA do orçamento"
        ent = ", ".join(sorted({e["categoria"] for e in (r.get("entorno") or [])})) or "—"
        n = f", amostra de {r['n_transacoes']} anúncios" if r.get("n_transacoes") else ""
        linhas.append(
            f"{i}. {r['bairro']}: custo ~{brl(r['total'])}/mês "
            f"(IC95% {brl(r['total_lo'])}–{brl(r['total_hi'])}{n}), {cabe}; "
            f"{r['dist_km']} km do trabalho"
            + (f" (~{r['tempo_min']} min)" if r.get("tempo_min") else "")
            + f"; entorno: {ent}."
        )
    return "\n".join(linhas)


def _system(perfil, recs):
    return (
        "Você é a Laís, consultora imobiliária por IA da Lastro. Fala português do Brasil, "
        "tom caloroso, direto e prático. Sua tarefa: recomendar UM bairro de São Paulo para a "
        "pessoa e descrever, de forma concreta, como seria a vida dela ali — rotina do dia a dia, "
        "deslocamento ao trabalho, custo mensal e a vibe do bairro.\n\n"
        "REGRAS (siga à risca):\n"
        "- Use SOMENTE números que vieram do cálculo. NUNCA invente preços, distâncias ou custos.\n"
        "- VOCÊ TEM FERRAMENTAS para recalcular: recomendar_bairros, simular_bairro, calcular_trajeto. "
        "Sempre que o usuário mudar um parâmetro ou perguntar 'e se...' (outro orçamento, bairro, "
        "transporte, área), CHAME a ferramenta e responda com os números novos — não estime de cabeça.\n"
        "- Recomende o bairro nº 1 da lista (melhor encaixe); pode citar 1 alternativa da lista.\n"
        "- Sempre cite o custo mensal e deixe claro que é uma ESTIMATIVA a partir de uma amostra "
        "de anúncios (não um valor oficial); use o intervalo de confiança para mostrar a incerteza.\n"
        "- VÁ DIRETO AO PONTO: comece pela resposta (bairro + custo). Sem introdução, sem rodeio. "
        "Depois, no MÁXIMO 1 frase sobre como é a vida lá.\n"
        "- Texto corrido, no máximo **negrito**. NÃO use títulos com #, listas, '---' nem emojis.\n"
        "- MUITO conciso: no máximo ~70 palavras. Termine com 1 linha curta convidando a deixar "
        "nome e contato para o relatório completo.\n\n"
        "PERFIL DA PESSOA:\n"
        f"- Orçamento: {brl(perfil['orcamento'])}/mês (moradia + contas + transporte)\n"
        f"- Trabalha em: {perfil.get('trabalho_endereco') or 'Av. Paulista (padrão)'}\n"
        f"- Vai ao trabalho de: {perfil['modo']}\n"
        f"- Área desejada: {perfil['area']} m², {perfil['pessoas']} pessoa(s)\n"
        f"- Operação: {perfil['modo_op']}\n"
        f"- Estilo de vida: {perfil.get('estilo') or 'não informado'}\n\n"
        f"BAIRROS AVALIADOS (estimativas já calculadas — use estes números):\n{_ctx_recomendacao(recs)}"
    )


def responder(historico, perfil, recs):
    """historico: lista [{'role':'user'/'assistant','content':str}] começando por 'user'."""
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            ctx = {"orcamento": perfil.get("orcamento", 0), "area": perfil["area"],
                   "pessoas": perfil["pessoas"], "modo": perfil.get("modo", "transporte"),
                   "modo_op": perfil.get("modo_op", "alugar"), "estilo": perfil.get("estilo", ""),
                   "trabalho_endereco": perfil.get("trabalho_endereco", ""),
                   "local": recs[0]["bairro"] if recs else None}
            return _anthropic_agentic(historico, _system(perfil, recs), ctx)
        except Exception as e:
            return _fallback(perfil, recs, erro=str(e))
    return _fallback(perfil, recs)


SITUACOES_LABEL = {
    "filhos": "tem filho(s)", "pet": "tem pet", "academia": "faz academia",
    "carro": "tem carro", "bar": "curte bar/vida noturna", "home_office": "faz home office",
}


def _ctx_vida(d):
    linhas = [
        f"Local definido: {d['local']} ({d['area']} m², {d['pessoas']} pessoa(s), {d['modo_op']}).",
        f"Custo mensal total: {brl(d['total'])}. Itens: "
        + "; ".join(f"{k} {brl(v)}" for k, v in d["itens"].items()) + ".",
        f"Aluguel/m² do bairro: {brl(d['aluguel_m2'])}"
        + (f" (amostra de {d['n_transacoes']} anúncios)" if d.get("n_transacoes") else " (estimado)") + ".",
    ]
    for t in d.get("trajetos", []):
        linhas.append(f"Trajeto {t['rotulo']}: {t['distancia_km']} km até {t['destino']} "
                      f"(~{t['tempo_min']} min de {t['modo']}).")
    ROT = {"padaria": "Padaria", "cafe": "Café", "escola": "Escola", "petshop": "Petshop",
           "veterinario": "Veterinário", "restaurante": "Restaurante", "mercado": "Mercado",
           "farmacia": "Farmácia", "parque": "Parque/praça", "empresa": "Empresa",
           "academia": "Academia", "metro": "Metrô", "hospital": "Hospital", "bar": "Bar/boteco"}

    def _lista(titulo, mapa, sufixo):
        linhas.append(titulo)
        for cat, p in mapa.items():
            nome = p["nome"] or "(sem nome)"
            hor = f" — horário: {p['horario']}" if p.get("horario") else ""
            linhas.append(f"  - {ROT.get(cat, cat)}: {nome} — {p['dist_m']} m {sufixo} — {p['walk_min']} min a pé{hor}")

    if d.get("perto"):
        _lista("Locais REAIS mais próximos de CASA (use ESTES nomes/distâncias/horários, não invente):",
               d["perto"], "de casa")
    if d.get("perto_trabalho"):
        _lista("Locais REAIS perto do TRABALHO (p/ almoço, café, academia, happy hour perto do escritório):",
               d["perto_trabalho"], "do trabalho")
    if d.get("entorno_count"):
        linhas.append("Quantidade por categoria (raio curto): "
                      + ", ".join(f"{k}={v}" for k, v in d["entorno_count"].items()) + ".")
    sc = d.get("score")
    if sc:
        linhas.append(f"SCORE DE COMPATIBILIDADE: {sc['total']}/100 — {sc['band']}. Por dimensão: "
                      + "; ".join(f"{x['label']} {x['nota']}/100 ({x['detalhe']})" for x in sc["dimensoes"]) + ".")
    if d.get("situacoes"):
        linhas.append("Situações da pessoa: "
                      + ", ".join(SITUACOES_LABEL.get(s, s) for s in d["situacoes"]) + ".")
    return "\n".join(linhas)


def _system_vida(d):
    return (
        "Você é a Laís, consultora imobiliária por IA da Lastro (português do Brasil, tom caloroso e "
        "entusiasmado). A pessoa JÁ escolheu o bairro — não recomende outro. Na PRIMEIRA resposta, "
        "desenhe COMO SERIA A ROTINA dela ali, seguindo EXATAMENTE este formato:\n\n"
        "1) Saudação com o nome da pessoa (se houver) + 1 frase sobre o espírito do bairro, "
        "JÁ mencionando o Score de compatibilidade (ex: 'esse bairro tira X/100 pra você').\n"
        "2) A frase: 'Deixa eu desenhar como seria a sua rotina:'\n"
        "3) Blocos de rotina, cada um numa linha começando com o emoji indicado, em 1-2 frases, "
        "citando UM lugar REAL da lista 'Locais mais próximos' com a distância e os minutos a pé:\n"
        "   ☕ Seu café da manhã: a padaria ou o café mais próximo (se houver horário, cite, ex: 'abre 6h').\n"
        "   💼 Seu trajeto para o trabalho: use o trajeto fornecido (km e minutos no modo informado). "
        "Se houver 'locais perto do trabalho', emende 1 dica concreta (ex: 'pro almoço, o Restaurante X "
        "fica a 200 m do escritório').\n"
        "   🎒 Escola das crianças: INCLUA SÓ se a pessoa tem filhos; use a escola mais próxima.\n"
        "   🐶 O passeio do seu cachorro: INCLUA SÓ se a pessoa tem pet; cite o petshop/veterinário "
        "e a praça/parque mais próximos.\n"
        "   🍽️ Jantar e lazer: cite 1 restaurante real próximo pelo nome.\n\n"
        "REGRAS (siga à risca):\n"
        "- Use SOMENTE os nomes de lugares e as distâncias/minutos FORNECIDOS. NUNCA invente um nome "
        "de estabelecimento, uma distância ou um valor. Se faltar lugar de uma categoria, omita o bloco.\n"
        "- Custo e distâncias são ESTIMATIVAS (amostra de anúncios + mapa público), não oficiais.\n"
        "- Pode dar um toque de entusiasmo ('dá adeus ao trânsito'), mas sem inventar dados. Sem títulos com #.\n"
        "- VOCÊ TEM FERRAMENTAS (calcular_trajeto, simular_bairro, recomendar_bairros): se o usuário "
        "perguntar 'e se eu fosse de bike/carro?' ou mudar algo, CHAME a ferramenta — não chute.\n"
        "- Esse formato completo vale para a PRIMEIRA resposta (a rotina). Nas perguntas seguintes, "
        "responda DIRETO e curto.\n\n"
        f"DADOS DESTE CENÁRIO (estimativas):\n{_ctx_vida(d)}"
    )


def narrar_vida(historico, dados):
    """Narra como seria a vida no local definido. Claude se houver key; senão, texto-modelo."""
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            modo = dados["trajetos"][0]["modo"] if dados.get("trajetos") else "transporte"
            ctx = {"orcamento": 0, "area": dados["area"], "pessoas": dados["pessoas"],
                   "modo": modo, "modo_op": dados["modo_op"], "estilo": "", "local": dados["local"]}
            return _anthropic_agentic(historico, _system_vida(dados), ctx)
        except Exception as e:
            return _fallback_vida(dados, erro=str(e))
    return _fallback_vida(dados)


def _fallback_vida(d, erro=None):
    trj = d.get("trajetos", [])
    linha_trj = ""
    if trj:
        partes = [f"{t['rotulo'].lower()} a ~{t['distancia_km']} km ({t['tempo_min']} min de {t['modo']})"
                  for t in trj]
        linha_trj = "Seu deslocamento: " + "; ".join(partes) + ". "
    ent = ", ".join(d.get("entorno_cats", []))
    txt = (
        f"Morar em **{d['local']}** custaria cerca de **{brl(d['total'])}/mês** "
        f"({d['area']} m², {d['pessoas']} pessoa(s), {d['modo_op']}) — estimativa a partir de uma amostra de anúncios.\n\n"
        f"**Como seria sua vida lá:** " + linha_trj
        + (f"No entorno você encontra {ent} a pé. " if ent else "")
        + "A rotina seria desenhada em torno desses deslocamentos e do orçamento acima.\n\n"
        f"Quer o **relatório completo de {d['local']}** (escolas, comércio, tendência de preço)? "
        f"Deixa seu nome e contato que eu te mando."
    )
    if erro:
        txt += "\n\n_(modo offline — configure ANTHROPIC_API_KEY p/ a narrativa completa)_"
    return txt


# ==================== Relatório completo (a entrega do lead magnet) ====================
def _normaliza_dados(d):
    """Aceita o shape do recommend (rec) OU do vida (montar_vida) e unifica."""
    trajetos = d.get("trajetos")
    if not trajetos and d.get("dist_km") is not None:
        trajetos = [{"rotulo": "Trabalho", "destino": "trabalho",
                     "distancia_km": d.get("dist_km"), "tempo_min": d.get("tempo_min"),
                     "modo": d.get("modo", "transporte")}]
    entorno_cats = d.get("entorno_cats")
    if entorno_cats is None:
        entorno_cats = sorted({e["categoria"] for e in (d.get("entorno") or [])})
    return {
        "local": d.get("local") or d.get("bairro") or "—",
        "total": d.get("total"), "total_lo": d.get("total_lo"), "total_hi": d.get("total_hi"),
        "itens": d.get("itens", {}), "valor_imovel": d.get("valor_imovel"),
        "n_anuncios": d.get("n_transacoes") or d.get("n_anuncios"),
        "fonte": d.get("fonte_preco") or d.get("fonte") or "estimativa",
        "trajetos": trajetos or [], "entorno_cats": entorno_cats,
        "situacoes": d.get("situacoes", []),
        "area": d.get("area"), "pessoas": d.get("pessoas"), "modo_op": d.get("modo_op"),
    }


def _ctx_relatorio(d):
    L = [f"Bairro: {d['local']} ({d.get('area') or '?'} m², {d.get('pessoas') or '?'} pessoa(s), "
         f"{d.get('modo_op') or '?'})."]
    if d.get("total") is not None:
        faixa = f" (faixa {brl(d['total_lo'])}–{brl(d['total_hi'])})" if d.get("total_lo") else ""
        L.append(f"Custo mensal estimado: {brl(d['total'])}{faixa}.")
    if d.get("itens"):
        L.append("Itens: " + "; ".join(f"{k} {brl(v)}" for k, v in d["itens"].items()) + ".")
    if d.get("valor_imovel"):
        L.append(f"Valor do imóvel (estimado): {brl(d['valor_imovel'])}.")
    if d.get("n_anuncios"):
        L.append(f"Amostra: {d['n_anuncios']} anúncios ({d['fonte']}).")
    for t in d["trajetos"]:
        L.append(f"Trajeto {t['rotulo']}: {t['distancia_km']} km, ~{t['tempo_min']} min de {t['modo']}.")
    if d["entorno_cats"]:
        L.append("Entorno: " + ", ".join(d["entorno_cats"]) + ".")
    if d["situacoes"]:
        L.append("Situações da pessoa: " + ", ".join(SITUACOES_LABEL.get(s, s) for s in d["situacoes"]) + ".")
    return "\n".join(L)


def _parse_json(txt):
    if not txt:
        return None
    i, j = txt.find("{"), txt.rfind("}")
    if i == -1 or j == -1:
        return None
    try:
        obj = json.loads(txt[i:j + 1])
        return obj if isinstance(obj, dict) and ("resumo" in obj or "veredito" in obj) else None
    except Exception:
        return None


def gerar_relatorio(dados):
    """Gera as seções qualitativas do relatório (IA com fallback). Números vêm do Python."""
    d = _normaliza_dados(dados)
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from anthropic import Anthropic
            system = (
                "Você é a Laís, da Lastro. Gere um RELATÓRIO de bairro para a pessoa, em português do "
                "Brasil, tom consultivo e honesto. Use SOMENTE os números fornecidos e trate-os como "
                "ESTIMATIVAS de uma amostra de anúncios (não valores oficiais). "
                "Responda APENAS com um JSON válido, sem texto fora e sem crases, com as chaves: "
                '{"resumo": "2-3 frases", "dia_na_vida": "1 parágrafo curto e concreto", '
                '"pros": ["item", "item", "item"], "contras": ["item", "item"], '
                '"pra_quem": "1 frase", "veredito": "1-2 frases"}. Sem emojis.\n\n'
                "DADOS:\n" + _ctx_relatorio(d)
            )
            client = Anthropic()
            resp = client.messages.create(model=MODEL, max_tokens=900, system=system,
                                          messages=[{"role": "user", "content": "Gere o relatório em JSON."}])
            txt = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            parsed = _parse_json(txt)
            if parsed:
                return parsed
        except Exception:
            pass
    return _relatorio_fallback(d)


def _relatorio_fallback(d):
    poucos = (d.get("n_anuncios") or 99) < 30
    pros = ["Custo dentro do estimado para a região"]
    if d["trajetos"]:
        t = d["trajetos"][0]
        pros.append(f"{t['rotulo']} a {t['distancia_km']} km (~{t['tempo_min']} min)")
    if d["entorno_cats"]:
        pros.append("Comércio e serviços por perto: " + ", ".join(d["entorno_cats"][:4]))
    return {
        "resumo": f"{d['local']} sai por cerca de {brl(d['total'])}/mês — estimativa a partir de uma "
                  f"amostra de anúncios, então use como referência.",
        "dia_na_vida": "Sua rotina giraria em torno do custo e dos trajetos listados ao lado.",
        "pros": pros,
        "contras": ["Estimativa de amostra pequena — confirme com anúncios reais" if poucos
                    else "Valores variam por rua, andar e estado do imóvel"],
        "pra_quem": "Quem busca equilíbrio entre custo e localização.",
        "veredito": f"Boa opção se {brl(d['total'])}/mês couber confortavelmente no seu orçamento.",
    }


def _anthropic(historico, system):
    from anthropic import Anthropic
    client = Anthropic()
    resp = client.messages.create(
        model=MODEL, max_tokens=700, system=system, messages=historico,
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def _fallback(perfil, recs, erro=None):
    r = recs[0]
    ent = ", ".join(sorted({e["categoria"] for e in (r.get("entorno") or [])}))
    transp = r["itens"].get("Transporte (trabalho)", 0)
    tempo = f" (~{r['tempo_min']} min de {perfil['modo']})" if r.get("tempo_min") else ""
    txt = (
        f"Pelo seu perfil, o bairro que mais combina é **{r['bairro']}**.\n\n"
        f"O custo de vida ali fica em torno de **{brl(r['total'])}/mês** "
        f"(estimativa, faixa {brl(r['total_lo'])}–{brl(r['total_hi'])}), "
        f"{'dentro do' if r['cabe_orcamento'] else 'um pouco acima do'} seu orçamento de "
        f"{brl(perfil['orcamento'])}. O trabalho fica a ~{r['dist_km']} km{tempo}.\n\n"
        f"**Como seria sua vida lá:** você acordaria num bairro "
        f"{'mais tranquilo' if r['dist_km'] > 8 else 'central e movimentado'}, sairia pro "
        f"trabalho gastando ~{brl(transp)}/mês em transporte"
        + (f", com padaria, mercado e comércio logo ali ({ent})" if ent else "")
        + f". No fim do mês, moradia + contas + transporte fecham em ~{brl(r['total'])}.\n\n"
        f"Quer o **relatório completo de {r['bairro']}** (escolas, comércio, tendência de "
        f"preço)? Deixa seu nome e contato que eu te mando."
    )
    if erro:
        txt += "\n\n_(modo offline — configure ANTHROPIC_API_KEY p/ a conversa completa com a IA)_"
    return txt
