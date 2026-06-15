// ===================== Cotidiano — front-end =====================
const $ = (s) => document.querySelector(s);
const brl = (v) => "R$ " + Math.round(v).toLocaleString("pt-BR");

// -------- Ícones Lucide (currentColor herda o tema) --------
const ICONS = {
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  bot: '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>',
  pin: '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
  wallet: '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
  route: '<polygon points="3 11 22 2 13 21 11 13 3 11"/>',
};
function icon(name, size = 16) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ""}</svg>`;
}

// -------- Tema (data-theme no <html>, persistido) --------
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  localStorage.setItem("cotidiano-theme", t);
  $("#theme-icon").innerHTML = icon(t === "dark" ? "sun" : "moon", 18);
  $("#theme-label").textContent = t === "dark" ? "Tema claro" : "Tema escuro";
}
applyTheme(localStorage.getItem("cotidiano-theme") || "light");
$("#theme-toggle").addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme");
  applyTheme(cur === "dark" ? "light" : "dark");
});

// -------- Navegação (scroll suave + estado ativo) --------
document.querySelectorAll("[data-scroll], [data-nav]").forEach((el) => {
  el.addEventListener("click", (e) => {
    const sel = el.getAttribute("data-scroll") || el.getAttribute("href");
    if (sel && sel.startsWith("#")) {
      e.preventDefault();
      $(sel)?.scrollIntoView({ behavior: "smooth" });
      document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
      document.querySelector(`.nav-item[href="${sel}"]`)?.classList.add("active");
    }
  });
});

// ===================== Estado =====================
let STATE = { perfil: null, recs: [], historico: [], online: false };

// ===================== Init: carrega config =====================
async function init() {
  const cfg = await fetch("/api/config").then((r) => r.json());
  STATE.online = cfg.online;
  // popula selects de modo
  const opts = Object.entries(cfg.modos).map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
  $("#f-modo").innerHTML = opts;
  $("#s-modo").innerHTML = opts;
  // popula bairros do simulador
  const bairroOpts = cfg.bairros.map((b) => `<option value="${b}">${b}</option>`).join("");
  $("#s-bairro").innerHTML = bairroOpts;
  // modo "já tenho um local"
  $("#v-local").innerHTML = bairroOpts;
  $("#v-trabalho-bairro").innerHTML = bairroOpts;
  $("#v-estudo-bairro").innerHTML = bairroOpts;
  $("#v-trabalho-modo").innerHTML = opts;
  $("#v-estudo-modo").innerHTML = opts;
  if (!cfg.online) {
    addMsg("assistant", "<em>Modo offline: respostas em texto-modelo. Defina ANTHROPIC_API_KEY no servidor pra conversa completa com o Claude.</em>");
  }
  simular(); // primeira simulação
}

// ===================== Chat helpers =====================
function mdToHtml(t) {
  return t
    .replace(/^#{1,6}\s*(.+)$/gm, "<strong>$1</strong>") // títulos -> negrito
    .replace(/^\s*-{3,}\s*$/gm, "")                       // linhas '---' -> some
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/\n{2,}/g, "<br><br>")
    .replace(/\n/g, "<br>");
}
function addMsg(role, html) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const avatar = role === "assistant"
    ? `<span class="avatar">${icon("bot", 16)} Laís</span>` : "";
  wrap.innerHTML = avatar + mdToHtml(html);
  $("#chat-messages").appendChild(wrap);
  wrap.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// bolha "digitando..." (a Laís pode estar chamando ferramentas — leva alguns segundos)
function thinking(sel) {
  const el = document.createElement("div");
  el.className = "msg assistant";
  el.innerHTML = `<span class="avatar">${icon("bot", 16)} Laís</span><span class="dots"><i></i><i></i><i></i></span>`;
  $(sel).appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return el;
}

// ===================== Recomendar =====================
function lerPerfil() {
  return {
    orcamento: +$("#f-orcamento").value,
    area: +$("#f-area").value,
    pessoas: +$("#f-pessoas").value,
    modo: $("#f-modo").value,
    modo_op: $("#f-op").value,
    estilo: $("#f-estilo").value,
    trabalho_endereco: $("#f-trabalho").value,
  };
}

function renderRecCards(recs) {
  $("#rec-cards").innerHTML = recs.map((r, i) => `
    <div class="rec-card ${i === 0 ? "top" : ""}">
      <div class="rec-rank">${i + 1}</div>
      <div class="rec-info">
        <div class="rec-name">${r.bairro}
          <span class="pill ${r.cabe_orcamento ? "ok" : "over"}">${r.cabe_orcamento ? "cabe no orçamento" : "acima"}</span>
        </div>
        <div class="rec-meta">${icon("route", 13)} ${r.dist_km} km${r.tempo_min ? " · ~" + r.tempo_min + " min" : ""} · ${r.fonte}</div>
      </div>
      <div class="rec-price">${brl(r.total)}<div class="rec-meta">/mês</div></div>
    </div>`).join("");
}

async function recomendar() {
  const btn = $("#btn-recomendar");
  btn.disabled = true;
  const perfil = lerPerfil();
  const data = await fetch("/api/recommend", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(perfil),
  }).then((r) => r.json());

  STATE.perfil = data.perfil;
  STATE.recs = data.recs;
  renderRecCards(data.recs);

  const situacao = `Minha situação: orçamento ${brl(perfil.orcamento)}/mês, ${perfil.pessoas} pessoa(s), quero ${perfil.area} m², trabalho em ${perfil.trabalho_endereco || "Av. Paulista"}, vou de ${perfil.modo}, prefiro ${perfil.modo_op}. Estilo: ${perfil.estilo || "sem preferência"}. Qual bairro combina comigo e como seria minha vida lá?`;
  STATE.historico = [{ role: "user", content: situacao }];

  const tEl = thinking("#chat-messages");
  const resp = await fetch("/api/chat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ perfil: STATE.perfil, recs: STATE.recs, historico: STATE.historico }),
  }).then((r) => r.json());
  tEl.remove();

  STATE.historico.push({ role: "assistant", content: resp.resposta });
  addMsg("assistant", resp.resposta);

  // habilita chat + lead
  $("#chat-input").disabled = false;
  $("#chat-send").disabled = false;
  $("#lead-bairro").textContent = data.recs[0].bairro;
  $("#lead-box").classList.remove("hidden");
  btn.disabled = false;
}

// ===================== Chat livre =====================
async function enviarMensagem() {
  const inp = $("#chat-input");
  const texto = inp.value.trim();
  if (!texto) return;
  inp.value = "";
  addMsg("user", texto);
  STATE.historico.push({ role: "user", content: texto });

  const tEl = thinking("#chat-messages");
  const resp = await fetch("/api/chat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ perfil: STATE.perfil, recs: STATE.recs, historico: STATE.historico }),
  }).then((r) => r.json());
  tEl.remove();

  STATE.historico.push({ role: "assistant", content: resp.resposta });
  addMsg("assistant", resp.resposta);
}

// ===================== Relatório completo =====================
function renderRelatorio(d, rel) {
  const local = d.local || d.bairro || "—";
  const itens = d.itens || {};
  const trajetos = d.trajetos || (d.dist_km != null
    ? [{ rotulo: "Trabalho", distancia_km: d.dist_km, tempo_min: d.tempo_min, modo: d.modo || "transporte" }] : []);
  const ent = d.entorno_cats || (d.entorno ? [...new Set(d.entorno.map((e) => e.categoria))] : []);
  $("#rel-titulo").textContent = `Relatório completo · ${local}`;
  $("#rel-body").innerHTML = `
    <div class="report-grid">
      <div class="report-main">
        <p class="report-resumo">${mdToHtml(rel.resumo || "")}</p>
        <h4>Um dia na sua vida</h4>
        <p>${mdToHtml(rel.dia_na_vida || "")}</p>
        <div class="report-cols">
          <div><h4>Prós</h4><ul class="pros">${(rel.pros || []).map((p) => `<li>${p}</li>`).join("")}</ul></div>
          <div><h4>Pontos de atenção</h4><ul class="contras">${(rel.contras || []).map((p) => `<li>${p}</li>`).join("")}</ul></div>
        </div>
        <h4>Pra quem é</h4><p>${mdToHtml(rel.pra_quem || "")}</p>
        <div class="report-veredito">${mdToHtml(rel.veredito || "")}</div>
      </div>
      <aside class="report-side">
        <div class="report-cost">
          <div class="rc-total">${brl(d.total)}<small>por mês (estimado)</small></div>
          ${d.total_lo ? `<div class="rc-ic">IC 95%: ${brl(d.total_lo)} – ${brl(d.total_hi)}</div>` : ""}
          <table>${Object.entries(itens).map(([k, v]) => `<tr><td>${k}</td><td>${brl(v)}</td></tr>`).join("")}</table>
        </div>
        ${trajetos.length ? `<div class="report-traj"><h4>Trajetos</h4>${trajetos.map((t) =>
          `<div class="rt-row"><span>${t.rotulo}</span><b>${t.distancia_km} km · ${t.tempo_min} min</b></div>`).join("")}</div>` : ""}
        ${ent.length ? `<div class="report-ent"><h4>Entorno</h4><div>${ent.map((c) =>
          `<span class="chip-static">${c}</span>`).join("")}</div></div>` : ""}
      </aside>
    </div>`;
  $("#relatorio").classList.remove("hidden");
  $("#relatorio").scrollIntoView({ behavior: "smooth" });
}

async function gerarRelatorio(dados, perfil, okEl, primeiroNome) {
  okEl.innerHTML = `${icon("bot", 14)} Gerando seu relatório, ${primeiroNome}... (alguns segundos)`;
  okEl.classList.remove("hidden");
  const r = await fetch("/api/relatorio", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dados, perfil }),
  }).then((res) => res.json());
  renderRelatorio(dados, r.relatorio);
  okEl.innerHTML = `${icon("bot", 14)} Pronto, ${primeiroNome}! Seu relatório completo está logo abaixo.`;
}

// ===================== Lead =====================
async function enviarLead() {
  const nome = $("#lead-nome").value.trim();
  const contato = $("#lead-contato").value.trim();
  if (!nome || !contato) return;
  await fetch("/api/lead", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome, contato, bairro: STATE.recs[0]?.bairro || "" }),
  });
  $("#lead-nome").value = "";
  $("#lead-contato").value = "";
  await gerarRelatorio(STATE.recs[0], STATE.perfil, $("#lead-ok"), nome.split(" ")[0]);
}

// ===================== Simulador =====================
async function simular() {
  const body = {
    bairro: $("#s-bairro").value,
    area: +$("#s-area").value,
    pessoas: +$("#s-pessoas").value,
    modo: $("#s-modo").value,
    modo_op: $("#s-op").value,
    orcamento: 999999,
  };
  const r = await fetch("/api/simular", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((res) => res.json());

  $("#s-metrics").innerHTML = `
    <div class="metric"><div class="metric-label">${icon("wallet", 14)} Custo mensal</div>
      <div class="metric-value">${brl(r.total)}</div>
      <div class="metric-sub">IC 95%: ${brl(r.total_lo)} – ${brl(r.total_hi)}</div></div>
    <div class="metric"><div class="metric-label">${icon("pin", 14)} Valor do imóvel</div>
      <div class="metric-value">${brl(r.valor_imovel)}</div>
      <div class="metric-sub">${r.n_transacoes ? r.n_transacoes + " anúncios na amostra" : "estimativa"}</div></div>
    <div class="metric"><div class="metric-label">${icon("route", 14)} Trabalho</div>
      <div class="metric-value">${r.dist_km} km</div>
      <div class="metric-sub">${r.tempo_min ? "~" + r.tempo_min + " min" : ""}</div></div>`;

  $("#s-itens").innerHTML = Object.entries(r.itens).map(([k, v]) => `
    <div class="rec-card"><div class="rec-info"><div class="rec-name" style="font-size:14px">${k}</div></div>
      <div class="rec-price" style="font-size:15px">${brl(v)}</div></div>`).join("");
}

// ===================== Modo "Já tenho um local" =====================
let VIDA = { questionario: null, dados: null, historico: [] };

function addMsgEl(containerSel, role, html) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const avatar = role === "assistant" ? `<span class="avatar">${icon("bot", 16)} Laís</span>` : "";
  wrap.innerHTML = avatar + mdToHtml(html);
  $(containerSel).appendChild(wrap);
  wrap.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function lerQuestionario() {
  const situacoes = [...document.querySelectorAll("#v-situacoes input:checked")].map((c) => c.value);
  return {
    local: $("#v-local").value,
    area: +$("#v-area").value,
    pessoas: +$("#v-pessoas").value,
    modo_op: $("#v-op").value,
    orcamento: +$("#v-orcamento").value || 0,
    trabalha: $("#v-trabalha").checked,
    trabalho_endereco: $("#v-trabalho-end").value,
    trabalho_bairro: $("#v-trabalho-bairro").value,
    trabalho_modo: $("#v-trabalho-modo").value,
    trabalho_dias: +$("#v-trabalho-dias").value,
    estuda: $("#v-estuda").checked,
    estudo_endereco: $("#v-estudo-end").value,
    estudo_bairro: $("#v-estudo-bairro").value,
    estudo_modo: $("#v-estudo-modo").value,
    situacoes,
  };
}

function renderVida(d) {
  $("#v-metrics").innerHTML = `
    <div class="metric"><div class="metric-label">${icon("wallet", 14)} Custo aqui</div>
      <div class="metric-value">${brl(d.total)}</div><div class="metric-sub">/mês · ${d.fonte_preco}</div></div>
    <div class="metric"><div class="metric-label">${icon("pin", 14)} Aluguel/m²</div>
      <div class="metric-value">${brl(d.aluguel_m2)}</div>
      <div class="metric-sub">${d.n_transacoes ? d.n_transacoes + " anúncios na amostra" : "estimativa"}</div></div>
    <div class="metric"><div class="metric-label">${icon("route", 14)} Trajetos</div>
      <div class="metric-value">${d.trajetos.length}</div><div class="metric-sub">${d.local}</div></div>`;

  $("#v-trajetos").innerHTML = d.trajetos.map((t) => `
    <div class="trajeto-row">
      <span class="t-ico">${icon("route", 18)}</span>
      <div class="t-main">
        <div class="t-label">${t.rotulo} · ${t.modo}</div>
        <div class="t-dest">${t.destino} · ${t.rota_real ? "rota real (ruas)" : "linha reta (estim.)"}</div>
      </div>
      <div class="t-val">${t.distancia_km} km<small>~${t.tempo_min} min</small></div>
    </div>`).join("");
}

// Score de Vida (nota + barras)
function renderScore(sc) {
  if (!sc) { $("#v-score").innerHTML = ""; return; }
  const cor = sc.total >= 80 ? "#1aa97a" : sc.total >= 62 ? "#5ba32a" : sc.total >= 45 ? "#E0801F" : "#D14545";
  const bars = sc.dimensoes.map((d) => `
    <div class="score-dim">
      <div class="score-dim-top"><span>${d.label}</span><b>${d.nota}</b></div>
      <div class="score-bar"><i style="width:${d.nota}%;background:${cor}"></i></div>
      <div class="score-det">${d.detalhe}</div>
    </div>`).join("");
  $("#v-score").innerHTML = `
    <div class="score-card">
      <div class="score-gauge">
        <div class="score-ring" style="--c:${cor};--p:${sc.total}">
          <div class="score-ring-inner"><div class="score-num">${sc.total}<small>/100</small></div></div>
        </div>
        <div class="score-band" style="color:${cor}">${sc.band}</div>
      </div>
      <div class="score-dims">${bars}</div>
    </div>`;
}

// mapa Leaflet (casa + trajetos + entorno)
const CAT_COR = {
  empresa: "#4DCFFC", padaria: "#FF8A3D", escola: "#2D6BE0", petshop: "#28E4A8",
  veterinario: "#0FA36B", restaurante: "#FF5C7A", mercado: "#B569F0",
  farmacia: "#14B8C6", parque: "#7BC043", cafe: "#8B5E3C", academia: "#F2C14E",
  metro: "#3A4A66", hospital: "#D64545", bar: "#E0529C",
};
const CAT_LABEL = {
  empresa: "Empresas", padaria: "Padarias", escola: "Escolas", petshop: "Petshops",
  veterinario: "Veterinários", restaurante: "Restaurantes", mercado: "Mercados",
  farmacia: "Farmácias", parque: "Parques", cafe: "Cafés", academia: "Academias",
  metro: "Metrô", hospital: "Hospitais", bar: "Bares",
};
let vmap = null, vmarkers = null;

function renderMapa(m) {
  if (!m || !m.home) return;
  $("#v-map").classList.remove("hidden");
  $("#v-map-legend").classList.remove("hidden");
  if (!vmap) {
    vmap = L.map("v-map", { scrollWheelZoom: false });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap", maxZoom: 19,
    }).addTo(vmap);
    vmarkers = L.layerGroup().addTo(vmap);
  }
  vmarkers.clearLayers();
  const pts = [];
  const h = m.home;
  L.circleMarker([h.lat, h.lng], { radius: 11, color: "#5b3a99", fillColor: "#9664FA", fillOpacity: .95, weight: 2 })
    .bindPopup(`<b>Casa</b><br>${h.nome}`).addTo(vmarkers);
  pts.push([h.lat, h.lng]);
  (m.destinos || []).forEach((d) => {
    L.circleMarker([d.lat, d.lng], { radius: 8, color: "#9e1f1f", fillColor: "#E23D3D", fillOpacity: .95, weight: 2 })
      .bindPopup(`<b>${d.rotulo}</b><br>${d.nome}`).addTo(vmarkers);
    L.polyline([[h.lat, h.lng], [d.lat, d.lng]], { color: "#6845AD", weight: 3, dashArray: "6 7", opacity: .7 }).addTo(vmarkers);
    pts.push([d.lat, d.lng]);
  });
  (m.entorno || []).forEach((e) => {
    const cor = CAT_COR[e.categoria] || "#28E4A8";
    const hor = e.horario ? `<br><span style="color:#888">⏰ ${e.horario}</span>` : "";
    L.circleMarker([e.lat, e.lng], { radius: 5, color: cor, fillColor: cor, fillOpacity: .9, weight: 1 })
      .bindPopup(`<b>${e.nome || CAT_LABEL[e.categoria] || e.categoria}</b><br>${CAT_LABEL[e.categoria] || e.categoria}${hor}`)
      .addTo(vmarkers);
    pts.push([e.lat, e.lng]);
  });
  // legenda dinâmica (só as categorias presentes)
  const cats = [...new Set((m.entorno || []).map((e) => e.categoria))];
  $("#v-map-legend").innerHTML =
    `<span><i style="background:#9664FA"></i> Casa</span>` +
    (m.destinos && m.destinos.length ? `<span><i style="background:#E23D3D"></i> Trabalho/Estudo</span>` : "") +
    cats.map((c) => `<span><i style="background:${CAT_COR[c] || "#28E4A8"}"></i> ${CAT_LABEL[c] || c}</span>`).join("");
  if (pts.length) vmap.fitBounds(pts, { padding: [30, 30], maxZoom: 15 });
  setTimeout(() => vmap.invalidateSize(), 120);
}

