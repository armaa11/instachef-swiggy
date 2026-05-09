# AGENTS.md — InstaChef AI

## Project Overview
InstaChef AI is a 10-node agentic cooking commerce pipeline that turns recipe sources (YouTube, Instagram, blogs, text) into Swiggy Instamart grocery orders.

## Architecture
- **Backend**: FastAPI + LangGraph state machine (`backend/app/agent.py`)
- **Frontend**: Next.js 14 + Tailwind (`frontend/app/`)
- **Pipeline**: 10 nodes with 2 validation gates and conditional routing
- **Commerce**: Swiggy MCP integration via OAuth 2.1

## Key Files
- `backend/app/agent.py` — LangGraph workflow engine (state machine)
- `backend/app/pipeline/` — Individual pipeline nodes (classifier, extractor, understander, normalizer, optimizer, validators, instagram)
- `backend/app/mcp/` — Swiggy MCP client, auth, and cart management
- `backend/app/config.py` — Environment configuration
- `frontend/app/components/` — React components (RecipeInput, PipelineProgress, CartReview, TrackingView)

## Conventions
- All pipeline nodes follow the pattern: `async def node_name(state: GraphState) -> GraphState`
- Every node emits SSE events via `emit_sse()` for real-time frontend updates
- Every node appends to `pipeline_trace` for debugging
- Redis is used for caching at multiple levels (transcripts, recipes, user context)
- Mock mode (`MOCK_MCP=true`) provides full functionality without Swiggy credentials
