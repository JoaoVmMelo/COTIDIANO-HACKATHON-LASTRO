/**
 * Cotidiano — gerador de banco de dados sintético (São Paulo)
 * Gera: imóveis, escolas, pontos de ônibus (com linhas/frequência),
 * POIs com horário de funcionamento, e rotas/distâncias por modo.
 *
 * Uso:  node generate-data.js
 * Saída: ./database.json  (+ arquivos individuais em ./tables/)
 *
 * RNG semeado => mesma saída toda vez (troque SEED p/ outro dataset).
 */

const fs = require('fs');
const path = require('path');

// ---------- RNG semeado (mulberry32) ----------
const SEED = 20260614;
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = mulberry32(SEED);
const rint = (min, max) => Math.floor(rnd() * (max - min + 1)) + min;
const rfloat = (min, max, d = 2) => +(rnd() * (max - min) + min).toFixed(d);
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
const pickN = (arr, n) => {
  const c = [...arr];
  const out = [];
  while (out.length < n && c.length) out.push(c.splice(Math.floor(rnd() * c.length), 1)[0]);
  return out;
};
const chance = (p) => rnd() < p;

// ---------- geo ----------
function haversineM(a, b) {
  const R = 6371000, toRad = (x) => (x * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat), dLng = toRad(b.lng - a.lng);
  const la1 = toRad(a.lat), la2 = toRad(b.lat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLng / 2) ** 2;
  return Math.round(2 * R * Math.asin(Math.sqrt(h)));
}
// jitter ~ raio em metros ao redor de um centro
function jitter(center, raioM) {
  const dLat = (rnd() - 0.5) * 2 * (raioM / 111000);
  const dLng = (rnd() - 0.5) * 2 * (raioM / (111000 * Math.cos((center.lat * Math.PI) / 180)));
  return { lat: +(center.lat + dLat).toFixed(6), lng: +(center.lng + dLng).toFixed(6) };
}
// tempos (min) a partir da distância em metros
function tempos(distM) {
  const kmh = { a_pe: 5, bike: 15, carro: 24, transporte: 16 };
  const esperaTransporte = 6; // min de espera média
  return {
    a_pe: Math.max(1, Math.round((distM / 1000 / kmh.a_pe) * 60)),
    bike: Math.max(1, Math.round((distM / 1000 / kmh.bike) * 60)),
    carro: Math.max(1, Math.round((distM / 1000 / kmh.carro) * 60)),
    transporte: Math.max(1, Math.round((distM / 1000 / kmh.transporte) * 60) + esperaTransporte),
  };
}

// ---------- dados-base de SP ----------
const BAIRROS = [
  { nome: 'Vila Madalena', lat: -23.5547, lng: -46.6896, precoM2: 11200, perfil: 'jovem/boêmio', ruidoNoite: 'alto' },
  { nome: 'Pinheiros',     lat: -23.5645, lng: -46.7019, precoM2: 12400, perfil: 'jovem/conectado', ruidoNoite: 'médio' },
  { nome: 'Moema',         lat: -23.6005, lng: -46.6650, precoM2: 11800, perfil: 'familiar/alto padrão', ruidoNoite: 'baixo' },
  { nome: 'Vila Mariana',  lat: -23.5890, lng: -46.6340, precoM2: 10300, perfil: 'familiar/tranquilo', ruidoNoite: 'baixo' },
  { nome: 'Tatuapé',       lat: -23.5400, lng: -46.5760, precoM2: 8600,  perfil: 'familiar', ruidoNoite: 'médio' },
  { nome: 'Santana',       lat: -23.5050, lng: -46.6250, precoM2: 8100,  perfil: 'familiar/tradicional', ruidoNoite: 'baixo' },
  { nome: 'Butantã',       lat: -23.5710, lng: -46.7080, precoM2: 7600,  perfil: 'universitário', ruidoNoite: 'médio' },
];

const HUBS_TRABALHO = [
  { nome: 'Av. Paulista',  lat: -23.5614, lng: -46.6560 },
  { nome: 'Faria Lima',    lat: -23.5760, lng: -46.6850 },
  { nome: 'Berrini',       lat: -23.6110, lng: -46.6960 },
  { nome: 'Centro (Sé)',   lat: -23.5500, lng: -46.6340 },
];

const CATEGORIAS_POI = {
  mercado:    { nomes: ['Mercado', 'Supermercado', 'Empório', 'Hortifruti'], horario: '08:00-22:00' },
  padaria:    { nomes: ['Padaria', 'Panificadora', 'Casa de Pães'], horario: '06:00-20:00' },
  farmacia:   { nomes: ['Farmácia', 'Drogaria'], horario: '07:00-23:00', h24: 0.25 },
  cafe:       { nomes: ['Café', 'Cafeteria', 'Coffee'], horario: '07:00-19:00' },
  academia:   { nomes: ['Academia', 'Studio Fit', 'CrossBox'], horario: '06:00-23:00' },
  parque:     { nomes: ['Parque', 'Praça'], horario: '05:00-22:00' },
  restaurante:{ nomes: ['Restaurante', 'Bistrô', 'Cantina'], horario: '11:00-23:00' },
  hospital:   { nomes: ['Hospital', 'Pronto-Socorro', 'UPA'], horario: '24h' },
  banco:      { nomes: ['Banco', 'Agência'], horario: '10:00-16:00' },
  petshop:    { nomes: ['Pet Shop', 'Clínica Vet'], horario: '08:00-20:00' },
};

