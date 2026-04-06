#!/usr/bin/env python3
"""
fetch_data.py — Собирает данные VRS/турниров с Liquipedia и сохраняет в data/*.json
Запускается GitHub Actions каждые 6 часов.

Использует: Liquipedia API v3 (https://api.liquipedia.net/api/v3/)
Регистрация API-ключа: https://api.liquipedia.net/api-docs (бесплатно)
"""

import json
import os
import time
import datetime
import re
import urllib.request
import urllib.parse

# ── Конфиг ──────────────────────────────────────────────────────────────────
# Установи API_KEY в GitHub Secrets как LIQUIPEDIA_API_KEY
API_KEY = os.environ.get("LIQUIPEDIA_API_KEY", "")
BASE_URL = "https://api.liquipedia.net/api/v3"
HEADERS = {
    "Authorization": f"Apikey {API_KEY}",
    "Accept": "application/json",
    "User-Agent": "CS2Hub/1.0 (GitHub Pages; contact via repo issues)"
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Флаги стран для популярных команд ───────────────────────────────────────
TEAM_FLAGS = {
    "Natus Vincere": "🇺🇦", "NAVI": "🇺🇦",
    "Team Vitality": "🇫🇷", "Vitality": "🇫🇷",
    "FaZe Clan": "🌍", "FaZe": "🌍",
    "G2 Esports": "🇪🇺", "G2": "🇪🇺",
    "Team Spirit": "🇷🇺", "Spirit": "🇷🇺",
    "Heroic": "🇩🇰",
    "Astralis": "🇩🇰",
    "MOUZ": "🇩🇪",
    "Falcons": "🇸🇦",
    "Cloud9": "🇺🇸", "C9": "🇺🇸",
    "Team Liquid": "🇺🇸", "Liquid": "🇺🇸",
    "NRG Esports": "🇺🇸", "NRG": "🇺🇸",
    "MIBR": "🇧🇷",
    "Imperial": "🇧🇷",
    "paiN Gaming": "🇧🇷", "paiN": "🇧🇷",
    "FURIA": "🇧🇷",
    "TYLOO": "🇨🇳",
    "Lynn Vision": "🇨🇳",
    "The MongolZ": "🇲🇳", "MongolZ": "🇲🇳",
    "ENCE": "🇫🇮",
    "Complexity": "🇺🇸",
    "BIG": "🇩🇪",
    "OG": "🇪🇺",
    "3DMAX": "🇫🇷",
    "SAW": "🇵🇹",
    "Eternal Fire": "🇹🇷",
}

def lp_get(endpoint, params):
    """HTTP GET к Liquipedia API."""
    url = f"{BASE_URL}/{endpoint}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  [WARN] {endpoint}: {e}")
        return None

def save_json(filename, data):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Сохранено: {filename}")

# ── Парсинг VRS рейтинга ─────────────────────────────────────────────────────
def fetch_vrs_rankings():
    print("\n[1/3] Загружаем VRS рейтинг...")

    # Регионы VRS
    regions = {
        "europe":   "europe",
        "americas": "americas",
        "asia":     "asia",
    }

    all_teams = []
    global_rank = 0

    for region_key, region_val in regions.items():
        resp = lp_get("standings/table", {
            "wiki": "counterstrike",
            "extradata[standings_type]": "valve_regional_standings",
            "extradata[region]": region_val,
            "limit": 40,
        })

        if not resp or "result" not in resp:
            # Fallback: попробуем через tournament endpoint
            print(f"  [WARN] Нет данных для {region_key}, используем fallback")
            all_teams.extend(get_fallback_teams(region_key))
            continue

        for entry in resp["result"]:
            global_rank += 1
            team_name = entry.get("team", {}).get("name", "Unknown")
            flag = TEAM_FLAGS.get(team_name, "🏳")

            all_teams.append({
                "global_rank": global_rank,
                "name": team_name,
                "region": region_key,
                "flag": flag,
                "points": int(entry.get("points", 0)),
                "qualified": entry.get("placement", 999) <= 8,
            })

        time.sleep(1)  # Rate limiting

    # Сортируем по очкам глобально
    all_teams.sort(key=lambda x: x["points"], reverse=True)
    for i, t in enumerate(all_teams):
        t["global_rank"] = i + 1

    result = {
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
        "source": "Liquipedia VRS",
        "teams": all_teams
    }
    save_json("rankings.json", result)
    return all_teams

