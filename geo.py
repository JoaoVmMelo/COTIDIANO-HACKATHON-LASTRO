# -*- coding: utf-8 -*-
"""Camada geo: usa cache real (cache/geo.json) se existir; senão estima pela coordenada.
Inclui geocoding (Nominatim) com cache p/ resolver endereços de trabalho/estudo."""
import json
import os
import math
import unicodedata
import urllib.parse
import urllib.request
import config as C

CACHE_PATH = "cache/geo.json"
ENTORNO_PATH = "cache/entorno.json"
GEOCODE_CACHE_PATH = "cache/geocode.json"
DETOUR = 1.35  # fator de desvio viário (linha reta -> rua)


def haversine_km(a_lat, a_lng, b_lat, b_lng):
    R = 6371.0
    p = math.pi / 180
    dlat = (b_lat - a_lat) * p
    dlng = (b_lng - a_lng) * p
    h = (math.sin(dlat / 2) ** 2
         + math.cos(a_lat * p) * math.cos(b_lat * p) * math.sin(dlng / 2) ** 2)
    return round(2 * R * math.asin(math.sqrt(h)), 2)


def _tempo(dist_km, modo):
    v = C.VELOCIDADE_KMH[modo]
    t = dist_km / v * 60
    if modo == "transporte":
        t += C.ESPERA_TRANSPORTE_MIN
    return max(1, round(t))


def _load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


_CACHE = _load_cache()


def geo_do_imovel(imovel, modo="transporte"):
    """Distância ao trabalho + tempos + entorno. Cache real se houver; senão estimado."""
    cache = _CACHE.get(imovel["id"])
    if cache and cache.get("distancia_trabalho_km") is not None:
        return cache
    # fallback: distância em linha reta * fator de desvio viário (~1.35)
    dist = haversine_km(imovel["lat"], imovel["lng"],
                        C.TRABALHO["lat"], C.TRABALHO["lng"]) * 1.35
    tempos = {m: _tempo(dist, m) for m in C.VELOCIDADE_KMH}
    return {
        "distancia_trabalho_km": round(dist, 1),
        "tempos_min": tempos,
        "entorno": [],
        "fonte": "estimado (rode cache_geo.py p/ dado real)",
    }


# ==================== Base de locais por bairro (entorno) ====================
_ENTORNO = None


