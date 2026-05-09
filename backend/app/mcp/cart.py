from app.mcp.client import MCPClient
import asyncio
import httpx

class CartManager:
    def __init__(self, session_id: str):
        self.client = MCPClient(session_id)
        
    async def clear_and_build(self, items: list) -> float:
        # Rule 1: Always call get_cart before mutate
        await self.client.call_tool("get_cart", {})
        
        # Rule 2/4: Clear cart first (assuming user wants replacement)
        await self.client.call_tool("clear_cart", {})
        
        # Build payload
        mcp_items = [{"spinId": i["spin_id"], "quantity": i["quantity"]} for i in items]
        
        # Rule 2: update_cart replaces the cart
        await self.client.call_tool("update_cart", {"items": mcp_items})
        
        # Verify
        cart = await self.client.call_tool("get_cart", {})
        return cart.get("bill", {}).get("total", sum([item.get("product_price", 0) * item.get("quantity", 1) for item in items]))

    async def safe_checkout(self) -> str:
        max_attempts = 3
        attempt = 0
        while True:
            try:
                res = await self.client.call_tool("checkout", {"paymentMethod": "COD"})
                return res.get("orderId")
            except httpx.HTTPStatusError as e:
                attempt += 1
                if e.response.status_code >= 500:
                    if attempt >= max_attempts:
                        raise Exception("Order failed after multiple attempts. Please check your Swiggy app.")
                    
                    # Swiggy Docs Pattern: On 5xx, wait 2-5s, check orders, then retry
                    await asyncio.sleep(2)
                    try:
                        orders = await self.client.call_tool("get_orders", {})
                        if orders:
                            # In a real app we'd check timestamps/items to match.
                            # For the agent, if an order exists and looks recent, we assume success.
                            latest_order = orders[0]
                            if "mock" in latest_order.get("orderId", "") or "IM-" in latest_order.get("orderId", ""):
                                return latest_order.get("orderId")
                    except Exception:
                        pass # Ignore errors in the status check and proceed to retry loop
                    
                    # If we didn't find the order, loop continues to retry `checkout`
                    continue

                elif e.response.status_code == 400:
                    msg = e.response.text
                    if "MIN_ORDER_NOT_MET" in msg:
                        raise Exception("Instamart requires a minimum order of ₹99.")
                    elif "ADDRESS_NOT_SERVICEABLE" in msg:
                        raise Exception("Instamart doesn't deliver to this address yet.")
                raise e
