import math
import pandas as pd
import unicodedata
from collections import Counter
from typing import List, Dict, Any, Optional

import pandas as pd


def _split_semicolon(val: Any, lower: bool = True, limit: Optional[int] = None) -> List[str]:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return []
    if not isinstance(val, str):
        val = str(val)
    parts = [p.strip() for p in val.split(';') if p.strip()]
    if lower:
        parts = [p.lower() for p in parts]
    if limit is not None:
        parts = parts[:limit]
    return parts


def strip_accents(text: str) -> str:
    if not isinstance(text, str):
        return text
    # Normalize to NFKD, then drop diacritics
    text_norm = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text_norm if not unicodedata.combining(c))


def flavors_into_list(flavors: str) -> List[str]:
    return _split_semicolon(flavors)

def get_most_common_flavors(df: pd.DataFrame) -> dict:
    varietal_flavors = {}
    for varietal_name, group in df.groupby('varietal_name'):
        all_flavors = []
        for row in group.itertuples(index=False):
            all_flavors.extend(flavors_into_list(getattr(row, 'top_flavors')))
        # Count and get most common 10
        most_common = Counter(all_flavors).most_common(6)
        string_flavors = ";".join([el[0] for el in most_common])
        varietal_flavors[varietal_name] = string_flavors

    return varietal_flavors

def relevant_food_into_list(relevant_food: str) -> List[str]:
    return _split_semicolon(relevant_food)

def get_most_common_relevant_food(df: pd.DataFrame) -> dict:
    varietal_relevant_food = {}
    for varietal_name, group in df.groupby('varietal_name'):
        all_relevant_food = []
        for row in group.itertuples(index=False):
            all_relevant_food.extend(relevant_food_into_list(getattr(row, 'relevant_food')))

        most_common = Counter(all_relevant_food).most_common(3)
        string_relevant_food = ";".join([el[0] for el in most_common])
        varietal_relevant_food[varietal_name] = string_relevant_food

    return varietal_relevant_food


def varietal_name_normalisation(varietal_name: str) -> str:
    return strip_accents(varietal_name).lower().strip()

def region_and_country_normalisation(region_or_country: str) -> str:
    return strip_accents(region_or_country).lower().strip()

# ---- Tunable thresholds (picked from your stats) ----
SWEET_DRY_MAX   = 1.80   # dry  (≤ P50)
SWEET_OFF_MAX   = 2.60   # off-dry (≈ P75)
ACID_HIGH_MIN   = 3.80   # high acid (above ~P75)
TANNIN_HIGH_MIN = 3.60   # high tannin (above ~P75)
TANNIN_LOW_MAX  = 2.80   # low tannin (below ~P25)
BODY_FULL_MIN   = 4.30   # full body (≈ P75 of intensity)
FIZZ_MIN        = 3.50   # sparkling-ish

def _isna(x):
    return x is None or (isinstance(x, float) and math.isnan(x))

def taste_category(row) -> str:
    wt = str(row.get("wine_type") or "").strip().lower()
    sw = row.get("sweetness")
    ac = row.get("acidity")
    tn = row.get("tannin")
    it = row.get("intensity")
    fz = row.get("fizziness")

    # Dessert / Fortified get their own bucket
    if wt in {"dessert", "fortified"} or (not _isna(sw) and sw >= 4.0):
        return "dessert or fortified"

    # Sparkling styles (use sweetness bands if available)
    if not _isna(fz) and fz >= FIZZ_MIN or wt == "sparkling":
        if not _isna(sw):
            if sw <= SWEET_DRY_MAX:
                return "sparkling brut (dry)"
            elif sw <= SWEET_OFF_MAX:
                return "sparkling demi-sec (off-dry)"
            else:
                return "sparkling doux (sweet)"
        # Fallback by acidity for sparkling
        if not _isna(ac) and ac >= ACID_HIGH_MIN:
            return "sparkling brut (dry)"
        return "sparkling (unspecified)"

    # Red-specific tannin splits
    if wt == "red":
        if not _isna(tn):
            if tn >= TANNIN_HIGH_MIN and (_isna(sw) or sw <= 2.2):
                return "tannic & structured red"
            if tn <= TANNIN_LOW_MAX and (_isna(sw) or sw <= SWEET_OFF_MAX):
                return "soft & smooth red"
        # Fall back to body/sweetness
        if not _isna(it) and it >= BODY_FULL_MIN and (_isna(sw) or sw <= SWEET_OFF_MAX):
            return "rich & full red"
        if not _isna(sw):
            if sw <= SWEET_DRY_MAX:
                return "dry red"
            elif sw <= SWEET_OFF_MAX:
                return "off-dry red"
            else:
                return "sweet-leaning red"
        return "red (unspecified)"

    # Whites / Rosé (or anything else still)
    # Crisp & dry: high acid + dry
    if (not _isna(ac) and ac >= ACID_HIGH_MIN) and (not _isna(sw) and sw <= SWEET_DRY_MAX):
        return "crisp & dry"
    # Lush & sweet: sweetness high
    if not _isna(sw) and sw > SWEET_OFF_MAX:
        return "lush & sweet"
    # Rich & full-bodied: high intensity, not sweet
    if not _isna(it) and it >= BODY_FULL_MIN and (_isna(sw) or sw <= SWEET_OFF_MAX):
        return "rich & full-bodied"
    # Balanced / off-dry middle
    if not _isna(sw) and SWEET_DRY_MAX < sw <= SWEET_OFF_MAX:
        return "balanced (off-dry)"
    # Default fallbacks
    if not _isna(sw) and sw <= SWEET_DRY_MAX:
        return "dry & balanced"
    if not _isna(ac) and ac >= ACID_HIGH_MIN:
        return "bright & zesty"
    return "neutral or unspecified"

# ---- Usage ----
# df["taste_category"] = df.apply(taste_category, axis=1)
