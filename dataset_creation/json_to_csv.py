import os
import json
import pandas as pd
from typing import Any, Dict, Optional
from scraper import STYLES


def count_styles():
    total_unique_ids = 0
    total_rows = 0

    for style in STYLES:
        files = [f for f in os.listdir("data/scrapped_data") if style[0] in f]
        unique_ids = set()
        for file in files:
            with open(f"data/scrapped_data/{file}", "r") as f:
                data = json.load(f)
                total_rows += len(data)
                wine_ids = set([el["vintage"]["id"] for el in data])
                unique_ids.update(wine_ids)
        total_unique_ids += len(unique_ids)
        print(f"{style}: {len(unique_ids)}")
    print(f"Total vintages: {total_unique_ids}")
    print(f"Total rows: {total_rows }")


def _get(d: dict, path: str, default=None):
    """Safe getter: path like 'vintage.wine.region.country.code'."""
    cur = d
    for p in path.split('.'):
        if cur is None:
            return default
        # handle list index like 'prices[0]'
        if '[' in p and p.endswith(']'):
            name, idx = p[:-1].split('[')
            cur = cur.get(name) if isinstance(cur, dict) else None
            try:
                cur = cur[int(idx)] if isinstance(cur, list) else None
            except (ValueError, IndexError, TypeError):
                return default
        else:
            cur = cur.get(p) if isinstance(cur, dict) else None
    return default if cur is None else cur


def extract_top_flavors(el: dict, TOP_N: int = 5) -> str:
    def _get(d, path, default=None):
        cur = d
        for p in path.split('.'):
            if cur is None:
                return default
            cur = cur.get(p) if isinstance(cur, dict) else default
        return default if cur is None else cur

    flavor_groups = _get(el, "vintage.wine.taste.flavor", []) or []
    items = []
    for g in flavor_groups:
        for k in g.get("primary_keywords", []) or []:
            name = k.get("name")
            cnt = k.get("count", 0) or 0
            if name:
                items.append((name, cnt))
    # fallback to secondary if no primary found
    if not items:
        for g in flavor_groups:
            for k in g.get("secondary_keywords", []) or []:
                name = k.get("name")
                cnt = k.get("count", 0) or 0
                if name:
                    items.append((name, cnt))

    # aggregate counts of same flavor name across groups
    from collections import Counter
    agg = Counter()
    for name, cnt in items:
        agg[name] += cnt

    top = [name for name, _ in agg.most_common(TOP_N)]
    return "; ".join(top)

def extract_wine_row(el: dict, wine_type: str) -> dict:
    def _get(d, path, default=None):
        cur = d
        for p in path.split('.'):
            if cur is None:
                return default
            cur = cur.get(p) if isinstance(cur, dict) else default
        return default if cur is None else cur

    def _pick_price(el: dict):
        prices = _get(el, "prices", []) or []
        if prices:
            valid = [p for p in prices if isinstance(p, dict) and _get(p, "amount") is not None]
            if valid:
                pmin = min(valid, key=lambda p: _get(p, "amount"))
                return _get(pmin, "amount"), _get(pmin, "currency.code")
        # fallback to single price block
        return _get(el, "price.amount"), _get(el, "price.currency.code")

    # ids and names
    wine_id     = _get(el, "vintage.wine.id")
    vintage_id  = _get(el, "vintage.id")
    region_id = _get(el, "vintage.wine.region.id")
    region_name = _get(el, "vintage.wine.region.name")
    region_name = _get(el, "vintage.wine.region.name")
    country_name = _get(el, "vintage.wine.region.country.name")
    vintage_name= _get(el, "vintage.name")
    wine_name   = _get(el, "vintage.wine.name")
    style_description = _get(el, "vintage.wine.style.description")
    varietal_name =  _get(el, "vintage.wine.style.varietal_name")
    style_name =  _get(el, "vintage.wine.style.name")

    # grapes
    used_grapes = "; ".join([grape['name'] for grape in _get(el, "vintage.wine.region.country.most_used_grapes", default=[])])

    # go well with
    relevant_food = "; ".join([dish['name'] for dish in _get(el, "vintage.wine.style.food", default=[])])

    # top flavors
    top_flavors = extract_top_flavors(el, TOP_N=10)
    
    # year (normalize NV to None)
    year_val = _get(el, "vintage.year")
    try:
        year = int(str(year_val)) if str(year_val).isdigit() else None
    except:
        year = None

    # ratings
    rating_avg   = _get(el, "vintage.statistics.ratings_average")
    rating_count = _get(el, "vintage.statistics.ratings_count")

    # price (single number) + currency
    price, currency_code = _pick_price(el)

    # taste metrics
    acidity   = _get(el, "vintage.wine.taste.structure.acidity")
    intensity = _get(el, "vintage.wine.taste.structure.intensity")
    sweetness = _get(el, "vintage.wine.taste.structure.sweetness")
    tannin    = _get(el, "vintage.wine.taste.structure.tannin")
    fizziness = _get(el, "vintage.wine.taste.structure.fizziness")

    # vivino link (stable pattern)
    seo = "-".join(_get(el, "vintage.seo_name").split("-")[:-1])
    vivino_url = f"https://www.vivino.com/US/en/{seo}/w/{wine_id}" if seo and vintage_id else None

    
    return {
        "wine_id": wine_id,
        "vintage_id": vintage_id,
        "wine_type": wine_type,
        "region_id": region_id,
        "region_name": region_name,
        "country_name": country_name,
        "used_grapes": used_grapes,
        "relevant_food": relevant_food,
        "top_flavors": top_flavors,
        "vintage_name": vintage_name,
        "wine_name": wine_name,
        "varietal_name": varietal_name,
        "style_name": style_name,
        "year": year,
        "price": price,                 # one number
        "currency_code": currency_code, # so price is meaningful
        "acidity": acidity,
        "intensity": intensity,
        "sweetness": sweetness,
        "tannin": tannin,
        "fizziness": fizziness,
        "rating_avg": rating_avg,
        "rating_count": rating_count,
        "vivino_url": vivino_url,
        "style_description": style_description,
    }


def process_one_file(file_name: str, vintage_ids: set):
    rows = []
    with open(file_name, "r") as f:
        data = json.load(f)
        wine_type = file_name.split('_')[3]

        for el in data:
            if el["vintage"]["id"] not in vintage_ids:
                row = extract_wine_row(el, wine_type=wine_type)
                rows.append(row)
                vintage_ids.add(el["vintage"]["id"])
    return vintage_ids, rows

def process_all_files():
    vintage_ids = set()       
    rows = []
    for file in os.listdir("data/scrapped_data"):
        vintage_ids, new_rows = process_one_file(f"data/scrapped_data/{file}", vintage_ids)
        rows.extend(new_rows)

    df = pd.DataFrame(rows)
    df.to_csv("data/wines.csv", index=False, encoding="utf-8")
    df.sample(20).to_csv("data/wines_head.csv", index=False, encoding="utf-8")

if __name__ == "__main__":
    # count_styles()
    process_all_files() 