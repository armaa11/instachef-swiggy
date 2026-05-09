import uuid
import httpx
import asyncio
from typing import Any, Dict, List, Optional
import structlog
from app.config import settings
from app.mcp.auth import MCPAuth

logger = structlog.get_logger()

# Methods that are not safe to blind-retry
NON_IDEMPOTENT_TOOLS = {"checkout", "place_food_order", "book_table"}

class MCPClient:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.auth = MCPAuth(session_id)

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name in NON_IDEMPOTENT_TOOLS:
            # Special handling for non-idempotent tools (no blind retries)
            return await self._execute_call(name, arguments)
        
        # Idempotent tools: exponential backoff retry
        max_attempts = 4
        attempt = 0
        while True:
            try:
                return await self._execute_call(name, arguments)
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
                attempt += 1
                if attempt >= max_attempts:
                    raise e
                
                # Check if it's a 4xx (except 429) - don't retry bad requests
                if isinstance(e, httpx.HTTPStatusError):
                    status = e.response.status_code
                    if 400 <= status < 500 and status != 429 and status != 401:
                        raise e

                base_ms = 500 * (2 ** (attempt - 1))
                logger.warning("mcp.retry", tool=name, attempt=attempt, delay_ms=base_ms)
                await asyncio.sleep(base_ms / 1000.0)

    async def _execute_call(self, name: str, arguments: Dict[str, Any]) -> Any:
        request_id = str(uuid.uuid4())

        if settings.MOCK_MCP:
            result = self._mock_call(name, arguments)
            logger.debug("mcp.mock_call", tool=name, request_id=request_id)
            return result

        token = self.auth.get_valid_token()
        if not token:
            raise ValueError("No valid auth token")

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }

        logger.info("mcp.call", tool=name, request_id=request_id, args_keys=list(arguments.keys()))

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                settings.SWIGGY_MCP_INSTAMART_URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Rate limiting handling
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "30"))
                logger.warning("mcp.rate_limited", tool=name, retry_after=retry_after)
                await asyncio.sleep(retry_after)
                raise httpx.HTTPStatusError("Rate limited", request=resp.request, response=resp)
                
            if resp.status_code >= 400:
                logger.warning("mcp.http_error", tool=name, status_code=resp.status_code, request_id=request_id)
                raise httpx.HTTPStatusError(f"HTTP Error {resp.status_code}", request=resp.request, response=resp)

            data = resp.json()
            if "error" in data:
                logger.error("mcp.rpc_error", tool=name,
                              error=data['error'], request_id=request_id)
                raise Exception(f"MCP Error: {data['error']}")

            logger.info("mcp.success", tool=name, request_id=request_id)
            return data["result"]

    def _mock_call(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name == "get_addresses":
            return [
                {"id": "mock_addr_1", "label": "Home", "address": "123 Mock St, Bangalore 560001"},
                {"id": "mock_addr_2", "label": "Office", "address": "456 Tech Park, Bangalore 560037"},
            ]
        elif name == "search_products":
            query = arguments.get("query", "").lower()
            return {
                "products": [
                    {
                        "name": f"{query.title()} Premium",
                        "brand": "Organic Tattva" if "spice" in query or "powder" in query else "Fresh & Pure",
                        "variants": [
                            {"spinId": f"mock_spin_{query.replace(' ', '_')}_1", "price": 120, "pack_grams": 500, "in_stock": True, "display": "500g", "brand": "Fresh & Pure"}
                        ],
                        "image_url": f"https://placehold.co/150x150?text={query.replace(' ', '+')}"
                    }
                ]
            }
        elif name == "get_cart":
            return {"items": [], "bill": {"total": 0}}
        elif name == "update_cart":
            return {"success": True}
        elif name == "clear_cart":
            return {"success": True}
        elif name == "checkout":
            return {"orderId": f"IM-{uuid.uuid4().hex[:8].upper()}"}
        elif name == "track_order":
            import random
            statuses = ["Order Placed", "Being Packed", "Out for Delivery"]
            return {"status": random.choice(statuses), "eta_minutes": random.randint(10, 25)}
        elif name == "get_orders":
            return [
                {"orderId": "IM-DEMO001", "placed_at": "2 days ago", "total": 540},
                {"orderId": "IM-DEMO002", "placed_at": "5 days ago", "total": 320},
                {"orderId": "IM-DEMO003", "placed_at": "1 week ago", "total": 890},
            ]
        elif name == "your_go_to_items":
            return {"items": [
                {"spinId": "mock_spin_eggs_1", "name": "Farm Fresh Eggs (6 pcs)", "brand": "Nandini", "price": 60, "image_url": "https://placehold.co/150x150?text=Eggs"},
                {"spinId": "mock_spin_milk_1", "name": "Full Cream Milk 500ml", "brand": "Nandini", "price": 30, "image_url": "https://placehold.co/150x150?text=Milk"},
                {"spinId": "mock_spin_onion_1", "name": "Onion 1kg", "brand": "Fresh & Pure", "price": 40, "image_url": "https://placehold.co/150x150?text=Onion"},
                {"spinId": "mock_spin_rice_1", "name": "Basmati Rice 1kg", "brand": "India Gate", "price": 180, "image_url": "https://placehold.co/150x150?text=Rice"},
                {"spinId": "mock_spin_ghee_1", "name": "Pure Ghee 500ml", "brand": "Amul", "price": 280, "image_url": "https://placehold.co/150x150?text=Ghee"},
            ]}
        elif name == "get_order_details":
            order_id = arguments.get("orderId", "")
            if order_id == "IM-DEMO001":
                return {"orderId": order_id, "status": "Delivered", "items": [
                    {"name": "Basmati Rice 1kg", "brand": "India Gate", "price": 180, "quantity": 1},
                    {"name": "Onion 1kg", "brand": "Fresh & Pure", "price": 40, "quantity": 2},
                    {"name": "Chicken Breast 500g", "brand": "Licious", "price": 250, "quantity": 1},
                ], "total": 510}
            elif order_id == "IM-DEMO002":
                return {"orderId": order_id, "status": "Delivered", "items": [
                    {"name": "Paneer 200g", "brand": "Amul", "price": 90, "quantity": 1},
                    {"name": "Tomato 500g", "brand": "Fresh & Pure", "price": 30, "quantity": 1},
                    {"name": "Garam Masala 100g", "brand": "Everest", "price": 65, "quantity": 1},
                ], "total": 185}
            return {"orderId": order_id, "status": "Delivered", "items": [
                {"name": "Mixed Vegetables", "price": 120, "quantity": 1}
            ], "total": 120}
        elif name == "report_error":
            return {"success": True, "ticketId": f"TKT-{uuid.uuid4().hex[:8]}"}
        return {}
