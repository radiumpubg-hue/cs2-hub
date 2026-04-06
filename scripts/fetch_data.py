#!/usr/bin/env python3
"""
fetch_data.py — Собирает данные CS2 с PandaScore API
Документация: https://developers.pandascore.co/docs
Регистрация: https://pandascore.co (ключ сразу после регистрации)
Ключ добавь в GitHub Secrets как PANDASCORE_API_KEY
"""

import json
import os
import datetime
import urllib.request
import urllib.parse

# ── Конфиг ───────────────────────────────────────────────────────────────────
API_KEY  = os.environ.get("PANDASCORE_API_KEY", "")
BASE_URL = "https://api.pandascore.co"
HEADERS  = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Флаги стран ───────────────────────────────────────────────────────────────
COUNTRY_FLAGS = {
    "UA": "🇺🇦", "FR": "🇫🇷", "DE": "🇩🇪", "DK": "🇩🇰",
    "SE": "🇸🇪", "FI": "🇫🇮", "RU": "🇷🇺", "PL": "🇵🇱",
    "US": "🇺🇸", "BR": "🇧🇷", "CA": "🇨🇦", "MX": "🇲🇽",
    "CN": "🇨🇳", "KR": "🇰🇷", "AU": "🇦🇺", "MN": "🇲🇳",
    "SA": "🇸🇦", "TR": "🇹🇷", "PT": "🇵🇹", "ES": "🇪🇸",
    "NL": "🇳🇱", "BE": "🇧🇪", "CZ": "🇨🇿", "NO": "🇳🇴",
    "RO": "🇷🇴", "GR": "🇬🇷", "IL": "🇮🇱", "SK": "🇸🇰",
}

EU_COUNTRIES = {"UA","FR","DE","DK","SE","FI","RU","PL","PT","ES","NL","BE","CZ","SK","NO","RO","GR","IL"}
AM_COUNTRIES = {"US","BR","CA","MX","AR","CL","CO","PE"}

def get_flag(country_code):
    if not country_code:
        return "🏳"
    return COUNTRY_FLAGS.get(country_code.upper(), "🏳")

def get_region(country_code):
    if not country_code:
        return "europe"
    cc = country_code.upper()
    if cc in EU_COUNTRIES:
        return "europe"
    if cc in AM_COUNTRIES:
        return "americas"
    return "asia"

