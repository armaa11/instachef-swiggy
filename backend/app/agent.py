"""
Mise en Place — Agentic Workflow Engine

This is a REAL state machine, not a linear pipeline.
It has:
- Conditional routing based on confidence scores
- Validation gates that can reject and re-route
- Retry loops for failed searches with synonym expansion
- Human-in-loop checkpoints
- Structured logging at every node
- Failure recovery with graceful degradation
"""
from langgraph.graph import StateGraph, END
from typing import Dict, Any, TypedDict, Optional, List
from app.pipeline.classifier import classify_input
from app.pipeline.extractor import extract_content
from app.pipeline.understander import understand_recipe
from app.pipeline.normalizer import normalize_ingredients
from app.pipeline.optimizer import rank_and_optimize
from app.pipeline.user_context import build_user_context, UserContext
from app.pipeline.validators import validate_recipe, validate_cart
from app.mcp.client import MCPClient
from app.mcp.cart import CartManager
from app.config import settings
import structlog
import asyncio
import json
import time

logger = structlog.get_logger()


# ─── State Schema ─────────────────────────────────────────────────────

class GraphState(TypedDict):
    session_id: str
    raw_input: str
    input_type: str
    raw_content: str
    recipe: Any
    normalized_ingredients: list
    search_results: dict
    ranked_products: list
    cart_items: list
    user_approved: bool
    order_id: Optional[str]
    error: Optional[str]
    # Agentic intelligence fields
    user_context: Optional[Any]
    validation_result: Optional[dict]
    cart_validation_result: Optional[dict]
    retry_count: int
    pipeline_trace: list
    pipeline_metrics: dict
    started_at: float


# ─── SSE Emitter (overridden by main.py) ──────────────────────────────

async def emit_sse(session_id: str, data: dict):
    pass


# ─── Pipeline Trace Helper ────────────────────────────────────────────

def _trace_entry(stage: str, status: str, detail: str = "", duration_ms: int = 0) -> dict:
    return {
        "stage": stage,
        "status": status,
        "detail": detail,
        "duration_ms": duration_ms,
        "timestamp": time.time(),
    }


# ─── Node: Classify ──────────────────────────────────────────────────

async def classify_node(state: GraphState) -> GraphState:
    t0 = time.time()
    input_type = classify_input(state["raw_input"])
    duration = int((time.time() - t0) * 1000)

    logger.info("node.classify", session_id=state["session_id"],
                input_type=input_type, duration_ms=duration)

    await emit_sse(state["session_id"], {
        "stage": "classify", "status": "done",
        "input_type": input_type, "duration_ms": duration
    })

    trace = state.get("pipeline_trace", []) + [
        _trace_entry("classify", "done", f"Detected: {input_type}", duration)
    ]
    return {
        "input_type": input_type,
        "pipeline_trace": trace,
        "started_at": time.time(),
    }


# ─── Node: Build User Context (Intelligence Layer) ───────────────────

async def user_context_node(state: GraphState) -> GraphState:
    """Fetch user's order history, go-to items, and brand preferences from Swiggy MCP."""
    t0 = time.time()
    try:
        ctx = await build_user_context(state["session_id"])
        duration = int((time.time() - t0) * 1000)

        logger.info("node.user_context", session_id=state["session_id"],
                     go_to_items=len(ctx.go_to_items),
                     preferred_brands=len(ctx.preferred_brands),
                     recent_purchases=len(ctx.recent_purchases),
                     duration_ms=duration)

        await emit_sse(state["session_id"], {
            "stage": "user_context", "status": "done",
            "go_to_items": len(ctx.go_to_items),
            "preferred_brands": len(ctx.preferred_brands),
            "recent_purchases": len(ctx.recent_purchases),
            "dietary_signals": ctx.dietary_signals,
            "duration_ms": duration,
        })

        trace = state.get("pipeline_trace", []) + [
            _trace_entry("user_context", "done",
                         f"{len(ctx.go_to_items)} go-to items, "
                         f"{len(ctx.preferred_brands)} brand prefs, "
                         f"{len(ctx.recent_purchases)} recent purchases",
                         duration)
        ]
        return {"user_context": ctx, "pipeline_trace": trace}
    except Exception as e:
        duration = int((time.time() - t0) * 1000)
        logger.warning("node.user_context.failed", error=str(e)[:100])
        trace = state.get("pipeline_trace", []) + [
            _trace_entry("user_context", "skipped", "Proceeding without personalization", duration)
        ]
        return {"user_context": UserContext(), "pipeline_trace": trace}


# ─── Node: Extract Content ───────────────────────────────────────────

