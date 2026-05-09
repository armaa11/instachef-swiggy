import json
import os
import difflib
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()

def load_ingredients() -> List[Dict]:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "ingredients.json")
    with open(path, "r") as f:
        return json.load(f)

logger.info("normalizer.loading_db", status="started")
ingredients_db = load_ingredients()

# ─── LIGHTWEIGHT FUZZY MATCHING ──────────────────────────────────────────────
# We use standard lib difflib instead of heavy ML models (FAISS/SentenceTransformers)
# to keep the pipeline extremely fast and lightweight.

# Pre-build a flat dictionary of all searchable names to their db items
search_index: Dict[str, Dict] = {}
for db_ing in ingredients_db:
    search_index[db_ing["canonical"]] = db_ing
    for variant in db_ing.get("variants", []):
        search_index[variant.lower()] = db_ing

all_search_terms = list(search_index.keys())

def _find_ingredient_match(raw_name: str, canonical_name: str) -> Dict | None:
    """
    Find the best matching ingredient using lightweight fuzzy string matching.
    """
    raw = raw_name.lower().strip()
    canon = canonical_name.lower().strip()

    # Strategy 1: Exact canonical match (O(1) fast path)
    if canon in search_index:
        return search_index[canon]
    if raw in search_index:
        return search_index[raw]

    # Strategy 2: Fuzzy matching
    queries = [canon]
    if raw and raw != canon:
        queries.append(raw)
        
    for query in queries:
        matches = difflib.get_close_matches(query, all_search_terms, n=1, cutoff=0.75)
        if matches:
            best_match_key = matches[0]
            return search_index[best_match_key]
            
    return None

def normalize_ingredients(recipe_ingredients: List[Any], serving_size: int) -> List[Dict]:
    """
    Normalize extracted ingredients into searchable terms with gram quantities.
    Uses lightweight fuzzy matching for accuracy without heavy dependencies.
    """
    normalized = []
    match_count = 0
    semantic_count = 0
    unmatched_count = 0

    for ing in recipe_ingredients:
        raw = ing.raw_name.lower()
        canon = ing.canonical_name.lower()

        match = _find_ingredient_match(raw, canon)

        if match:
            search_term = match["search_term"]
            match_count += 1
            if match["canonical"] != canon:
                semantic_count += 1
        else:
            # No match found — fallback to canonical name as search term
            search_term = canon
            unmatched_count += 1

        # ─── Unit conversion to grams ─────────────────────────────
        q = ing.quantity
        unit = ing.unit.lower().strip()
        grams = None

        if unit in ["g", "grams", "gram", "ml", "milliliters"]:
            grams = q
        elif unit in ["kg", "kilogram", "kilograms"]:
            grams = q * 1000
        elif unit in ["l", "litre", "liter", "litres", "liters"]:
            grams = q * 1000
        elif unit in ["tbsp", "tablespoon", "tablespoons"]:
            grams = q * 15
        elif unit in ["tsp", "teaspoon", "teaspoons"]:
            grams = q * 5
        elif unit in ["cups", "cup"]:
            grams = q * 200
        elif unit in ["pinch", "pinches"]:
            grams = q * 1
        elif unit in ["pieces", "piece", "nos", "number", "whole"]:
            # For whole items (onion, tomato etc.), estimate grams
            PIECE_WEIGHTS = {
                "onion": 150, "tomato": 120, "potato": 180,
                "green chilli": 5, "garlic": 5, "ginger": 10,
                "lemon": 50, "lime": 40, "egg": 60,
                "banana": 120, "apple": 180, "carrot": 80,
                "bay leaf": 1, "cardamom": 1, "cloves": 1,
                "cinnamon": 3,
            }
            weight = PIECE_WEIGHTS.get(canon, 100)
            grams = q * weight
        else:
            # Unknown unit — estimate from DB if possible
            if match and match.get("default_grams_per_tsp"):
                grams = q * match["default_grams_per_tsp"]

        normalized.append({
            "original_ingredient_id": ing.id,
            "search_term": search_term,
            "quantity_grams": grams,
            "quantity_display": f"{q} {unit}",
            "unit_display": unit,
            "ingredient_name": ing.canonical_name,
            "is_optional": getattr(ing, "is_optional", False),
            "category": getattr(ing, "category", "other"),
            "matched_in_db": match is not None,
        })

    logger.info("normalizer.complete",
                total=len(normalized),
                db_matched=match_count,
                fuzzy_rescues=semantic_count,
                unmatched=unmatched_count)

    return normalized