const SOBRENOMES = ['Augusta', 'Harmonia', 'Aspicuelta', 'Fradique', 'Cardeal', 'Girassol', 'Wisard',
  'Mourato', 'Teodoro', 'Joaquim', 'Cunha Gago', 'Fidalga', 'Inácio Pereira', 'Belmiro', 'Original'];
const TIPOS_VIA = ['Rua', 'Av.', 'Alameda', 'Travessa'];

// ---------- geradores ----------
let _id = 0;
const nid = (p) => `${p}_${(++_id).toString().padStart(4, '0')}`;

function gerarPOIs() {
  const pois = [];
  for (const b of BAIRROS) {
    for (const [cat, cfg] of Object.entries(CATEGORIAS_POI)) {
      const qtd = cat === 'hospital' ? rint(0, 1) : cat === 'parque' ? rint(1, 3) : rint(2, 6);
      for (let i = 0; i < qtd; i++) {
        const loc = jitter(b, 1400);
        const h24 = cfg.h24 && chance(cfg.h24);
        pois.push({
          id: nid('poi'),
          nome: `${pick(cfg.nomes)} ${pick(['do Bairro', 'Central', 'Express', pick(SOBRENOMES), '24h', 'da Esquina'])}`.replace(' 24h', h24 ? ' 24h' : ''),
          categoria: cat,
          bairro: b.nome,
          lat: loc.lat,
          lng: loc.lng,
          opening_hours: h24 ? '24h' : cfg.horario,
          nota: rfloat(3.4, 4.9, 1),
        });
      }
    }
  }
  return pois;
}

function gerarEscolas() {
  const escolas = [];
  const niveis = ['creche', 'fundamental', 'médio'];
  for (const b of BAIRROS) {
    const qtd = rint(2, 5);
    for (let i = 0; i < qtd; i++) {
      const loc = jitter(b, 1500);
      const rede = chance(0.55) ? 'privada' : 'pública';
      escolas.push({
        id: nid('esc'),
        nome: `${chance(0.5) ? 'Colégio' : chance(0.5) ? 'Escola' : 'EMEI'} ${pick(SOBRENOMES)}`,
        rede,
        niveis: pickN(niveis, rint(1, 3)),
        bairro: b.nome,
        lat: loc.lat,
        lng: loc.lng,
        idea_nota: rfloat(4.5, 7.8, 1), // nota fictícia tipo IDEB
        horario: '07:00-18:00',
      });
    }
  }
  return escolas;
}

function gerarPontosOnibus() {
  const pontos = [];
  const destinos = ['Term. Pinheiros', 'Metrô Faria Lima', 'Term. Lapa', 'Metrô Santana',
    'Praça da Sé', 'Term. Bandeira', 'Metrô Vila Madalena', 'USP', 'Aeroporto Congonhas', 'Term. Princesa Isabel'];
  for (const b of BAIRROS) {
    const qtd = rint(3, 7);
    for (let i = 0; i < qtd; i++) {
      const loc = jitter(b, 1300);
      const nLinhas = rint(1, 4);
      const linhas = [];
      for (let l = 0; l < nLinhas; l++) {
        linhas.push({
          numero: `${rint(100, 899)}${pick(['', 'A', 'P', '-10', 'C'])}`,
          destino: pick(destinos),
          frequencia_min: pick([8, 10, 12, 15, 20, 25, 30]),
        });
      }
      pontos.push({
        id: nid('bus'),
        nome: `Ponto ${pick(TIPOS_VIA)} ${pick(SOBRENOMES)}`,
        bairro: b.nome,
        lat: loc.lat,
        lng: loc.lng,
        linhas,
      });
    }
  }
  return pontos;
}

function nearest(origem, lista, n) {
  return lista
    .map((x) => ({ ...x, distancia_m: haversineM(origem, x) }))
    .sort((a, b) => a.distancia_m - b.distancia_m)
    .slice(0, n);
}