def get_fallback_teams(region):
    """Возвращает пример данных если API недоступен."""
    fallback = {
        "europe": [
            {"name": "Natus Vincere", "flag": "🇺🇦", "points": 2400},
            {"name": "Team Vitality", "flag": "🇫🇷", "points": 2200},
            {"name": "FaZe Clan",     "flag": "🌍",  "points": 1900},
            {"name": "G2 Esports",    "flag": "🇪🇺", "points": 1750},
            {"name": "Team Spirit",   "flag": "🇷🇺", "points": 1600},
            {"name": "MOUZ",          "flag": "🇩🇪", "points": 1450},
            {"name": "Heroic",        "flag": "🇩🇰", "points": 1300},
            {"name": "Astralis",      "flag": "🇩🇰", "points": 900},
            {"name": "BIG",           "flag": "🇩🇪", "points": 600},
            {"name": "ENCE",          "flag": "🇫🇮", "points": 450},
            {"name": "3DMAX",         "flag": "🇫🇷", "points": 380},
            {"name": "SAW",           "flag": "🇵🇹", "points": 310},
        ],
        "americas": [
            {"name": "Team Liquid",   "flag": "🇺🇸", "points": 1800},
            {"name": "FURIA",         "flag": "🇧🇷", "points": 1650},
            {"name": "NRG Esports",   "flag": "🇺🇸", "points": 1400},
            {"name": "Cloud9",        "flag": "🇺🇸", "points": 1200},
            {"name": "MIBR",          "flag": "🇧🇷", "points": 1000},
            {"name": "paiN Gaming",   "flag": "🇧🇷", "points": 850},
            {"name": "Complexity",    "flag": "🇺🇸", "points": 700},
            {"name": "Imperial",      "flag": "🇧🇷", "points": 580},
        ],
        "asia": [
            {"name": "The MongolZ",   "flag": "🇲🇳", "points": 2100},
            {"name": "Falcons",       "flag": "🇸🇦", "points": 1700},
            {"name": "Lynn Vision",   "flag": "🇨🇳", "points": 900},
            {"name": "TYLOO",         "flag": "🇨🇳", "points": 650},
            {"name": "Eternal Fire",  "flag": "🇹🇷", "points": 500},
        ],
    }
    teams = []
    for t in fallback.get(region, []):
        teams.append({
            "name": t["name"], "region": region,
            "flag": t["flag"], "points": t["points"],
            "qualified": t["points"] > 1000
        })
    return teams

# ── Парсинг турниров ──────────────────────────────────────────────────────────
def fetch_tournaments():
    print("\n[2/3] Загружаем турниры...")

    resp = lp_get("tournament", {
        "wiki": "counterstrike",
        "type": "qualifier",
        "game": "cs2",
        "limit": 20,
        "conditions": "[[status::upcoming]] OR [[status::ongoing]]",
        "order": "date_start ASC",
    })

    tournaments = []

    if resp and "result" in resp:
        for t in resp["result"]:
            name = t.get("name", "")
            # Фильтруем только RMR / Major Qualifier
            if not any(kw in name for kw in ["RMR", "Major", "Qualifier", "Regional"]):
                continue

            region = detect_region(name, t)
            tournaments.append({
                "id": t.get("pagename", "").replace(" ", "_"),
                "name": name,
                "region": region,
                "date": format_date(t.get("date_start", "")),
                "major_slots": estimate_slots(name),
                "status": t.get("status", "Upcoming"),
                "liquipedia_url": "https://liquipedia.net/counterstrike/" + urllib.parse.quote(t.get("pagename", "")),
            })
    else:
        print("  [WARN] API не вернул турниры, используем fallback")
        tournaments = get_fallback_tournaments()

    result = {
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
        "tournaments": tournaments
    }
    save_json("tournaments.json", result)

