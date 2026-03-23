# AgentLens

**Open-source observability for AI agents. Add 2 lines of code, see every LLM call.**

AgentLens automatically captures all OpenAI and Anthropic API calls from your AI agent and displays them on a real-time dashboard with cost tracking, performance metrics, and execution traces.

---

## Features

- **Auto-capture SDK** -- Monkey-patches OpenAI and Anthropic clients. No manual instrumentation required.
- **Non-blocking telemetry** -- Background sender thread flushes captured data every 5 seconds with zero impact on agent performance.
- **Cost tracking** -- Per-model pricing for accurate spend monitoring across all LLM calls.
- **Execution traces** -- Full request/response capture with token counts, latency, and model metadata.
- **Multi-tenant isolation** -- Row-level filtering ensures each user sees only their own data.
- **Dual auth** -- Auth0 JWT for the dashboard (Google + GitHub social login), API keys for the SDK.
- **Analytics dashboard** -- Six pages: Login, Onboarding, Dashboard, Execution Detail, Analytics, and Settings.
- **Structured logging** -- Request correlation IDs and JSON-structured logs for every API call.

---

## Quick Start

### 1. Sign up and get an API key

Create an account on the AgentLens dashboard and copy your API key from the Settings page.

### 2. Install the SDK

```bash
pip install agentlens
```

### 3. Initialize in your agent code (2 lines)

```python
from agentlens import AgentLens

AgentLens.init(api_key="al_your_api_key_here")
```

### 4. Run your agent normally

```python
import openai

client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello, world!"}]
)
```

All LLM calls are automatically captured and sent to your AgentLens dashboard.

---

## Architecture

```
                    ┌─────────────────────────────┐
                    │   Developer's Agent Code     │
                    │   (OpenAI / Anthropic calls)  │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │      AgentLens SDK           │
                    │  ┌────────────────────────┐  │
                    │  │  Monkey-Patcher        │  │
                    │  │  (OpenAI + Anthropic)   │  │
                    │  └──────────┬─────────────┘  │
                    │  ┌──────────▼─────────────┐  │
                    │  │  Event Recorder        │  │
                    │  │  (thread-safe buffer)   │  │
                    │  └──────────┬─────────────┘  │
                    │  ┌──────────▼─────────────┐  │
                    │  │  Background Sender     │  │
                    │  │  (flush every 5s)       │  │
                    │  └──────────┬─────────────┘  │
                    └─────────────┼────────────────┘
                                  │ POST /api/traces
                                  │ (X-API-Key auth)
                    ┌─────────────▼────────────────┐
                    │     FastAPI Backend           │
                    │  ┌─────────────────────────┐  │
                    │  │  Request Logging        │  │
                    │  │  (correlation IDs)       │  │
                    │  ├─────────────────────────┤  │
                    │  │  Auth: Auth0 JWT (web)  │  │
                    │  │  Auth: API Key (SDK)    │  │
                    │  ├─────────────────────────┤  │
                    │  │  Routes: traces, stats, │  │
                    │  │  executions, keys, auth │  │
                    │  └──────────┬──────────────┘  │
                    └─────────────┼─────────────────┘
                                  │
                    ┌─────────────▼────────────────┐
                    │  SQLite (dev) / PostgreSQL    │
                    │  Tables: users, executions,   │
                    │  llm_calls, tool_calls, keys  │
                    └──────────────────────────────┘
                                  │
                    ┌─────────────▼────────────────┐
                    │     React Dashboard           │
                    │  Auth0 (Google + GitHub)       │
                    │  Pages: Dashboard, Analytics,  │
                    │  Execution Detail, Settings    │
                    └──────────────────────────────┘
```

**Auth flow:**

- Dashboard users authenticate via Auth0 (Google/GitHub). JIT provisioning creates the user record on first login.
- SDK clients authenticate with API keys (`al_xxx`) that resolve to a `user_id` for multi-tenant data isolation.

---

## Tech Stack

| Layer      | Technology                                            |
|------------|-------------------------------------------------------|
| Backend    | FastAPI, SQLAlchemy, SQLite (dev), PostgreSQL (prod)  |
| Frontend   | React 19, Vite, TailwindCSS v4, Recharts             |
| Auth       | Auth0 (Google + GitHub social login), API keys (SDK)  |
| SDK        | Python, monkey-patching, background sender thread     |
| CI/CD      | GitHub Actions (tests, lint, build)                   |
| Deploy     | DigitalOcean App Platform (Docker)                    |
| Testing    | pytest (30 tests), multi-tenancy isolation tests      |

---

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 18+

### Option 1: Docker Compose (recommended)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit .env files with your Auth0 credentials

docker compose up -d --build
```

Backend: `http://localhost:8000` | Frontend: `http://localhost:5173`

### Option 2: Manual

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Seed Data

```bash
export AGENTLENS_API_KEY=al_your_key_here
python examples/simple_agent.py
```

---

## Running Tests

```bash
cd backend
pytest -v
```

All 30 tests cover authentication, multi-tenancy, API key management, trace ingestion, and stats endpoints.

---

## Project Structure

```
agentlens/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── main.py           # App entrypoint, middleware
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── config.py         # Environment-based settings
│   │   ├── auth0.py          # Auth0 JWT verification (RS256)
│   │   ├── dependencies.py   # FastAPI dependency injection
│   │   ├── middleware/        # Request logging, correlation IDs
│   │   └── routes/            # auth, executions, keys, stats, traces
│   ├── tests/                # 30 pytest tests
│   ├── scripts/              # Seed data utilities
│   └── Dockerfile
├── frontend/                 # React + Vite dashboard
│   └── src/
│       ├── pages/            # Login, Dashboard, ExecutionPage, Analytics, Settings, Onboarding
│       ├── components/       # StatCard, ExecutionTable, Layout, ProtectedRoute
│       ├── context/          # AuthContext (Auth0 integration)
│       └── api/              # API client with JWT auth
├── sdk/                      # Python SDK package
│   └── agentlens/
│       ├── client.py         # Core client + monkey-patching
│       ├── recorder.py       # Thread-safe event recording
│       ├── sender.py         # Background sender with error logging
│       ├── pricing.py        # Per-model cost calculations
│       └── patchers/         # OpenAI + Anthropic auto-capture
├── examples/                 # Demo scripts (no external API keys needed)
├── .github/workflows/        # CI: tests, lint, build
├── .do/                      # DigitalOcean App Platform config
├── docker-compose.yml        # Local dev (PostgreSQL + backend + frontend)
└── DEPLOYMENT.md             # Production deployment guide
```

---

## Examples

Run example agents to populate your dashboard with sample data:

```bash
export AGENTLENS_API_KEY=al_your_key_here

# Simple agent (3 executions with LLM + tool calls)
python examples/simple_agent.py

# Multi-step research agent (3 research queries)
python examples/multi_step_agent.py

# Simulated auto-capture (no OpenAI key needed)
python examples/auto_capture_simulated.py
```

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for DigitalOcean App Platform deployment instructions (~$5/mo).

---

## License

MIT
