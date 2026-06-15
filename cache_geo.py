# -*- coding: utf-8 -*-
"""Pré-cacheia dados geo REAIS (Overpass/OSRM) p/ os imóveis-demo -> cache/geo.json.
Usa só a biblioteca padrão (urllib). Rode uma vez:  python cache_geo.py"""
import json
import os
import time
import urllib.request
import urllib.parse
import config as C

UA = {"User-Agent": "CotidianoHackathon/1.0"}


def _get(url, data=None, timeout=35):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def osrm_carro(o_lat, o_lng, d_lat, d_lng):
    url = (f"https://router.project-osrm.org/route/v1/driving/"
           f"{o_lng},{o_lat};{d_lng},{d_lat}?overview=false")
    rt = _get(url)["routes"][0]
    return round(rt["distance"] / 1000, 1), round(rt["duration"] / 60)


def overpass_entorno(lat, lng, raio=800):
    q = ("[out:json][timeout:25];("
         f'node["shop"="bakery"](around:{raio},{lat},{lng});'
         f'node["shop"="supermarket"](around:{raio},{lat},{lng});'
         f'node["amenity"="pharmacy"](around:{raio},{lat},{lng});'
         f'node["amenity"="school"](around:{raio},{lat},{lng});'
         f'node["highway"="bus_stop"](around:{raio},{lat},{lng}););out body 30;')
    data = urllib.parse.urlencode({"data": q}).encode()
    j = _get("https://overpass-api.de/api/interpreter", data=data)
    out = []
    for e in j.get("elements", []):
        t = e.get("tags", {})
        cat = t.get("shop") or t.get("amenity") or t.get("highway")
        out.append({"categoria": cat, "nome": t.get("name", "(sem nome)"),
                    "lat": e["lat"], "lng": e["lon"],
                    "opening_hours": t.get("opening_hours")})
    return out


def _tempo(dist_km, modo):
    v = C.VELOCIDADE_KMH[modo]
    t = dist_km / v * 60
    if modo == "transporte":
        t += C.ESPERA_TRANSPORTE_MIN
    return max(1, round(t))


def main():
    os.makedirs("cache", exist_ok=True)
    cache = {}
    w = C.TRABALHO
    for im in C.DEMO_IMOVEIS:
        print("->", im["label"])
        dist = dur = None
        try:
            dist, dur = osrm_carro(im["lat"], im["lng"], w["lat"], w["lng"])
        except Exception as ex:
            print("   OSRM falhou:", ex)
        entorno = []
        try:
            entorno = overpass_entorno(im["lat"], im["lng"])
            print(f"   entorno: {len(entorno)} pontos reais")
        except Exception as ex:
            print("   Overpass falhou:", ex)
        tempos = {m: _tempo(dist, m) for m in C.VELOCIDADE_KMH} if dist else {}
        cache[im["id"]] = {
            "distancia_trabalho_km": dist,
            "tempo_carro_min": dur,
            "tempos_min": tempos,
            "entorno": entorno,
            "fonte": "real (OSM/OSRM)",
        }
        time.sleep(1.2)  # gentileza com as APIs públicas
    with open("cache/geo.json", "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print("OK -> cache/geo.json")


if __name__ == "__main__":
    main()
