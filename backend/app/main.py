from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from typing import Dict, Any, List
import asyncio
import json
import structlog
from app.config import settings
from app.agent import build_graph, emit_sse
import app.agent as agent_module
from app.mcp.auth import MCPAuth
from app.mcp.client import MCPClient

from app.logging_config import configure_logging

configure_logging(settings.LOG_LEVEL)

logger = structlog.get_logger()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Production — add your Vercel URL here
        # "https://your-app.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

event_queues: Dict[str, asyncio.Queue] = {}

async def push_sse(session_id: str, data: dict):
    if session_id in event_queues:
        await event_queues[session_id].put(data)

agent_module.emit_sse = push_sse

graphs_state: Dict[str, Any] = {}

class ProcessRequest(BaseModel):
    session_id: str
    url_or_text: str

class ConfirmRequest(BaseModel):
    session_id: str
    cart_items: List[Dict[str, Any]]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/auth/status")
def auth_status(session_id: str):
    auth = MCPAuth(session_id)
    return {"authenticated": auth.has_valid_session()}

@app.get("/auth/login")
def auth_login(session_id: str):
    auth = MCPAuth(session_id)
    return {"url": auth.generate_auth_url()}

@app.post("/api/process")
async def process_recipe(req: ProcessRequest):
    # Input validation
    if not req.url_or_text or not req.url_or_text.strip():
        raise HTTPException(status_code=400, detail="Input cannot be empty")
    if len(req.url_or_text) > 10000:
        raise HTTPException(status_code=400, detail="Input too long (max 10,000 characters)")

    graph = build_graph()
    state = {
        "session_id": req.session_id,
        "raw_input": req.url_or_text,
        "input_type": "",
        "raw_content": "",
        "recipe": None,
        "normalized_ingredients": [],
        "search_results": {},
        "ranked_products": [],
        "cart_items": [],
        "user_approved": False,
        "order_id": None,
        "error": None,
        # Agentic intelligence state
        "user_context": None,
        "validation_result": None,
        "cart_validation_result": None,
        "retry_count": 0,
        "pipeline_trace": [],
        "pipeline_metrics": {},
        "started_at": 0,
    }
    
    if req.session_id not in event_queues:
        event_queues[req.session_id] = asyncio.Queue()
        
    asyncio.create_task(run_pipeline(graph, state, req.session_id))
    return {"status": "started"}

async def run_pipeline(graph, state, session_id):
    try:
        async for s in graph.astream(state):
            for k, v in s.items():
                state.update(v)
            graphs_state[session_id] = state

            # Check if optimize + validate_cart is done → send proposal
            if "validate_cart" in s or "optimize" in s:
                if state.get("cart_items") and not state.get("error"):
                    available_items = [i for i in state["cart_items"] if i.get("spin_id")]
                    await push_sse(session_id, {
                        "stage": "proposal_ready",
                        "cart_items": state["cart_items"],
                        "cart_total": sum(
                            i.get("product_price", 0) * i.get("quantity", 1)
                            for i in available_items
                        ),
                        "pipeline_trace": state.get("pipeline_trace", []),
                        "pipeline_metrics": state.get("pipeline_metrics", {}),
                        "validation": state.get("cart_validation_result", {}),
                    })

    except Exception as e:
        logger.error("pipeline.crashed", session_id=session_id, error=str(e))
        await push_sse(session_id, {"stage": "error", "message": str(e)})

@app.post("/api/cart/confirm")
async def confirm_cart(req: ConfirmRequest):
    state = graphs_state.get(req.session_id, {})
    if not state:
        raise HTTPException(status_code=400, detail="Session not found")
        
    state["user_approved"] = True
    state["cart_items"] = req.cart_items
    
    try:
        await agent_module.build_cart_node(state)
        await agent_module.checkout_node(state)
    except Exception as e:
        await push_sse(req.session_id, {"stage": "error", "message": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success"}

@app.get("/api/stream")
async def stream_events(session_id: str, request: Request):
    if session_id not in event_queues:
        event_queues[session_id] = asyncio.Queue()
        
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    # Wait up to 15 seconds for an event, then send heartbeat
                    data = await asyncio.wait_for(
                        event_queues[session_id].get(), timeout=15.0
                    )
                    yield json.dumps(data)
                except asyncio.TimeoutError:
                    # Send keepalive heartbeat to prevent browser from closing connection
                    yield json.dumps({"stage": "heartbeat", "status": "alive"})
        finally:
            pass
                
    return EventSourceResponse(event_generator())

@app.get("/api/track")
async def track_order(session_id: str):
    state = graphs_state.get(session_id, {})
    order_id = state.get("order_id", None)
    if not order_id:
        return {"status": "No active order", "eta_minutes": 0}
    client = MCPClient(session_id)
    status = await client.call_tool("track_order", {"orderId": order_id})
    return status
