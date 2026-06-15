# -*- coding: utf-8 -*-
"""Cotidiano — simulador de custo de vida por bairro (SP), com intervalo de confiança,
chat com IA (a "Laís") + isca de lead.  Rode:  python -m streamlit run app.py"""
import os
import streamlit as st
import pandas as pd
import config as C
import cost_engine as CE
import geo as G
import recommend as R
import ai as AI
from stats import bairro_stats

st.set_page_config(page_title="Cotidiano — custo de vida por bairro", layout="wide")


def brl(v):
    return f"R$ {v:,.0f}".replace(",", ".")


MODOS = {"transporte": "Transporte público", "carro": "Carro",
         "bike": "Bicicleta", "a_pe": "A pé"}

st.title("🏙️ Cotidiano — quanto custaria sua vida nesse bairro?")
st.caption("Estimativa de custo a partir de uma amostra de anúncios de SP + distâncias (OpenStreetMap). "
           "Valores com intervalo de confiança de 95%.")

tab_chat, tab_sim = st.tabs(["💬 Fale com a Laís (IA)", "🧮 Simulador"])

# ============================ ABA: CHAT COM A IA ============================
with tab_chat:
    st.subheader("💬 A Laís acha seu bairro ideal e conta como seria sua vida lá")

    with st.expander("📝 Sua situação", expanded=not st.session_state.get("chat")):
        c1, c2 = st.columns(2)
        with c1:
            orc = st.number_input("Orçamento mensal (moradia + contas + transporte)",
                                  1500, 30000, 4500, 250)
            area_c = st.slider("Área desejada (m²)", 25, 200, 60, 5, key="chat_area")
            pessoas_c = st.slider("Pessoas na casa", 1, 6, 2, key="chat_pessoas")
        with c2:
            modo_c = st.selectbox("Como vai ao trabalho", list(MODOS),
                                  format_func=lambda m: MODOS[m], key="chat_modo")
            op_c = st.radio("Comprar ou alugar?", ["alugar", "comprar"],
                            horizontal=True, key="chat_op")
            estilo = st.text_input("O que você curte? (bares, parques, família, sossego, "
                                   "vida noturna...)", key="chat_estilo")
        if st.button("🔮 Recomendar meu bairro", type="primary"):
            perfil = {"orcamento": orc, "area": area_c, "pessoas": pessoas_c,
                      "modo": modo_c, "modo_op": op_c, "estilo": estilo}
            recs = R.recomendar(perfil)
            situacao = (f"Minha situação: orçamento {brl(orc)}/mês, {pessoas_c} pessoa(s), "
                        f"quero {area_c} m², vou ao trabalho de {MODOS[modo_c]}, "
                        f"prefiro {op_c}. Estilo: {estilo or 'sem preferência específica'}. "
                        f"Qual bairro combina comigo e como seria minha vida lá?")
            hist = [{"role": "user", "content": situacao}]
            resposta = AI.responder(hist, perfil, recs)
            st.session_state["perfil"] = perfil
            st.session_state["recs"] = recs
            st.session_state["chat"] = hist + [{"role": "assistant", "content": resposta}]
            st.rerun()

    if not os.getenv("ANTHROPIC_API_KEY"):
        st.caption("ℹ️ Rodando em modo offline (texto-modelo). Defina `ANTHROPIC_API_KEY` "
                   "para a conversa completa com o Claude.")

    # histórico do chat
    for m in st.session_state.get("chat", []):
        st.chat_message(m["role"]).markdown(m["content"])

    # mapa + custo da recomendação atual
    recs = st.session_state.get("recs")
    if recs:
        top = recs[0]
        st.divider()
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("🏆 Recomendado", top["bairro"])
        cc2.metric("Custo mensal", brl(top["total"]),
                   help=f"IC 95%: {brl(top['total_lo'])} – {brl(top['total_hi'])}")
        cc3.metric("Trabalho", f"{top['dist_km']} km",
                   f"{top['tempo_min']} min" if top.get("tempo_min") else None)
        st.caption("Outras opções avaliadas: "
                   + " · ".join(f"{r['bairro']} ({brl(r['total'])})" for r in recs[1:]))

        prompt = st.chat_input("Pergunte algo (ex: e um bairro mais barato? tem parque por perto?)")
        if prompt:
            st.session_state["chat"].append({"role": "user", "content": prompt})
            resposta = AI.responder(st.session_state["chat"],
                                    st.session_state["perfil"], recs)
            st.session_state["chat"].append({"role": "assistant", "content": resposta})
            st.rerun()

        # captura de lead direto do chat
        with st.form("lead_chat"):
            st.write(f"📄 **Quer o relatório completo de {top['bairro']}?**")
            nome = st.text_input("Nome", key="nome_chat")
            contato = st.text_input("WhatsApp ou e-mail", key="contato_chat")
            if st.form_submit_button("Quero o relatório") and nome and contato:
                os.makedirs("cache", exist_ok=True)
                with open("cache/leads.csv", "a", encoding="utf-8") as f:
                    f.write(f'"{nome}","{contato}","{top["bairro"]}"\n')
                st.success(f"✅ Recebido, {nome.split()[0]}! Em produção, cai direto no CRM / na Laís.")