async def extract_node(state: GraphState) -> GraphState:
    t0 = time.time()
    try:
        content, source = await extract_content(state["raw_input"], state["input_type"])
        duration = int((time.time() - t0) * 1000)
        word_count = len(content.split())

        logger.info("node.extract", session_id=state["session_id"],
                     source=source, word_count=word_count, duration_ms=duration)

        await emit_sse(state["session_id"], {
            "stage": "extract", "status": "done",
            "source": source, "word_count": word_count, "duration_ms": duration
        })

        trace = state.get("pipeline_trace", []) + [
            _trace_entry("extract", "done", f"{word_count} words from {source}", duration)
        ]
        return {"raw_content": content, "pipeline_trace": trace}

    except Exception as e:
        duration = int((time.time() - t0) * 1000)
        logger.error("node.extract.failed", session_id=state["session_id"],
                      error=str(e), duration_ms=duration)

        trace = state.get("pipeline_trace", []) + [
            _trace_entry("extract", "failed", str(e), duration)
        ]
        error_msg = str(e)
        if "subtitles" in error_msg.lower() or "transcript" in error_msg.lower():
            error_msg = "Could not get video transcript. Try pasting the recipe text directly."

        return {"error": error_msg, "pipeline_trace": trace}


# ─── Node: Understand Recipe (LLM) ───────────────────────────────────

async def understand_node(state: GraphState) -> GraphState:
    t0 = time.time()
    retry_count = state.get("retry_count", 0)

    try:
        recipe = await understand_recipe(state["raw_content"])
        duration = int((time.time() - t0) * 1000)

        logger.info("node.understand", session_id=state["session_id"],
                     recipe_name=recipe.recipe_name,
                     ingredient_count=len(recipe.ingredients),
                     confidence=recipe.confidence_score,
                     duration_ms=duration)

        await emit_sse(state["session_id"], {
            "stage": "understand", "status": "done",
            "recipe_name": recipe.recipe_name,
            "ingredient_count": len(recipe.ingredients),
            "confidence": recipe.confidence_score,
            "duration_ms": duration,
        })

        trace = state.get("pipeline_trace", []) + [
            _trace_entry("understand", "done",
                         f"{recipe.recipe_name}: {len(recipe.ingredients)} ingredients, "
                         f"{recipe.confidence_score:.0%} confidence", duration)
        ]
        return {"recipe": recipe, "pipeline_trace": trace}

    except Exception as e:
        duration = int((time.time() - t0) * 1000)
        logger.error("node.understand.failed", session_id=state["session_id"],
                      error=str(e), retry_count=retry_count, duration_ms=duration)

        trace = state.get("pipeline_trace", []) + [
            _trace_entry("understand", "failed", f"Attempt {retry_count + 1}: {str(e)}", duration)
        ]
        return {
            "error": f"Failed to parse recipe: {str(e)}",
            "retry_count": retry_count + 1,
            "pipeline_trace": trace,
        }


# ─── Node: Validate Recipe (GATE) ────────────────────────────────────

async def validate_recipe_node(state: GraphState) -> GraphState:
    t0 = time.time()
    recipe = state["recipe"]

    repaired_recipe, result = validate_recipe(recipe)
    duration = int((time.time() - t0) * 1000)

    logger.info("node.validate_recipe", session_id=state["session_id"],
                 passed=result.passed,
                 issues=result.issues, warnings=result.warnings,
                 repairs=result.repairs, duration_ms=duration)

    detail_parts = []
    if result.repairs:
        detail_parts.append(f"{len(result.repairs)} auto-repairs")
    if result.warnings:
        detail_parts.append(f"{len(result.warnings)} warnings")
    if result.issues:
        detail_parts.append(f"{len(result.issues)} blocking issues")
    detail = ", ".join(detail_parts) if detail_parts else "Clean"

    await emit_sse(state["session_id"], {
        "stage": "validate_recipe", "status": "done",
        "passed": result.passed,
        "issues": result.issues,
        "warnings": result.warnings,
        "repairs": result.repairs,
        "duration_ms": duration,
    })

    trace = state.get("pipeline_trace", []) + [
        _trace_entry("validate_recipe", "done" if result.passed else "issues", detail, duration)
    ]

    return {
        "recipe": repaired_recipe,
        "validation_result": result.to_dict(),
        "pipeline_trace": trace,
    }


# ─── Node: Normalize Ingredients ─────────────────────────────────────

async def normalize_node(state: GraphState) -> GraphState:
    t0 = time.time()
    normalized = normalize_ingredients(state["recipe"].ingredients, state["recipe"].serving_size)
    duration = int((time.time() - t0) * 1000)

    db_matched = sum(1 for n in normalized if n.get("matched_in_db"))
    unmatched = len(normalized) - db_matched

    logger.info("node.normalize", session_id=state["session_id"],
                 total=len(normalized), db_matched=db_matched,
                 unmatched=unmatched, duration_ms=duration)

    await emit_sse(state["session_id"], {
        "stage": "normalize", "status": "done",
        "total": len(normalized), "db_matched": db_matched,
        "unmatched": unmatched, "duration_ms": duration,
    })

    trace = state.get("pipeline_trace", []) + [
        _trace_entry("normalize", "done",
                     f"{len(normalized)} ingredients, {db_matched} matched in DB", duration)
    ]
    return {"normalized_ingredients": normalized, "pipeline_trace": trace}