async function verVida() {
  const btn = $("#btn-vida");
  btn.disabled = true;
  btn.querySelector("svg")?.remove();
  const q = lerQuestionario();
  VIDA.questionario = q;
  VIDA.historico = [{ role: "user", content: "Como seria minha vida nesse local?" }];

  $("#v-messages").innerHTML = "";
  const tEl = thinking("#v-messages");
  const r = await fetch("/api/vida", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ questionario: q, historico: VIDA.historico }),
  }).then((res) => res.json());
  tEl.remove();

  VIDA.dados = r.dados;
  renderVida(r.dados);
  renderScore(r.dados.score);
  renderMapa(r.dados.mapa);
  VIDA.historico.push({ role: "assistant", content: r.resposta });
  addMsgEl("#v-messages", "assistant", r.resposta);

  $("#v-input").disabled = false;
  $("#v-send").disabled = false;
  $("#v-lead-bairro").textContent = r.dados.local;
  $("#v-lead-box").classList.remove("hidden");
  btn.disabled = false;
}

async function enviarVidaMsg() {
  const inp = $("#v-input");
  const texto = inp.value.trim();
  if (!texto) return;
  inp.value = "";
  addMsgEl("#v-messages", "user", texto);
  VIDA.historico.push({ role: "user", content: texto });
  const tEl = thinking("#v-messages");
  const r = await fetch("/api/vida", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ questionario: VIDA.questionario, historico: VIDA.historico }),
  }).then((res) => res.json());
  tEl.remove();
  VIDA.historico.push({ role: "assistant", content: r.resposta });
  addMsgEl("#v-messages", "assistant", r.resposta);
}

