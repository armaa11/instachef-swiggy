"""
User Context Intelligence Layer

Builds a rich user profile from Swiggy MCP data (order history, go-to items)
to enable context-aware, personalized cart optimization.
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import structlog
from app.mcp.client import MCPClient

logger = structlog.get_logger()


@dataclass
class UserContext:
    """Rich user context built from Swiggy order history and preferences."""
    preferred_brands: Dict[str, str] = field(default_factory=dict)      # ingredient → brand
    recent_purchases: Dict[str, str] = field(default_factory=dict)      # ingredient → date
    go_to_spin_ids: Set[str] = field(default_factory=set)               # frequently ordered spinIds
    go_to_items: List[Dict] = field(default_factory=list)               # raw go-to items from Swiggy
    dietary_signals: List[str] = field(default_factory=list)            # detected from order history
    order_count: int = 0
    address_id: str = ""
    address_label: str = ""


async def build_user_context(session_id: str) -> UserContext:
    """
    Build a UserContext by calling Swiggy MCP tools:
    1. get_addresses → resolve delivery address
    2. your_go_to_items → user's frequently ordered products
    3. get_orders → recent order history for brand preferences
    
    This context is injected into the optimizer to make the agent
    context-aware and personalized.
    """
    ctx = UserContext()
    client = MCPClient(session_id)

    # ─── Step 1: Resolve address ──────────────────────────────────
    try:
        addresses = await client.call_tool("get_addresses", {})
        home_addr = next(
            (a for a in addresses if a.get("label", "").lower() == "home"),
            addresses[0] if addresses else None
        )
        if home_addr:
            ctx.address_id = home_addr.get("id", "")
            ctx.address_label = home_addr.get("label", "Unknown")
        logger.info("user_context.address_resolved",
                     address_id=ctx.address_id, label=ctx.address_label)
    except Exception as e:
        logger.warning("user_context.address_failed", error=str(e)[:100])
        ctx.address_id = "mock_addr_1"

    # ─── Step 2: Fetch go-to items ────────────────────────────────
    try:
        go_to_data = await client.call_tool("your_go_to_items", {
            "addressId": ctx.address_id
        })
        go_to_items = go_to_data.get("items", []) if isinstance(go_to_data, dict) else []
        ctx.go_to_items = go_to_items
        ctx.go_to_spin_ids = {item.get("spinId", "") for item in go_to_items if item.get("spinId")}

        # Extract brand preferences from go-to items
        for item in go_to_items:
            name = item.get("name", "").lower()
            brand = item.get("brand", "")
            if brand:
                # Map product name keywords to brand preference
                for keyword in name.split():
                    if len(keyword) > 3:  # skip short words
                        ctx.preferred_brands[keyword] = brand

        logger.info("user_context.go_to_items",
                     count=len(go_to_items),
                     brands=len(ctx.preferred_brands))
    except Exception as e:
        logger.warning("user_context.go_to_failed", error=str(e)[:100])

    # ─── Step 3: Analyze recent orders ────────────────────────────
    try:
        orders = await client.call_tool("get_orders", {})
        ctx.order_count = len(orders) if isinstance(orders, list) else 0

        # Analyze recent orders for patterns
        if isinstance(orders, list):
            for order in orders[:5]:  # Last 5 orders
                order_id = order.get("orderId", "")
                if order_id:
                    try:
                        details = await client.call_tool("get_order_details", {
                            "orderId": order_id
                        })
                        items = details.get("items", []) if isinstance(details, dict) else []
                        for item in items:
                            item_name = item.get("name", "").lower()
                            ctx.recent_purchases[item_name] = order.get("placed_at", "unknown")

                            # Detect dietary signals
                            if any(kw in item_name for kw in ["chicken", "mutton", "fish", "egg"]):
                                if "non-vegetarian" not in ctx.dietary_signals:
                                    ctx.dietary_signals.append("non-vegetarian")
                            if any(kw in item_name for kw in ["paneer", "tofu", "soy"]):
                                if "vegetarian-leaning" not in ctx.dietary_signals:
                                    ctx.dietary_signals.append("vegetarian-leaning")
                    except Exception:
                        pass  # Skip individual order failures

        logger.info("user_context.orders_analyzed",
                     order_count=ctx.order_count,
                     recent_purchases=len(ctx.recent_purchases),
                     dietary_signals=ctx.dietary_signals)
    except Exception as e:
        logger.warning("user_context.orders_failed", error=str(e)[:100])

    return ctx