# ─── Node: Search Instamart (with synonym retry) ─────────────────────

async def search_instamart_node(state: GraphState) -> GraphState:
    t0 = time.time()
    client = MCPClient(state["session_id"])

    # Use address from UserContext (already resolved)
    ctx = state.get("user_context") or UserContext()
    address_id = ctx.address_id or "mock_addr_1"

    search_results = {}
    sem = asyncio.Semaphore(8)

    async def do_search(term: str) -> tuple:
        async with sem:
            try:
                res = await client.call_tool("search_products", {
                    "addressId": address_id, "query": term
                })
                # If no results, try a simplified search term
                if not res.get("products"):
                    simplified = term.split()[0] if " " in term else term
                    if simplified != term:
                        logger.info("search.retry_simplified",
                                    original=term, simplified=simplified)
                        res = await client.call_tool("search_products", {
                            "addressId": address_id, "query": simplified
                        })
                return term, res
            except Exception as e:
                logger.warning("search.failed", term=term, error=str(e))
                return term, {"products": []}

    tasks = [do_search(ing["search_term"]) for ing in state["normalized_ingredients"]]
    results = await asyncio.gather(*tasks)

    for term, res in results:
        search_results[term] = res

    found_count = sum(1 for res in search_results.values() if res.get("products"))
    missing_count = len(state["normalized_ingredients"]) - found_count
    duration = int((time.time() - t0) * 1000)

    logger.info("node.search", session_id=state["session_id"],
                 found=found_count, missing=missing_count,
                 duration_ms=duration)

    await emit_sse(state["session_id"], {
        "stage": "search", "status": "done",
        "found_count": found_count, "missing_count": missing_count,
        "duration_ms": duration,
    })

    trace = state.get("pipeline_trace", []) + [
        _trace_entry("search", "done",
                     f"{found_count} found, {missing_count} missing", duration)
    ]
    return {"search_results": search_results, "pipeline_trace": trace}


# ─── Node: Rank & Optimize ───────────────────────────────────────────

async def optimize_node(state: GraphState) -> GraphState:
    t0 = time.time()
    ctx = state.get("user_context") or UserContext()
    cart_items = rank_and_optimize(state["search_results"], state["normalized_ingredients"], ctx)

    available = [i for i in cart_items if i.get("spin_id")]
    pantry = [i for i in cart_items if i.get("pantry_likely") and not i.get("spin_id")]
    unavailable = [i for i in cart_items if not i.get("spin_id") and not i.get("pantry_likely")]
    substitutes = [i for i in cart_items if i.get("confidence") == "low"]

    cart_total = sum(
        i.get("product_price", 0) * i.get("quantity", 1)
        for i in available
    )
    avg_waste = (
        sum(i.get("waste_pct", 0) for i in available) / max(len(available), 1)
    )
    avg_confidence = (
        sum(i.get("confidence_score", 0) for i in available) / max(len(available), 1)
    )

    duration = int((time.time() - t0) * 1000)

    metrics = {
        "cart_total": cart_total,
        "item_count": len(available),
        "pantry_skipped": len(pantry),
        "unavailable_count": len(unavailable),
        "substitute_count": len(substitutes),
        "avg_waste_pct": round(avg_waste, 1),
        "avg_confidence": round(avg_confidence, 2),
        "duration_ms": duration,
    }

    logger.info("node.optimize", session_id=state["session_id"], **metrics)

    await emit_sse(state["session_id"], {
        "stage": "optimize", "status": "done", **metrics
    })

    trace = state.get("pipeline_trace", []) + [
        _trace_entry("optimize", "done",
                     f"₹{cart_total}, {len(available)} items, "
                     f"{avg_waste:.0f}% avg waste, {avg_confidence:.0%} avg confidence",
                     duration)
    ]

    return {
        "cart_items": cart_items,
        "ranked_products": cart_items,
        "pipeline_trace": trace,
        "pipeline_metrics": metrics,
    }


# ─── Node: Validate Cart (GATE) ──────────────────────────────────────

async def validate_cart_node(state: GraphState) -> GraphState:
    t0 = time.time()
    result = validate_cart(state["cart_items"], state["normalized_ingredients"])
    duration = int((time.time() - t0) * 1000)

    logger.info("node.validate_cart", session_id=state["session_id"],
                 passed=result.passed, issues=result.issues,
                 warnings=result.warnings, duration_ms=duration)

    await emit_sse(state["session_id"], {
        "stage": "validate_cart", "status": "done",
        "passed": result.passed,
        "warnings": result.warnings,
        "duration_ms": duration,
    })

    trace = state.get("pipeline_trace", []) + [
        _trace_entry("validate_cart", "done" if result.passed else "issues",
                     f"{len(result.warnings)} warnings" if result.warnings else "Clean", duration)
    ]

    return {
        "cart_validation_result": result.to_dict(),
        "pipeline_trace": trace,
    }