function gerarImoveis(pois, escolas, pontos) {
  const imoveis = [];
  const tipos = ['Apartamento', 'Casa', 'Studio', 'Cobertura', 'Kitnet'];
  for (const b of BAIRROS) {
    const qtd = rint(8, 11);
    for (let i = 0; i < qtd; i++) {
      const loc = jitter(b, 1200);
      const tipo = pick(tipos);
      const quartos = tipo === 'Kitnet' || tipo === 'Studio' ? rint(0, 1) : rint(1, 4);
      const area = tipo === 'Casa' ? rint(90, 320)
        : tipo === 'Cobertura' ? rint(120, 280)
        : tipo === 'Studio' || tipo === 'Kitnet' ? rint(22, 45)
        : rint(38, 140);
      const fatorTipo = tipo === 'Cobertura' ? 1.25 : tipo === 'Casa' ? 0.95 : 1;
      const valorVenda = Math.round((area * b.precoM2 * fatorTipo * rfloat(0.9, 1.12)) / 1000) * 1000;
      const valorAluguel = Math.round((valorVenda * rfloat(0.0035, 0.0052, 5)) / 50) * 50;
      const o = { lat: loc.lat, lng: loc.lng };

      const imovel = {
        id: nid('imv'),
        titulo: `${tipo} ${quartos > 0 ? quartos + ' dorm.' : 'sem dorm.'} em ${b.nome}`,
        endereco: `${pick(TIPOS_VIA)} ${pick(SOBRENOMES)}, ${rint(20, 1990)}`,
        bairro: b.nome,
        lat: loc.lat,
        lng: loc.lng,
        tipo,
        quartos,
        banheiros: Math.max(1, Math.min(quartos, rint(1, 3))),
        vagas: tipo === 'Kitnet' ? 0 : rint(0, 3),
        area_m2: area,
        valor_venda: valorVenda,
        valor_aluguel: valorAluguel,
        condominio: tipo === 'Casa' ? 0 : Math.round((rint(400, 1800)) / 10) * 10,
        iptu_mensal: Math.round((valorVenda * 0.000045) / 10) * 10,
        andar: tipo === 'Casa' ? null : rint(1, 22),
        mobiliado: chance(0.3),
        aceita_pet: chance(0.7),
        perfil_bairro: b.perfil,
        ruido_noturno: b.ruidoNoite,
        // relacionamentos espaciais já pré-computados:
        entorno: nearest(o, pois, 12).map((p) => ({
          id: p.id, nome: p.nome, categoria: p.categoria, opening_hours: p.opening_hours,
          nota: p.nota, distancia_m: p.distancia_m, tempos: tempos(p.distancia_m),
        })),
        escolas_proximas: nearest(o, escolas, 5).map((e) => ({
          id: e.id, nome: e.nome, rede: e.rede, niveis: e.niveis, idea_nota: e.idea_nota,
          distancia_m: e.distancia_m, tempos: tempos(e.distancia_m),
        })),
        pontos_onibus: nearest(o, pontos, 4).map((pt) => ({
          id: pt.id, nome: pt.nome, linhas: pt.linhas,
          distancia_m: pt.distancia_m, tempo_a_pe_min: tempos(pt.distancia_m).a_pe,
        })),
        rotas_trabalho: HUBS_TRABALHO.map((h) => {
          const d = haversineM(o, h);
          const t = tempos(d);
          return { hub: h.nome, distancia_km: +(d / 1000).toFixed(1), tempos_min: t };
        }),
      };
      imoveis.push(imovel);
    }
  }
  return imoveis;
}

// ---------- montar e salvar ----------
const pois = gerarPOIs();
const escolas = gerarEscolas();
const pontos = gerarPontosOnibus();
const imoveis = gerarImoveis(pois, escolas, pontos);

const db = {
  meta: {
    projeto: 'Cotidiano',
    cidade: 'São Paulo',
    gerado_em: '2026-06-14',
    seed: SEED,
    descricao: 'Banco sintético: imóveis com entorno, escolas, ônibus e rotas pré-computadas.',
    contagens: { imoveis: imoveis.length, pois: pois.length, escolas: escolas.length, pontos_onibus: pontos.length, bairros: BAIRROS.length, hubs_trabalho: HUBS_TRABALHO.length },
    premissas_tempo: { a_pe_kmh: 5, bike_kmh: 15, carro_kmh: 24, transporte_kmh: 16, espera_transporte_min: 6 },
  },
  bairros: BAIRROS,
  hubs_trabalho: HUBS_TRABALHO,
  imoveis,
  escolas,
  pontos_onibus: pontos,
  pois,
};

const outDir = __dirname;
const tablesDir = path.join(outDir, 'tables');
if (!fs.existsSync(tablesDir)) fs.mkdirSync(tablesDir, { recursive: true });

fs.writeFileSync(path.join(outDir, 'database.json'), JSON.stringify(db, null, 2), 'utf8');
fs.writeFileSync(path.join(tablesDir, 'imoveis.json'), JSON.stringify(imoveis, null, 2), 'utf8');
fs.writeFileSync(path.join(tablesDir, 'escolas.json'), JSON.stringify(escolas, null, 2), 'utf8');
fs.writeFileSync(path.join(tablesDir, 'pontos_onibus.json'), JSON.stringify(pontos, null, 2), 'utf8');
fs.writeFileSync(path.join(tablesDir, 'pois.json'), JSON.stringify(pois, null, 2), 'utf8');

console.log('OK — database.json gerado.');
console.log(JSON.stringify(db.meta.contagens, null, 2));
