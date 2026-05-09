"""
Validation gates for the agentic pipeline.
Layer 1: Schema validation (Pydantic — handled in understander.py)
Layer 2: Semantic validation (rule-based — this file)
Layer 3: Cart integrity validation (this file)
"""
import structlog
from typing import List, Dict, Any, Tuple
from collections import Counter

logger = structlog.get_logger()


# ─── Recipe Validation Gate ───────────────────────────────────────────

class RecipeValidationResult:
    def __init__(self):
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.repairs: List[str] = []
        self.passed: bool = True

    def add_issue(self, issue: str):
        self.issues.append(issue)
        self.passed = False

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def add_repair(self, repair: str):
        self.repairs.append(repair)

    def to_dict(self):
        return {
            "passed": self.passed,
            "issues": self.issues,
            "warnings": self.warnings,
            "repairs": self.repairs,
        }


def validate_recipe(recipe) -> Tuple[Any, RecipeValidationResult]:
    """
    Validate and auto-repair a parsed recipe.
    Returns (possibly_repaired_recipe, validation_result).
    """
    result = RecipeValidationResult()

    # 1. Minimum ingredient check
    if len(recipe.ingredients) < 2:
        result.add_issue("TOO_FEW_INGREDIENTS: Recipe has fewer than 2 ingredients")

    # 2. Serving size sanity
    if recipe.serving_size < 1 or recipe.serving_size > 50:
        result.add_warning(f"UNUSUAL_SERVING_SIZE: {recipe.serving_size}")
        recipe.serving_size = max(1, min(recipe.serving_size, 50))
        result.add_repair(f"Capped serving size to {recipe.serving_size}")

    # 3. Duplicate ingredient detection & merge
    name_counts = Counter(i.canonical_name.lower().strip() for i in recipe.ingredients)
    duplicates = {name: count for name, count in name_counts.items() if count > 1}
    if duplicates:
        result.add_warning(f"DUPLICATE_INGREDIENTS: {list(duplicates.keys())}")
        # Auto-merge: keep first occurrence, sum quantities
        seen = {}
        merged_ingredients = []
        for ing in recipe.ingredients:
            key = ing.canonical_name.lower().strip()
            if key in seen:
                # Sum the quantity into the first occurrence
                seen[key].quantity += ing.quantity
                result.add_repair(f"Merged duplicate '{key}': combined quantity = {seen[key].quantity} {seen[key].unit}")
            else:
                seen[key] = ing
                merged_ingredients.append(ing)
        recipe.ingredients = merged_ingredients

    # 4. Quantity sanity per ingredient
    QUANTITY_LIMITS = {
        "grams": 10000, "g": 10000, "kg": 10,
        "ml": 5000, "litre": 5, "liter": 5, "l": 5,
        "cups": 20, "cup": 20,
        "tbsp": 50, "tablespoon": 50,
        "tsp": 30, "teaspoon": 30,
        "pieces": 50, "piece": 50, "nos": 50,
        "pinch": 10,
    }
    for ing in recipe.ingredients:
        unit_lower = ing.unit.lower().strip()
        limit = QUANTITY_LIMITS.get(unit_lower, 100)
        if ing.quantity > limit:
            result.add_warning(
                f"EXCESSIVE_QUANTITY: {ing.canonical_name} = {ing.quantity} {ing.unit} (limit: {limit})"
            )
            # Auto-repair: cap to a reasonable fraction
            old_qty = ing.quantity
            ing.quantity = min(ing.quantity, limit * 0.5)
            result.add_repair(f"Capped {ing.canonical_name} from {old_qty} to {ing.quantity} {ing.unit}")

    # 5. Confidence check
    if recipe.confidence_score < 0.5:
        result.add_issue(f"LOW_CONFIDENCE: {recipe.confidence_score}")

    # 6. Missing core ingredient heuristic
    recipe_name_lower = recipe.recipe_name.lower()
    ingredient_names = " ".join(i.canonical_name.lower() for i in recipe.ingredients)

    core_checks = [
        ("chicken", ["chicken", "murgh"]),
        ("paneer", ["paneer", "cottage cheese"]),
        ("dal", ["dal", "lentil", "daal"]),
        ("biryani", ["rice", "basmati"]),
        ("rice", ["rice"]),
        ("fish", ["fish", "machli", "meen"]),
        ("egg", ["egg", "anda"]),
        ("mutton", ["mutton", "lamb", "goat"]),
    ]
    for keyword, required_any in core_checks:
        if keyword in recipe_name_lower:
            if not any(req in ingredient_names for req in required_any):
                result.add_warning(f"MISSING_CORE_INGREDIENT: Recipe '{recipe.recipe_name}' may be missing {keyword}")

    logger.info("recipe.validated",
                passed=result.passed,
                issue_count=len(result.issues),
                warning_count=len(result.warnings),
                repair_count=len(result.repairs))

    return recipe, result


# ─── Cart Validation Gate ─────────────────────────────────────────────

class CartValidationResult:
    def __init__(self):
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.passed: bool = True

    def add_issue(self, issue: str):
        self.issues.append(issue)
        self.passed = False

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def to_dict(self):
        return {
            "passed": self.passed,
            "issues": self.issues,
            "warnings": self.warnings,
        }


def validate_cart(cart_items: List[Dict], normalized_ingredients: List[Dict]) -> CartValidationResult:
    """
    Validate the final cart before proposing to user.
    """
    result = CartValidationResult()

    # 1. Duplicate spin_id check
    spin_ids = [i["spin_id"] for i in cart_items if i.get("spin_id")]
    if len(spin_ids) != len(set(spin_ids)):
        dupes = [sid for sid, count in Counter(spin_ids).items() if count > 1]
        result.add_warning(f"DUPLICATE_PRODUCTS: {dupes}")

    # 2. Price sanity
    for item in cart_items:
        if item.get("spin_id") and item.get("product_price", 0) <= 0:
            result.add_warning(f"ZERO_PRICE: {item['ingredient_name']}")

    # 3. Total sanity
    total = sum(i.get("product_price", 0) for i in cart_items if i.get("spin_id"))
    if total > 5000:
        result.add_warning(f"HIGH_TOTAL: ₹{total} — unusually expensive for a single recipe")
    if total > 0 and total < 99:
        result.add_warning(f"BELOW_MINIMUM: ₹{total} — Instamart requires minimum ₹99 order")

    # 4. Coverage check
    needed = set(i["ingredient_name"].lower() for i in normalized_ingredients)
    covered = set(i["ingredient_name"].lower() for i in cart_items if i.get("spin_id"))
    flagged = set(i["ingredient_name"].lower() for i in cart_items if i.get("pantry_likely"))
    uncovered = needed - covered - flagged
    if uncovered:
        result.add_warning(f"UNCOVERED_INGREDIENTS: {uncovered}")

    # 5. Item count sanity
    if len(cart_items) == 0:
        result.add_issue("EMPTY_CART: No items in cart")

    logger.info("cart.validated",
                passed=result.passed,
                issue_count=len(result.issues),
                warning_count=len(result.warnings),
                total=total,
                item_count=len(cart_items))

    return result