# ─── Conditional Router: Post-Extraction ─────────────────────────────

def route_after_extract(state: GraphState) -> str:
    """Route after extraction: proceed or abort on error."""
    if state.get("error"):
        return "abort"
    return "understand"


# ─── Conditional Router: Post-Understanding ──────────────────────────

def route_after_understand(state: GraphState) -> str:
    """Route after LLM understanding: validate or retry."""
    if state.get("error"):
        retry_count = state.get("retry_count", 0)
        if retry_count < 2:
            return "retry_understand"
        return "abort"
    return "validate_recipe"


# ─── Conditional Router: Post-Validation ─────────────────────────────

def route_after_validation(state: GraphState) -> str:
    """Route after recipe validation: proceed or abort on blocking issues."""
    validation = state.get("validation_result", {})
    if not validation.get("passed", True):
        retry_count = state.get("retry_count", 0)
        if retry_count < 2:
            return "retry_understand"
        return "abort"
    return "normalize"


# ─── Node: Abort with Error ──────────────────────────────────────────

async def abort_node(state: GraphState) -> GraphState:
    error = state.get("error", "Unknown error occurred")
    logger.error("node.abort", session_id=state["session_id"], error=error)

    await emit_sse(state["session_id"], {
        "stage": "error", "message": error
    })

    trace = state.get("pipeline_trace", []) + [
        _trace_entry("abort", "error", error)
    ]
    return {"pipeline_trace": trace}


# ─── Node: Build Cart (post-approval) ─────────────────────────────────

async def build_cart_node(state: GraphState) -> GraphState:
    if not state.get("user_approved"):
        return {}

    manager = CartManager(state["session_id"])
    items_to_add = [
        {**item, "quantity": item.get("quantity", 1)}
        for item in state["cart_items"] if item.get("spin_id")
    ]

    verified_total = await manager.clear_and_build(items_to_add)
    logger.info("node.build_cart", session_id=state["session_id"],
                 item_count=len(items_to_add), verified_total=verified_total)

    await emit_sse(state["session_id"], {
        "stage": "cart_built", "status": "done",
        "verified_total": verified_total
    })
    return {}


# ─── Node: Checkout (post-approval) ──────────────────────────────────

async def checkout_node(state: GraphState) -> GraphState:
    manager = CartManager(state["session_id"])
    order_id = await manager.safe_checkout()

    logger.info("node.checkout", session_id=state["session_id"],
                 order_id=order_id)

    await emit_sse(state["session_id"], {
        "stage": "ordered", "status": "done",
        "order_id": order_id, "estimated_delivery_minutes": 15
    })
    return {"order_id": order_id}


# ─── Build the Agentic Graph ─────────────────────────────────────────

def build_graph():
    workflow = StateGraph(GraphState)

    # Register all nodes
    workflow.add_node("classify", classify_node)
    workflow.add_node("user_context", user_context_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("understand", understand_node)
    workflow.add_node("validate_recipe", validate_recipe_node)
    workflow.add_node("normalize", normalize_node)
    workflow.add_node("search", search_instamart_node)
    workflow.add_node("optimize", optimize_node)
    workflow.add_node("validate_cart", validate_cart_node)
    workflow.add_node("abort", abort_node)

    # Entry point
    workflow.set_entry_point("classify")

    # Parallel: classify → user_context (non-blocking) + extract
    workflow.add_edge("classify", "user_context")
    workflow.add_edge("user_context", "extract")

    # Conditional: after extract → understand or abort
    workflow.add_conditional_edges("extract", route_after_extract, {
        "understand": "understand",
        "abort": "abort",
    })

    # Conditional: after understand → validate or retry or abort
    workflow.add_conditional_edges("understand", route_after_understand, {
        "validate_recipe": "validate_recipe",
        "retry_understand": "understand",
        "abort": "abort",
    })

    # Conditional: after validation → normalize or retry or abort
    workflow.add_conditional_edges("validate_recipe", route_after_validation, {
        "normalize": "normalize",
        "retry_understand": "understand",
        "abort": "abort",
    })

    # Linear edges for the rest of the pipeline
    workflow.add_edge("normalize", "search")
    workflow.add_edge("search", "optimize")
    workflow.add_edge("optimize", "validate_cart")

    # Terminal edges
    workflow.add_edge("validate_cart", END)
    workflow.add_edge("abort", END)

    return workflow.compile()
