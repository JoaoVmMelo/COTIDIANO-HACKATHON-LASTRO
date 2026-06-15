# -*- coding: utf-8 -*-
"""Monta uma BASE DE LOCAIS por bairro (empresas, padarias, escolas, petshops,
restaurantes, veterinário, mercado, farmácia, parque) via Overpass/OpenStreetMap
-> cache/entorno.json.  Rode:  python build_entorno.py   (precisa de internet).

Faz 1 consulta por bairro (união de filtros) e classifica cada resultado por categoria.
Respeita o rate limit do Overpass (pausa entre bairros)."""
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
import config as C

OVERPASS = "https://overpass-api.de/api/interpreter"
RAIO = 1000           # metros ao redor do centro do bairro
MAX_POR_CAT = 35      # cota POR categoria (cada uma tem vaga própria na query)

# (categoria, [filtros OSM]) — cada categoria recebe um `out` próprio (sem starvation)
CATEGORIAS = [
    ("padaria",     ['node["shop"="bakery"]']),
    ("cafe",        ['node["amenity"="cafe"]']),
    ("escola",      ['node["amenity"="school"]', 'way["amenity"="school"]']),
    ("petshop",     ['node["shop"="pet"]']),
    ("veterinario", ['node["amenity"="veterinary"]']),
    ("restaurante", ['node["amenity"="restaurant"]']),
    ("empresa",     ['node["office"]']),
    ("mercado",     ['node["shop"="supermarket"]']),
    ("farmacia",    ['node["amenity"="pharmacy"]']),
    ("parque",      ['node["leisure"="park"]', 'way["leisure"="park"]']),
    ("academia",    ['node["leisure"="fitness_centre"]', 'way["leisure"="fitness_centre"]']),
    ("metro",       ['node["railway"="subway_entrance"]', 'node["railway"="station"]["station"="subway"]']),
    ("hospital",    ['node["amenity"="hospital"]', 'way["amenity"="hospital"]']),
]


def classifica(tags):
    if tags.get("shop") == "bakery": return "padaria"
    if tags.get("amenity") == "cafe": return "cafe"
    if tags.get("amenity") == "school": return "escola"
    if tags.get("shop") == "pet": return "petshop"
    if tags.get("amenity") == "veterinary": return "veterinario"
    if tags.get("amenity") == "restaurant": return "restaurante"
    if tags.get("shop") == "supermarket": return "mercado"
    if tags.get("amenity") == "pharmacy": return "farmacia"
    if tags.get("leisure") == "park": return "parque"
    if tags.get("leisure") == "fitness_centre": return "academia"
    if tags.get("railway") == "subway_entrance" or (tags.get("railway") == "station" and tags.get("station") == "subway"): return "metro"
    if tags.get("amenity") == "hospital": return "hospital"
    if "office" in tags: return "empresa"
    return None


CACHE = "cache/entorno.json"


def consulta(lat, lng, tentativas=4):
    # cada categoria vira um conjunto próprio com seu próprio `out` -> cota garantida por categoria
    blocos = []
    for i, (_, filtros) in enumerate(CATEGORIAS):
        corpo = "".join(f"{f}(around:{RAIO},{lat},{lng});" for f in filtros)
        blocos.append(f"({corpo})->.s{i};.s{i} out center {MAX_POR_CAT};")
    q = "[out:json][timeout:90];" + "".join(blocos)
    data = urllib.parse.urlencode({"data": q}).encode()
    for t in range(tentativas):
        try:
            req = urllib.request.Request(OVERPASS, data=data,
                                         headers={"User-Agent": "Cotidiano/1.0 (hackathon Lastro)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 504) and t < tentativas - 1:
                espera = 12 * (t + 1)  # backoff: 12s, 24s, 36s
                print(f"({e.code}, espera {espera}s)", end=" ", flush=True)
                time.sleep(espera)
            else:
                raise


def _salva(base):
    os.makedirs("cache", exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)


def main():
    base = {}
    if os.path.exists(CACHE):
        try:
            base = json.load(open(CACHE, encoding="utf-8"))
        except Exception:
            base = {}

    for i, (bairro, c) in enumerate(C.BAIRROS_CATALOGO.items(), 1):
        if base.get(bairro):  # já tem dado -> pula (não refaz)
            print(f"[{i}/{len(C.BAIRROS_CATALOGO)}] {bairro}... já tem ({len(base[bairro])})")
            continue
        print(f"[{i}/{len(C.BAIRROS_CATALOGO)}] {bairro}...", end=" ", flush=True)
        try:
            js = consulta(c["lat"], c["lng"])
        except Exception as e:
            print("ERRO:", e, "— re-rode depois")
            continue
        pontos, cont = [], {}
        for el in js.get("elements", []):
            cat = classifica(el.get("tags", {}))
            if not cat or cont.get(cat, 0) >= MAX_POR_CAT:
                continue
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lng = el.get("lon") or (el.get("center") or {}).get("lon")
            if lat is None or lng is None:
                continue
            tags = el.get("tags", {})
            pontos.append({"lat": round(lat, 6), "lng": round(lng, 6), "categoria": cat,
                           "nome": tags.get("name", ""),
                           "horario": tags.get("opening_hours", "")})  # horário real do OSM (quando há)
            cont[cat] = cont.get(cat, 0) + 1
        base[bairro] = pontos
        _salva(base)  # salva incremental (não perde progresso se cair)
        resumo = ", ".join(f"{k}:{v}" for k, v in sorted(cont.items())) or "vazio"
        print(f"{len(pontos)} pontos ({resumo})")
        time.sleep(4)  # educação com o servidor público

    _salva(base)
    total = sum(len(v) for v in base.values())
    print(f"\nOK -> {CACHE} ({total} locais em {len([b for b in base if base[b]])} bairros)")


if __name__ == "__main__":
    main()