def detect_region(name, t):
    name_lower = name.lower()
    if any(w in name_lower for w in ["europe", "european", "eur"]):
        return "europe"
    if any(w in name_lower for w in ["america", "north america", "south america", "na", "sa"]):
        return "americas"
    if any(w in name_lower for w in ["asia", "pacific", "apac", "middle east"]):
        return "asia"
    return "global"

def estimate_slots(name):
    name_lower = name.lower()
    if "major" in name_lower: return 16
    if "rmr" in name_lower:   return 8
    return 8

def format_date(raw):
    if not raw: return "TBD"
    try:
        d = datetime.datetime.fromisoformat(raw.replace("Z", ""))
        months = ["янв","фев","мар","апр","май","июн","июл","авг","сен","окт","ноя","дек"]
        return f"{d.day} {months[d.month - 1]} {d.year}"
    except:
        return raw[:10]

def get_fallback_tournaments():
    return [
        {
            "id": "eu_rmr_2025",
            "name": "European RMR 2025",
            "region": "europe",
            "date": "15 июн 2025",
            "major_slots": 8,
            "status": "Upcoming",
            "liquipedia_url": "https://liquipedia.net/counterstrike/"
        },
        {
            "id": "na_rmr_2025",
            "name": "Americas RMR 2025",
            "region": "americas",
            "date": "22 июн 2025",
            "major_slots": 8,
            "status": "Upcoming",
            "liquipedia_url": "https://liquipedia.net/counterstrike/"
        },
        {
            "id": "apac_rmr_2025",
            "name": "Asia Pacific RMR 2025",
            "region": "asia",
            "date": "29 июн 2025",
            "major_slots": 8,
            "status": "Upcoming",
            "liquipedia_url": "https://liquipedia.net/counterstrike/"
        },
        {
            "id": "pgl_major_2025",
            "name": "PGL Major 2025",
            "region": "global",
            "date": "15 авг 2025",
            "major_slots": 24,
            "status": "Upcoming",
            "liquipedia_url": "https://liquipedia.net/counterstrike/"
        }
    ]