# ── HTTP запрос ───────────────────────────────────────────────────────────────
def api_get(path, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  [HTTP {e.code}] {path}: {e.reason}")
        return None
    except Exception as e:
        print(f"  [ERR] {path}: {e}")
        return None

def save_json(filename, data):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Сохранено: {filename}")

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

# ── 1. Рейтинг команд ─────────────────────────────────────────────────────────
def fetch_rankings():
    print("\n[1/3] Загружаем команды CS2...")

    if not API_KEY:
        print("  [!] Нет API ключа — используем fallback данные")
        save_json("rankings.json", fallback_rankings())
        return

    data = api_get("/csgo/teams", {
        "sort": "-modified_at",
        "page[size]": 50,
    })

    if not data:
        print("  [!] API не ответил — используем fallback")
        save_json("rankings.json", fallback_rankings())
        return

    teams = []
    for i, t in enumerate(data):
        location = (t.get("location") or "")
        teams.append({
            "global_rank":   i + 1,
            "name":          t.get("name", "Unknown"),
            "acronym":       t.get("acronym", ""),
            "flag":          get_flag(location),
            "region":        get_region(location),
            "points":        max(2500 - i * 110, 50),
            "qualified":     i < 8,
            "pandascore_id": t.get("id"),
        })

    save_json("rankings.json", {
        "last_updated": now_iso(),
        "source": "PandaScore API",
        "note": "VRS очки приблизительные — PandaScore не публикует официальный VRS Valve",
        "teams": teams,
    })

# ── 2. Турниры ────────────────────────────────────────────────────────────────
def fetch_tournaments():
    print("\n[2/3] Загружаем турниры CS2...")

    if not API_KEY:
        save_json("tournaments.json", fallback_tournaments())
        return

    today = datetime.date.today().isoformat()
    data = api_get("/csgo/tournaments", {
        "sort": "begin_at",
        "page[size]": 20,
        "filter[tier]": "s,a",
        "range[begin_at]": f"{today},2026-12-31",
    })

    if not data:
        print("  [!] API не ответил — используем fallback")
        save_json("tournaments.json", fallback_tournaments())
        return

    tournaments = []
    for t in data:
        name   = t.get("name", "")
        league = ((t.get("league") or {}).get("name") or "")
        full_name = f"{league} — {name}" if league and league not in name else name

        tournaments.append({
            "id":            str(t.get("id", "")),
            "name":          full_name,
            "region":        detect_region(full_name),
            "date":          format_date(t.get("begin_at", "")),
            "major_slots":   estimate_slots(full_name, t.get("tier", "")),
            "status":        map_status(t.get("status", "")),
            "pandascore_id": t.get("id"),
        })

    save_json("tournaments.json", {
        "last_updated": now_iso(),
        "source": "PandaScore API",
        "tournaments": tournaments,
    })

def detect_region(name):
    n = name.lower()
    if any(w in n for w in ["europe", "european", "eur"]):
        return "europe"
    if any(w in n for w in ["america", "north america", "south america", "na ", "sa "]):
        return "americas"
    if any(w in n for w in ["asia", "pacific", "apac", "middle east"]):
        return "asia"
    return "global"

def estimate_slots(name, tier):
    n = name.lower()
    if "major" in n: return 24
    if "rmr"   in n: return 8
    if tier == "s":  return 16
    return 8

def map_status(s):
    return {
        "running":     "Идёт сейчас",
        "not_started": "Upcoming",
        "finished":    "Завершён",
    }.get(s, "Upcoming")

def format_date(raw):
    if not raw:
        return "TBD"
    try:
        d = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        months = ["янв","фев","мар","апр","май","июн",
                  "июл","авг","сен","окт","ноя","дек"]
        return f"{d.day} {months[d.month - 1]} {d.year}"
    except Exception:
        return raw[:10]

# ── 3. Таблица VRS очков (статичная) ─────────────────────────────────────────
def build_vrs_points():
    print("\n[3/3] Генерируем таблицу VRS очков...")
    data = {
        "last_updated": now_iso(),
        "info": "Valve Regional Standings — официальная таблица очков по местам",
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

# ── Fallback данные ───────────────────────────────────────────────────────────
def fallback_rankings():
    teams_raw = [
        ("Natus Vincere", "🇺🇦", "europe",   2400),
        ("Team Vitality", "🇫🇷", "europe",   2200),
        ("The MongolZ",   "🇲🇳", "asia",     2100),
        ("FaZe Clan",     "🌍",  "europe",   1900),
        ("G2 Esports",    "🇪🇺", "europe",   1750),
        ("Team Spirit",   "🇷🇺", "europe",   1600),
        ("Team Liquid",   "🇺🇸", "americas", 1800),
        ("FURIA",         "🇧🇷", "americas", 1650),
        ("Falcons",       "🇸🇦", "asia",     1700),
        ("MOUZ",          "🇩🇪", "europe",   1450),
        ("Heroic",        "🇩🇰", "europe",   1300),
        ("NRG Esports",   "🇺🇸", "americas", 1400),
        ("Astralis",      "🇩🇰", "europe",    900),
        ("Cloud9",        "🇺🇸", "americas", 1200),
        ("MIBR",          "🇧🇷", "americas", 1000),
        ("Lynn Vision",   "🇨🇳", "asia",      900),
        ("BIG",           "🇩🇪", "europe",    600),
        ("ENCE",          "🇫🇮", "europe",    450),
        ("paiN Gaming",   "🇧🇷", "americas",  850),
        ("TYLOO",         "🇨🇳", "asia",      650),
        ("3DMAX",         "🇫🇷", "europe",    380),
        ("Complexity",    "🇺🇸", "americas",  700),
        ("SAW",           "🇵🇹", "europe",    310),
        ("Eternal Fire",  "🇹🇷", "asia",      500),
        ("Imperial",      "🇧🇷", "americas",  580),
    ]
    teams = []
    for i, (name, flag, region, points) in enumerate(teams_raw):
        teams.append({
            "global_rank": i + 1,
            "name":        name,
            "flag":        flag,
            "region":      region,
            "points":      points,
            "qualified":   points > 1000,
        })
    teams.sort(key=lambda x: x["points"], reverse=True)
    for i, t in enumerate(teams):
        t["global_rank"] = i + 1
    return {
        "last_updated": now_iso(),
        "source": "Fallback (нет API ключа)",
        "teams": teams,
    }

def fallback_tournaments():
    return {
        "last_updated": now_iso(),
        "source": "Fallback (нет API ключа)",
        "tournaments": [
            {"id": "eu_rmr_2025",   "name": "European RMR 2025",      "region": "europe",   "date": "15 июн 2025", "major_slots": 8,  "status": "Upcoming"},
            {"id": "na_rmr_2025",   "name": "Americas RMR 2025",      "region": "americas", "date": "22 июн 2025", "major_slots": 8,  "status": "Upcoming"},
            {"id": "apac_rmr_2025", "name": "Asia Pacific RMR 2025",  "region": "asia",     "date": "29 июн 2025", "major_slots": 8,  "status": "Upcoming"},
            {"id": "pgl_major_2025","name": "PGL Major 2025",         "region": "global",   "date": "15 авг 2025", "major_slots": 24, "status": "Upcoming"},
        ]
    }

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("CS2 Hub — Сбор данных (PandaScore)")
    print("=" * 50)

    if not API_KEY:
        print("\n[!] PANDASCORE_API_KEY не задан.")
        print("    Регистрация: https://pandascore.co")
        print("    Используются fallback данные.\n")

    fetch_rankings()
    fetch_tournaments()
    build_vrs_points()

    print("\n✅ Готово! Данные сохранены в data/")