async function enviarVidaLead() {
  const nome = $("#v-lead-nome").value.trim();
  const contato = $("#v-lead-contato").value.trim();
  if (!nome || !contato) return;
  await fetch("/api/lead", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome, contato, bairro: VIDA.dados?.local || "" }),
  });
  $("#v-lead-nome").value = ""; $("#v-lead-contato").value = "";
  await gerarRelatorio(VIDA.dados, {}, $("#v-lead-ok"), nome.split(" ")[0]);
}

// toggles trabalho/estudo
$("#v-trabalha").addEventListener("change", (e) =>
  $("#v-trabalho-box").classList.toggle("hidden", !e.target.checked));
$("#v-estuda").addEventListener("change", (e) =>
  $("#v-estudo-box").classList.toggle("hidden", !e.target.checked));
$("#btn-vida").addEventListener("click", verVida);
$("#v-send").addEventListener("click", enviarVidaMsg);
$("#v-input").addEventListener("keydown", (e) => { if (e.key === "Enter") enviarVidaMsg(); });
$("#v-lead-send").addEventListener("click", enviarVidaLead);

// ===================== Listeners =====================
$("#btn-recomendar").addEventListener("click", recomendar);
$("#chat-send").addEventListener("click", enviarMensagem);
$("#chat-input").addEventListener("keydown", (e) => { if (e.key === "Enter") enviarMensagem(); });
$("#lead-send").addEventListener("click", enviarLead);
["s-bairro", "s-area", "s-pessoas", "s-modo", "s-op"].forEach((id) =>
  $("#" + id).addEventListener("change", simular));

init();