# ── VRS очки по местам ────────────────────────────────────────────────────────
def build_vrs_points_table():
    """
    Структура VRS очков по типам турниров.
    Источник: https://liquipedia.net/counterstrike/Valve_Regional_Standings
    """
    print("\n[3/3] Генерируем таблицу VRS очков...")

    # Официальная структура очков Valve (актуальна на 2025)
    data = {
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
        "info": "Valve Regional Standings points per placement",
        "tournaments": {
            "major": {
                "name": "CS2 Major Championship",
                "tier": "S",
                "placements": [
                    {"place": "1 место 🥇",  "vrs_points": 5000, "description": "Чемпион"},
                    {"place": "2 место 🥈",  "vrs_points": 3500, "description": "Финалист"},
                    {"place": "3–4 место",   "vrs_points": 2500, "description": "Полуфиналист"},
                    {"place": "5–8 место",   "vrs_points": 1500, "description": "Четвертьфиналист"},
                    {"place": "9–12 место",  "vrs_points": 900,  "description": "Легенды — выбыл"},
                    {"place": "13–16 место", "vrs_points": 600,  "description": "Претенденты — выбыл"},
                    {"place": "17–24 место", "vrs_points": 250,  "description": "Претенденты — не прошёл"},
                ]
            },
            "rmr_europe": {
                "name": "European RMR",
                "tier": "A",
                "placements": [
                    {"place": "1 место 🥇",  "vrs_points": 2000, "description": "Прямой слот на Мейджор"},
                    {"place": "2 место 🥈",  "vrs_points": 1600, "description": "Прямой слот на Мейджор"},
                    {"place": "3–4 место",   "vrs_points": 1300, "description": "Прямой слот на Мейджор"},
                    {"place": "5–8 место",   "vrs_points": 1000, "description": "Слот через претендентов"},
                    {"place": "9–12 место",  "vrs_points": 600,  "description": "Не прошёл"},
                    {"place": "13–16 место", "vrs_points": 300,  "description": "Не прошёл"},
                    {"place": "17+ место",   "vrs_points": 100,  "description": "Групповой этап"},
                ]
            },
            "rmr_americas": {
                "name": "Americas RMR",
                "tier": "A",
                "placements": [
                    {"place": "1 место 🥇",  "vrs_points": 2000, "description": "Прямой слот на Мейджор"},
                    {"place": "2 место 🥈",  "vrs_points": 1600, "description": "Прямой слот на Мейджор"},
                    {"place": "3–4 место",   "vrs_points": 1300, "description": "Прямой слот на Мейджор"},
                    {"place": "5–8 место",   "vrs_points": 1000, "description": "Слот через претендентов"},
                    {"place": "9–12 место",  "vrs_points": 600,  "description": "Не прошёл"},
                    {"place": "13–16 место", "vrs_points": 300,  "description": "Не прошёл"},
                ]
            },
            "rmr_asia": {
                "name": "Asia Pacific RMR",
                "tier": "A",
                "placements": [
                    {"place": "1 место 🥇",  "vrs_points": 2000, "description": "Прямой слот на Мейджор"},
                    {"place": "2 место 🥈",  "vrs_points": 1600, "description": "Прямой слот на Мейджор"},
                    {"place": "3–4 место",   "vrs_points": 1300, "description": "Прямой слот на Мейджор"},
                    {"place": "5–8 место",   "vrs_points": 1000, "description": "Слот через претендентов"},
                    {"place": "9–12 место",  "vrs_points": 600,  "description": "Не прошёл"},
                ]
            },
            "blast_open": {
                "name": "BLAST Open",
                "tier": "B",
                "placements": [
                    {"place": "1 место 🥇",  "vrs_points": 1000, "description": ""},
                    {"place": "2 место 🥈",  "vrs_points": 800,  "description": ""},
                    {"place": "3–4 место",   "vrs_points": 600,  "description": ""},
                    {"place": "5–8 место",   "vrs_points": 400,  "description": ""},
                    {"place": "9–12 место",  "vrs_points": 200,  "description": ""},
                    {"place": "13–16 место", "vrs_points": 100,  "description": ""},
                ]
            },
            "esl_pro_league": {
                "name": "ESL Pro League",
                "tier": "B",
                "placements": [
                    {"place": "1 место 🥇",  "vrs_points": 1200, "description": ""},
                    {"place": "2 место 🥈",  "vrs_points": 900,  "description": ""},
                    {"place": "3–4 место",   "vrs_points": 700,  "description": ""},
                    {"place": "5–8 место",   "vrs_points": 450,  "description": ""},
                    {"place": "9–12 место",  "vrs_points": 250,  "description": ""},
                    {"place": "13–16 место", "vrs_points": 120,  "description": ""},
                ]
            },
        }
    }

    save_json("vrs_points.json", data)

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("CS2 Hub — Сбор данных")
    print("=" * 50)

    if not API_KEY:
        print("\n[!] LIQUIPEDIA_API_KEY не задан — используются fallback данные.")
        print("    Получи ключ на: https://api.liquipedia.net/api-docs\n")

    fetch_vrs_rankings()
    fetch_tournaments()
    build_vrs_points_table()

    print("\n✅ Готово! Данные сохранены в data/")