# ============================ ABA: SIMULADOR ============================
with tab_sim:
    col_in, col_out = st.columns([1, 2])

    with col_in:
        st.subheader("Seu cenário")
        labels = [im["label"] for im in C.DEMO_IMOVEIS]
        idx = st.selectbox("Imóvel / bairro", range(len(labels)),
                           format_func=lambda i: labels[i])
        imovel = dict(C.DEMO_IMOVEIS[idx])
        imovel["area_m2"] = st.slider("Área (m²)", 25, 200, imovel["area_m2"], 5)
        pessoas = st.slider("Pessoas na casa", 1, 6, 2)
        modo = st.selectbox("Como vai ao trabalho", list(MODOS),
                            format_func=lambda m: MODOS[m])
        modo_op = st.radio("Comprar ou alugar?", ["alugar", "comprar"], horizontal=True)

    stb = bairro_stats(imovel["bairro"])
    gj = G.geo_do_imovel(imovel, modo)
    c = CE.montar_custo(imovel, stb, gj, pessoas=pessoas, modo=modo, modo_op=modo_op)

    with col_out:
        st.subheader(f"📍 {imovel['bairro']}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Custo mensal total", brl(c["total"]),
                  help=f"Intervalo de confiança 95%: {brl(c['total_lo'])} – {brl(c['total_hi'])}")
        m2.metric("Valor do imóvel", brl(c["valor_imovel"]),
                  help=f"IC 95%: {brl(c['valor_lo'])} – {brl(c['valor_hi'])}")
        tempo = gj.get("tempos_min", {}).get(modo)
        m3.metric("Trajeto ao trabalho", f"{gj.get('distancia_trabalho_km', '?')} km",
                  f"{tempo} min" if tempo else None)

        n = c.get("n_transacoes")
        st.info(
            f"💰 **Custo mensal: {brl(c['total'])}**  "
            f"(intervalo de confiança 95%: **{brl(c['total_lo'])} – {brl(c['total_hi'])}**)\n\n"
            f"Valor do imóvel: {brl(c['valor_imovel'])} "
            f"(faixa {brl(c['valor_lo'])} – {brl(c['valor_hi'])})"
            + (f" · estimativa de **amostra de {n} anúncios**" if n
               else " · _estimativa base (rode build_bairros.py p/ usar a amostra)_")
        )

        df = pd.DataFrame({"item": list(c["itens"].keys()), "R$/mês": list(c["itens"].values())})
        st.bar_chart(df.set_index("item"))
        st.dataframe(df, hide_index=True, use_container_width=True)

        pts = [{"lat": imovel["lat"], "lon": imovel["lng"]},
               {"lat": C.TRABALHO["lat"], "lon": C.TRABALHO["lng"]}]
        for e in (gj.get("entorno") or [])[:30]:
            pts.append({"lat": e["lat"], "lon": e["lng"]})
        st.map(pd.DataFrame(pts))

        if gj.get("entorno"):
            st.caption("Entorno real (OpenStreetMap): "
                       + ", ".join(sorted({e["categoria"] for e in gj["entorno"]})))
        else:
            st.caption("ℹ️ Rode `python cache_geo.py` para puxar o entorno real do OpenStreetMap.")