def _norm_bairro(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.lower().strip()


def entorno_do_bairro(bairro):
    """Locais reais (empresas, padarias, escolas, petshops...) do bairro -> cache/entorno.json."""
    global _ENTORNO
    if _ENTORNO is None:
        try:
            _ENTORNO = json.load(open(ENTORNO_PATH, encoding="utf-8")) if os.path.exists(ENTORNO_PATH) else {}
        except Exception:
            _ENTORNO = {}
    pts = _ENTORNO.get(bairro)
    if pts is None:
        alvo = _norm_bairro(bairro)
        pts = next((v for k, v in _ENTORNO.items() if _norm_bairro(k) == alvo), [])
    return pts or []


# ==================== Entorno ao redor de um PONTO (ex: trabalho) ====================
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ENTORNO_PONTOS_PATH = "cache/entorno_pontos.json"

# categorias úteis perto do trabalho (almoço, café, academia, happy hour...)
_CATS_TRAB = [
    ("restaurante", ['node["amenity"="restaurant"]']),
    ("cafe", ['node["amenity"="cafe"]']),
    ("academia", ['node["leisure"="fitness_centre"]']),
    ("bar", ['node["amenity"="bar"]', 'node["amenity"="pub"]']),
    ("mercado", ['node["shop"="supermarket"]']),
    ("farmacia", ['node["amenity"="pharmacy"]']),
    ("parque", ['node["leisure"="park"]', 'way["leisure"="park"]']),
]


def _classifica_trab(tags):
    if tags.get("amenity") == "restaurant": return "restaurante"
    if tags.get("amenity") == "cafe": return "cafe"
    if tags.get("leisure") == "fitness_centre": return "academia"
    if tags.get("amenity") in ("bar", "pub"): return "bar"
    if tags.get("shop") == "supermarket": return "mercado"
    if tags.get("amenity") == "pharmacy": return "farmacia"
    if tags.get("leisure") == "park": return "parque"
    return None


def _load_ep():
    if os.path.exists(ENTORNO_PONTOS_PATH):
        try:
            return json.load(open(ENTORNO_PONTOS_PATH, encoding="utf-8"))
        except Exception:
            return {}
    return {}


_ENTORNO_PONTOS = _load_ep()


def entorno_em(lat, lng, raio=600, max_cat=12):
    """Lazer/comércio reais ao redor de um ponto (ex: trabalho), via Overpass. Cacheado por
    coordenada. Lista vazia se o Overpass falhar (não quebra o app)."""
    if lat is None or lng is None:
        return []
    chave = f"{round(lat, 4)},{round(lng, 4)}"
    if chave in _ENTORNO_PONTOS:
        return _ENTORNO_PONTOS[chave]
    blocos = []
    for i, (_, filtros) in enumerate(_CATS_TRAB):
        corpo = "".join(f"{f}(around:{raio},{lat},{lng});" for f in filtros)
        blocos.append(f"({corpo})->.s{i};.s{i} out center {max_cat};")
    q = "[out:json][timeout:40];" + "".join(blocos)
    try:
        data = urllib.parse.urlencode({"data": q}).encode()
        req = urllib.request.Request(OVERPASS_URL, data=data,
                                     headers={"User-Agent": "Cotidiano/1.0 (hackathon Lastro)"})
        with urllib.request.urlopen(req, timeout=45) as r:
            js = json.load(r)
        pontos = []
        for el in js.get("elements", []):
            cat = _classifica_trab(el.get("tags", {}))
            la = el.get("lat") or (el.get("center") or {}).get("lat")
            lo = el.get("lon") or (el.get("center") or {}).get("lon")
            if not cat or la is None or lo is None:
                continue
            t = el.get("tags", {})
            pontos.append({"lat": round(la, 6), "lng": round(lo, 6), "categoria": cat,
                           "nome": t.get("name", ""), "horario": t.get("opening_hours", "")})
        _ENTORNO_PONTOS[chave] = pontos
        os.makedirs("cache", exist_ok=True)
        with open(ENTORNO_PONTOS_PATH, "w", encoding="utf-8") as f:
            json.dump(_ENTORNO_PONTOS, f, ensure_ascii=False)
        return pontos
    except Exception:
        return []


# ==================== Geocoding + trajeto genérico ====================
def _load_geocode_cache():
    if os.path.exists(GEOCODE_CACHE_PATH):
        try:
            with open(GEOCODE_CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


_GEO_CACHE = _load_geocode_cache()


# dois viewboxes (lon_oeste,lat_norte,lon_leste,lat_sul):
VB_CENTRO = "-46.80,-23.48,-46.58,-23.68"   # centro expandido — resolve ruas homônimas (ex: Faria Lima)
VB_CIDADE = "-46.83,-23.36,-46.36,-23.82"   # município inteiro — alcança zona norte/sul (ex: Cachoeirinha)


def _nominatim(q, viewbox, bounded):
    params = {"q": q, "format": "json", "limit": 1, "countrycodes": "br",
              "viewbox": viewbox, "bounded": 1 if bounded else 0}
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Cotidiano/1.0 (hackathon Lastro)"})
    with urllib.request.urlopen(req, timeout=6) as r:
        d = json.load(r)
    return d[0] if d else None


def geocode(endereco):
    """Resolve um endereço -> {lat, lng, nome} via Nominatim (cacheado). None se falhar.
    Busca no centro (estrito) E na cidade inteira (viés), e fica com a de maior `importance` —
    assim acerta tanto rua homônima central quanto bairro de zona norte/sul."""
    if not endereco or not endereco.strip():
        return None
    chave = endereco.strip().lower()
    if chave in _GEO_CACHE:
        return _GEO_CACHE[chave]

    q = endereco if ("são paulo" in chave or "sao paulo" in chave) else f"{endereco}, São Paulo, SP"
    try:
        central = _nominatim(q, VB_CENTRO, True)     # estrito no centro
        cidade = _nominatim(q, VB_CIDADE, False)     # cidade inteira, só viés
        cands = [c for c in (central, cidade) if c]
        if not cands:
            return None
        best = max(cands, key=lambda c: float(c.get("importance", 0)))  # empate -> central (vem 1º)
        partes = best.get("display_name", endereco).split(",")
        nome = ", ".join(p.strip() for p in partes[:2] if p.strip())
        res = {"lat": float(best["lat"]), "lng": float(best["lon"]), "nome": nome}
        _GEO_CACHE[chave] = res
        os.makedirs("cache", exist_ok=True)
        with open(GEOCODE_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_GEO_CACHE, f, ensure_ascii=False, indent=2)
        return res
    except Exception:
        return None


def resolver_local(endereco=None, bairro=None):
    """Devolve coords de um destino: tenta o endereço (geocode); cai no bairro do catálogo."""
    if endereco:
        g = geocode(endereco)
        if g:
            return {"lat": g["lat"], "lng": g["lng"], "nome": g["nome"], "fonte": "endereço localizado"}
    if bairro and bairro in C.BAIRROS_CATALOGO:
        c = C.BAIRROS_CATALOGO[bairro]
        return {"lat": c["lat"], "lng": c["lng"], "nome": bairro, "fonte": "centro do bairro"}
    return None


OSRM_URL = "https://router.project-osrm.org/route/v1/driving/"
ROTAS_PATH = "cache/rotas.json"


def _load_rotas():
    if os.path.exists(ROTAS_PATH):
        try:
            return json.load(open(ROTAS_PATH, encoding="utf-8"))
        except Exception:
            return {}
    return {}


_ROTAS = _load_rotas()


def _osrm_rota(o_lat, o_lng, d_lat, d_lng):
    """Rota real por ruas (OSRM driving) -> [dist_km, dur_min]. None se falhar."""
    url = f"{OSRM_URL}{o_lng},{o_lat};{d_lng},{d_lat}?overview=false"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Cotidiano/1.0 (hackathon Lastro)"})
        with urllib.request.urlopen(req, timeout=6) as r:
            js = json.load(r)
        if js.get("code") == "Ok" and js.get("routes"):
            rt = js["routes"][0]
            return [round(rt["distance"] / 1000.0, 2), round(rt["duration"] / 60.0, 1)]
    except Exception:
        return None
    return None


def trajeto(orig_lat, orig_lng, dest, modo="transporte"):
    """Distância + tempo entre origem e destino. Usa ROTA REAL (OSRM, cacheada);
    cai na estimativa por linha reta se o OSRM não responder."""
    if not dest:
        return None
    chave = f"{round(orig_lat, 4)},{round(orig_lng, 4)};{round(dest['lat'], 4)},{round(dest['lng'], 4)}"
    rota = _ROTAS.get(chave)
    if rota is None:
        rota = _osrm_rota(orig_lat, orig_lng, dest["lat"], dest["lng"])
        if rota:
            _ROTAS[chave] = rota
            os.makedirs("cache", exist_ok=True)
            with open(ROTAS_PATH, "w", encoding="utf-8") as f:
                json.dump(_ROTAS, f, ensure_ascii=False)

    if rota:
        dist_km, dur_carro_min = rota          # distância REAL por ruas
        rota_real = True
    else:
        dist_km = haversine_km(orig_lat, orig_lng, dest["lat"], dest["lng"]) * DETOUR
        dur_carro_min = None
        rota_real = False

    # tempo: de carro usa a duração real do OSRM; nos outros modos, distância real ÷ velocidade
    if modo == "carro" and dur_carro_min:
        tempo = max(1, round(dur_carro_min))
    else:
        tempo = _tempo(dist_km, modo)

    return {
        "destino": dest.get("nome", ""),
        "fonte": dest.get("fonte", ""),
        "distancia_km": round(dist_km, 1),
        "tempo_min": tempo,
        "modo": modo,
        "rota_real": rota_real,
    }
