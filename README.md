# AgentLens

**Open-source observability for AI agents. Add 2 lines of code, see every LLM call.**

AgentLens automatically captures all OpenAI and Anthropic API calls from your AI agent and displays them on a real-time dashboard with cost tracking, performance metrics, and execution traces.

<!-- screenshot -->

---

## Features

- **Auto-capture SDK** -- Monkey-patches OpenAI and Anthropic clients. No manual instrumentation required.
- **Non-blocking telemetry** -- Background sender thread flushes captured data every 5 seconds with zero impact on agent performance.
- **Cost tracking** -- Per-model pricing for accurate spend monitoring across all LLM calls.
- **Execution traces** -- Full request/response capture with token counts, latency, and model metadata.
- **Multi-tenant isolation** -- Row-level filtering ensures each user sees only their own data.
- **Dual auth** -- Auth0 JWT for the dashboard (Google + GitHub social login), API keys for the SDK.
- **Analytics dashboard** -- Five pages: Login, Dashboard, Execution Detail, Analytics, and Settings.

---

## Quick Start

### 1. Sign up and get an API key

Create an account on the AgentLens dashboard and copy your API key from the Settings page.

### 2. Install the SDK

```bash
pip install agentlens
```

### 3. Initialize in your agent code

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
[Developer's Agent Code]
        |
[AgentLens SDK] --- monkey-patches OpenAI/Anthropic clients
        |
[Background Sender Thread] --- flushes every 5s, non-blocking
        |
[FastAPI Backend] --- validates API key, resolves user_id
        |
[SQLite (dev) / PostgreSQL (prod)] --- executions, llm_calls, tool_calls
        |
[React Dashboard] --- stats, execution list, analytics charts
```

**Auth flow:**

- Dashboard users authenticate via Auth0 (Google/GitHub). JIT provisioning creates the user record on first login.
- SDK clients authenticate with API keys (`al_xxx`) that resolve to a `user_id` for multi-tenant data isolation.

---

## Tech Stack

| Layer    | Technology                                      |
|----------|------------------------------------------------|
| Backend  | FastAPI, SQLAlchemy, SQLite (dev), PostgreSQL (prod) |
| Frontend | React 18, Vite, TailwindCSS v4, Recharts, React Router |
| Auth     | Auth0 (Google + GitHub social login)            |
| SDK      | Python, monkey-patching, background sender thread |
| Testing  | pytest (30 passing tests)                       |

---

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 18+

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API server starts at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard starts at `http://localhost:5173`.

### Seed Data

```bash
python backend/scripts/seed_data.py
```

---

## Running Tests

```bash
PYTHONPATH=backend pytest backend/tests/ -v
```

All 30 tests cover authentication, multi-tenancy, API key management, execution ingestion, and stats endpoints.

---

## Project Structure

```
agentlens/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── main.py           # Application entrypoint and middleware
│   │   ├── models.py         # SQLAlchemy models (User, Execution, LLMCall, ToolCall, APIKey)
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── database.py       # Database engine and session management
│   │   ├── config.py         # Application settings
│   │   ├── auth0.py          # Auth0 JWT verification
│   │   ├── dependencies.py   # FastAPI dependency injection
│   │   └── routes/
│   │       ├── auth_routes.py    # Auth0 callback, user provisioning
│   │       ├── executions.py     # Execution CRUD and trace ingestion
│   │       ├── keys.py           # API key management
│   │       ├── stats.py          # Dashboard statistics
│   │       └── traces.py         # Trace data endpoints
│   ├── tests/                # pytest test suite (30 tests)
│   ├── scripts/              # Seed data and utilities
│   └── requirements.txt
├── frontend/                 # React + Vite dashboard
│   └── src/
│       ├── pages/            # Login, Dashboard, ExecutionPage, Analytics, Settings, Onboarding
│       ├── components/       # StatCard, ExecutionTable, Layout, ProtectedRoute
│       ├── context/          # AuthContext (Auth0 integration)
│       ├── App.jsx           # Router configuration
│       └── main.jsx          # Application entry
├── sdk/                      # Python SDK package
│   └── agentlens/
│       ├── __init__.py       # Public API (AgentLens.init)
│       ├── client.py         # Core client and monkey-patching logic
│       ├── recorder.py       # Call recording and data capture
│       ├── sender.py         # Background thread for async data transmission
│       ├── pricing.py        # Per-model cost calculations
│       └── trace.py          # Trace context management
├── examples/                 # Demo scripts
│   ├── simple_agent.py
│   ├── multi_step_agent.py
│   ├── auto_capture_demo.py
│   └── auto_capture_simulated.py
└── README.md
```

---

## License

MIT
