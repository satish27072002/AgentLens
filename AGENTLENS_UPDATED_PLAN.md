# AgentLens — Updated Implementation Plan (Building From Phase 1)

**Student:** Satish Somarouthu (BIT Sweden, Masters)  
**Updated:** March 20, 2026  
**Status:** Phase 1 complete (backend API + SDK + database + sample agent working)  
**Goal:** Full product experience — developer signs up, adds 2 lines of code, sees analytics on dashboard

---

## What's Already Built (Your Foundation)

From the original Phase 1, you have:

- FastAPI backend running locally
- Database schema: `executions`, `llm_calls`, `tool_calls`, `errors` tables
- API endpoints: POST `/api/traces`, GET `/api/executions`, GET `/api/executions/{id}`, GET `/api/stats`
- Python SDK with `@track_agent` decorator
- HTTP client in SDK that sends data to backend
- Sample agent that tests the full pipeline
- Data flows: Agent → SDK → Backend → Database ✅

**None of this gets thrown away.** Everything below builds on top of it.

---

## The Target Experience

When you're done, this is what happens:

```
1. Developer visits agentlens.vercel.app
2. Developer clicks "Sign Up", creates an account
3. Developer sees onboarding page: "Here's your API key: al_k7x9m2..."
4. Developer installs the SDK:  pip install agentlens
5. Developer adds TWO lines to their existing agent code:

    from agentlens import AgentLens
    AgentLens.init(api_key="al_k7x9m2...")

6. Developer runs their agent normally — changes nothing else
7. Every OpenAI/Anthropic call is automatically captured
8. Developer opens the dashboard → sees all their executions, costs, performance
9. Another developer signs up → they only see THEIR OWN data
```

---

## What Needs to Change (Overview)

### Database: 2 new tables + 1 column added

```
EXISTING (keep as-is):              NEW (add these):
┌──────────────┐                   ┌──────────────┐
│  executions  │ ← add user_id    │    users     │
│  llm_calls   │                   │   api_keys   │
│  tool_calls  │                   └──────────────┘
│  errors      │
└──────────────┘
```

### Backend: 3 things added

```
EXISTING (keep as-is):              NEW (add these):
├── POST /api/traces               ├── POST /api/auth/signup
├── GET  /api/executions           ├── POST /api/auth/login
├── GET  /api/executions/{id}      ├── GET  /api/auth/me
├── GET  /api/stats                ├── POST /api/keys/generate
                                   ├── Auth middleware (JWT)
                                   └── User filtering on all GET endpoints
```

### SDK: swap manual for automatic

```
BEFORE (what you have now):         AFTER (what you're building):
@track_agent                       AgentLens.init(api_key="...")
def my_agent():                    # That's it. Everything below
    # manually log calls           # is automatically captured.
    trace.log_llm_call(...)        response = openai.chat.completions.create(...)
```

### Frontend: 3 pages added

```
EXISTING (not built yet):           NEW (add these):
├── Dashboard                      ├── Login page
├── Execution detail               ├── Signup page
├── Analytics                      ├── Onboarding / API key page
                                   └── Auth state management
```

---

## Revised Timeline: 5 Phases From Here

| Phase | Duration | Focus | Builds On |
|-------|----------|-------|-----------|
| **Phase 2** | ~1 week | Auth system + multi-tenancy | Your existing backend |
| **Phase 3** | ~1 week | Auto-capture SDK (monkey-patching) | Your existing SDK |
| **Phase 4** | ~1.5 weeks | Frontend dashboard + auth pages | Your existing API |
| **Phase 5** | ~1 week | Deployment + seed data + polish | Everything |
| **Phase 6** | ~0.5 week | Documentation + interview prep | Everything |

Total: ~5 weeks from now.

---

## PHASE 2: Authentication + Multi-Tenancy (~1 Week)

**Goal:** Users can sign up, log in, get API keys. Each user only sees their own data.

### Step 1: New Database Tables

Add these two tables alongside your existing ones.

**users table:**
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,                -- UUID
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,         -- bcrypt hashed, NEVER store plain text
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**api_keys table:**
```sql
CREATE TABLE api_keys (
    id TEXT PRIMARY KEY,                -- UUID
    user_id TEXT NOT NULL REFERENCES users(id),
    key_value TEXT UNIQUE NOT NULL,     -- the actual key like "al_k7x9m2abc..."
    name TEXT DEFAULT 'Default',       -- user can name their keys
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_keys_key_value ON api_keys(key_value);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
```

**Modify existing executions table:**
```sql
-- Add this column to your existing executions table
ALTER TABLE executions ADD COLUMN user_id TEXT REFERENCES users(id);

CREATE INDEX idx_executions_user_id ON executions(user_id);
```

**How the API key works:**
- Developer signs up → gets a user account
- They generate an API key → stored in `api_keys` table, linked to their `user_id`
- SDK sends this key in every request header: `X-API-Key: al_k7x9m2...`
- Backend looks up the key → finds the `user_id` → tags the execution with that `user_id`
- Dashboard queries filter by `user_id` → each developer only sees their own data

### Step 2: Auth Endpoints

**New file: `backend/app/routes/auth.py`**

```
POST /api/auth/signup
    Input:  { "email": "dev@company.com", "password": "...", "name": "Satish" }
    Action: Hash password with bcrypt, create user, auto-generate first API key
    Output: { "user_id": "...", "token": "jwt-token-here", "api_key": "al_..." }

POST /api/auth/login
    Input:  { "email": "dev@company.com", "password": "..." }
    Action: Verify password against hash, generate JWT token
    Output: { "token": "jwt-token-here", "user_id": "..." }

GET /api/auth/me
    Input:  JWT token in Authorization header
    Action: Decode token, return user info
    Output: { "user_id": "...", "email": "...", "name": "..." }
```

**New file: `backend/app/routes/keys.py`**

```
POST /api/keys/generate
    Input:  JWT token + { "name": "Production Key" }
    Action: Generate new API key for this user
    Output: { "key": "al_x9k2m7...", "name": "Production Key" }

GET /api/keys
    Input:  JWT token
    Action: List all API keys for this user (masked, show last 4 chars only)
    Output: { "keys": [{ "id": "...", "name": "Production Key", "key_preview": "...m7abc" }] }

DELETE /api/keys/{key_id}
    Input:  JWT token + key_id
    Action: Deactivate the key
    Output: { "status": "deleted" }
```

### Step 3: Auth Middleware

Create a dependency function that protects your existing endpoints.

**Two types of authentication you need:**

```
Type 1: JWT Token (for frontend/dashboard)
    Used by: GET /api/executions, GET /api/stats, etc.
    How: Frontend sends "Authorization: Bearer <jwt-token>" header
    Middleware extracts user_id from the JWT

Type 2: API Key (for SDK/telemetry)
    Used by: POST /api/traces
    How: SDK sends "X-API-Key: al_k7x9m2..." header
    Middleware looks up the key in api_keys table, finds user_id
```

Both resolve to a `user_id`. The difference is just HOW the user_id is determined.

### Step 4: Modify Existing Endpoints

Your existing endpoints need small changes:

**POST /api/traces (receives telemetry from SDK):**
```
BEFORE: Receives data → stores in database
AFTER:  Receives data → validates API key → extracts user_id → stores with user_id
```

**GET /api/executions (dashboard lists executions):**
```
BEFORE: SELECT * FROM executions ORDER BY started_at DESC
AFTER:  SELECT * FROM executions WHERE user_id = :current_user ORDER BY started_at DESC
```

**GET /api/stats (dashboard summary):**
```
BEFORE: SELECT COUNT(*) FROM executions
AFTER:  SELECT COUNT(*) FROM executions WHERE user_id = :current_user
```

The change is adding `WHERE user_id = :current_user` to every query. That one filter is what makes the system multi-tenant.

### Step 5: Generate API Key Format

Use a recognizable prefix so developers know it's an AgentLens key:

```python
import secrets

def generate_api_key():
    random_part = secrets.token_urlsafe(24)  # 32 chars of random
    return f"al_{random_part}"
    # Example output: "al_k7x9m2abcDEF123_ghiJKL456"
```

The `al_` prefix is a common pattern (Stripe uses `sk_`, OpenAI uses `sk-`). It helps developers identify which key belongs to which service.

### Phase 2 Success Criteria

- [ ] Can create a new user account via POST /api/auth/signup
- [ ] Signup returns a JWT token AND a first API key
- [ ] Can log in and get a JWT token
- [ ] Can generate additional API keys
- [ ] POST /api/traces requires a valid API key header
- [ ] POST /api/traces with an invalid key returns 401 Unauthorized
- [ ] GET /api/executions with User A's token shows only User A's data
- [ ] GET /api/executions with User B's token shows only User B's data
- [ ] All your existing tests still pass (with a valid API key added)

### Dependencies to Install

```bash
pip install python-jose[cryptography]   # JWT token creation/verification
pip install passlib[bcrypt]             # Password hashing
```

---

## PHASE 3: Auto-Capture SDK (~1 Week)

**Goal:** Developer adds 2 lines of code. All OpenAI calls are automatically captured.

### Step 1: Understand the Architecture

The auto-capture SDK has three components:

```
┌─────────────────────────────────────────────────────┐
│                    AgentLens SDK                      │
│                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │   Patcher    │  │   Recorder   │  │   Sender    │ │
│  │             │  │              │  │             │ │
│  │ Replaces    │  │ Collects     │  │ Sends data  │ │
│  │ openai      │→ │ events into  │→ │ to backend  │ │
│  │ functions   │  │ a session    │  │ in batches  │ │
│  └─────────────┘  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Patcher:** Replaces `openai.chat.completions.create` (and similar functions) with wrapped versions that record data.

**Recorder:** A global session object that accumulates events (LLM calls, tool calls, errors) in memory.

**Sender:** A background thread that periodically sends accumulated events to your backend via HTTP POST. This is important — you never send data synchronously during an LLM call, because that would slow down the developer's code.

### Step 2: The Init Function

```python
# agentlens/__init__.py

class AgentLens:
    _instance = None  # singleton

    @classmethod
    def init(cls, api_key, endpoint="https://your-backend.onrender.com"):
        cls._instance = cls(api_key, endpoint)
        cls._instance._patch_all()       # monkey-patch LLM clients
        cls._instance._start_sender()    # start background sender thread
        return cls._instance

    def __init__(self, api_key, endpoint):
        self.api_key = api_key
        self.endpoint = endpoint
        self.events = []          # accumulated events
        self.current_execution = None
```

When `AgentLens.init()` runs, two things happen:
1. LLM client functions get replaced with wrapped versions
2. A background thread starts that flushes events to your backend every few seconds

### Step 3: Monkey-Patching OpenAI (Start Simple)

**Start with ONE function: `openai.chat.completions.create` (sync, non-streaming).**

This single function covers the most common use case. Don't try to patch everything at once.

```python
# agentlens/patchers/openai_patcher.py

import time
import openai

def patch_openai(recorder):
    """Replace openai.chat.completions.create with our tracked version."""
    
    original_create = openai.chat.completions.create
    
    def tracked_create(*args, **kwargs):
        start = time.time()
        error = None
        response = None
        
        try:
            # Call the REAL OpenAI function
            response = original_create(*args, **kwargs)
            return response
        except Exception as e:
            error = str(e)
            raise  # Re-raise so developer's error handling still works
        finally:
            # Record the event whether it succeeded or failed
            duration_ms = int((time.time() - start) * 1000)
            
            event = {
                "type": "llm_call",
                "provider": "openai",
                "model": kwargs.get("model", "unknown"),
                "duration_ms": duration_ms,
                "error": error,
            }
            
            # Extract token usage if we got a response
            if response and hasattr(response, "usage") and response.usage:
                event["prompt_tokens"] = response.usage.prompt_tokens
                event["completion_tokens"] = response.usage.completion_tokens
                event["total_tokens"] = response.usage.total_tokens
                event["cost"] = calculate_cost(
                    kwargs.get("model"), 
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
            
            # Add to recorder (thread-safe append)
            recorder.record_event(event)
    
    # Do the actual replacement
    openai.chat.completions.create = tracked_create
```

**Key things to notice:**
- `try/finally` ensures you record data even if the OpenAI call fails
- You `raise` the exception so the developer's code still gets the error
- Token data comes from the response object's `.usage` field
- Cost is calculated by you based on known model pricing
- Recording is a simple list append (fast, non-blocking)

### Step 4: Cost Calculation

You need a lookup table of model prices:

```python
# agentlens/pricing.py

# Prices per 1K tokens (update periodically)
MODEL_PRICING = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
}

def calculate_cost(model, prompt_tokens, completion_tokens):
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return 0.0
    input_cost = (prompt_tokens / 1000) * pricing["input"]
    output_cost = (completion_tokens / 1000) * pricing["output"]
    return round(input_cost + output_cost, 6)
```

### Step 5: Background Sender

Events accumulate in memory. A background thread sends them to your backend every 5 seconds (or when the list hits a certain size).

```python
# agentlens/sender.py

import threading
import requests
import time

class BackgroundSender:
    def __init__(self, endpoint, api_key, flush_interval=5):
        self.endpoint = endpoint
        self.api_key = api_key
        self.flush_interval = flush_interval
        self.events = []
        self.lock = threading.Lock()
        self._running = True
        
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def add_event(self, event):
        with self.lock:
            self.events.append(event)
    
    def _run(self):
        while self._running:
            time.sleep(self.flush_interval)
            self._flush()
    
    def _flush(self):
        with self.lock:
            if not self.events:
                return
            batch = self.events.copy()
            self.events.clear()
        
        try:
            requests.post(
                f"{self.endpoint}/api/traces",
                json={"events": batch},
                headers={"X-API-Key": self.api_key},
                timeout=5
            )
        except Exception:
            pass  # NEVER crash the developer's code
```

**Critical:** The `except Exception: pass` is intentional. If your backend is down, the developer's agent must keep running. You silently drop the telemetry. This is a fundamental principle of observability tools — the monitoring must never affect what it's monitoring.

### Step 6: What the Developer's Experience Looks Like

After you build all of this:

```python
# developer_agent.py — this is the developer's file

from agentlens import AgentLens
import openai

# ONE-TIME SETUP (2 lines)
AgentLens.init(api_key="al_k7x9m2abc123")

# THEIR NORMAL CODE — UNCHANGED
client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Explain quantum computing"}]
)
print(response.choices[0].message.content)

# They run this file: python developer_agent.py
# AgentLens silently records: model, tokens, cost, duration
# Data appears on their dashboard within 5 seconds
```

The developer doesn't call any AgentLens functions after init. They don't wrap anything. They don't log anything. It just works.

### Phased SDK Development (Within This Phase)

**Day 1-2:** Build the basic structure — init, singleton, background sender, event recording.

**Day 3-4:** Build the OpenAI patcher (sync, non-streaming only). Test with a real OpenAI call.

**Day 5:** Handle the execution grouping problem (see below). Test end-to-end.

**Day 6-7:** Add Anthropic patcher (same pattern, different client structure). Buffer time for bugs.

### The Execution Grouping Problem

Your current backend expects data grouped by "execution" — one agent run with multiple LLM calls inside it. But with auto-capture, how do you know which LLM calls belong to the same execution?

**Simplest solution:** Each `AgentLens.init()` creates one execution. All events between init and program exit belong to that execution. The background sender tags all events with the same `execution_id`.

**Better solution (stretch):** Keep the context manager for grouping:

```python
AgentLens.init(api_key="al_...")

# Group 1: Customer support agent
with AgentLens.execution("CustomerSupportAgent"):
    openai.chat.completions.create(...)  # recorded under this execution
    openai.chat.completions.create(...)  # same execution

# Group 2: Research agent
with AgentLens.execution("ResearchAgent"):
    openai.chat.completions.create(...)  # recorded under THIS execution
```

Start with the simple solution. Add execution grouping as an improvement.

### Phase 3 Success Criteria

- [ ] `AgentLens.init(api_key="...")` patches OpenAI client successfully
- [ ] Making an OpenAI call after init automatically records the event
- [ ] Events are sent to backend in background (not blocking the LLM call)
- [ ] Data appears on dashboard within 5-10 seconds
- [ ] If backend is down, developer's code still works normally
- [ ] Cost calculation is correct for at least 3 OpenAI models
- [ ] Anthropic calls are also captured (stretch but recommended)

---

## PHASE 4: Frontend Dashboard + Auth Pages (~1.5 Weeks)

**Goal:** Complete web app with login, signup, onboarding, and data dashboard.

### Page Map

```
agentlens.vercel.app/
├── /login              ← Log in with email/password
├── /signup             ← Create new account
├── /onboarding         ← Shows API key + setup instructions (after signup)
├── /dashboard          ← Main view: stats + execution list (protected)
├── /executions/:id     ← Execution detail with LLM/tool calls (protected)
├── /analytics          ← Charts: cost over time, agents, etc. (protected)
└── /settings           ← Manage API keys (protected)
```

"Protected" means: if you're not logged in, you get redirected to `/login`.

### Step 1: Auth State Management (Day 1)

Store the JWT token in React state (and localStorage for persistence across page refreshes).

```
User logs in → receives JWT token → store in localStorage
Every API call → attach token in header: "Authorization: Bearer <token>"
Page load → check localStorage for token → if exists, user is logged in
Logout → clear localStorage → redirect to /login
```

Create a simple auth context:

```
src/
├── context/
│   └── AuthContext.jsx     ← provides user + token to whole app
├── api/
│   └── client.js           ← attaches JWT to every request automatically
```

### Step 2: Auth Pages (Day 2-3)

**Signup page:**
- Form: name, email, password, confirm password
- On submit: POST /api/auth/signup
- On success: store token, redirect to /onboarding
- Show validation errors inline

**Login page:**
- Form: email, password
- On submit: POST /api/auth/login
- On success: store token, redirect to /dashboard
- Link to signup: "Don't have an account? Sign up"

**Onboarding page (shown once after signup):**
- Big display of their API key: `al_k7x9m2abc123`
- "Copy" button
- Setup instructions:
  ```
  Step 1: pip install agentlens
  Step 2: Add to your code:
          from agentlens import AgentLens
          AgentLens.init(api_key="al_k7x9m2abc123")
  Step 3: Run your agent
  Step 4: Come back here to see your data
  ```
- "Go to Dashboard" button

This onboarding page is important for the portfolio. It shows you think about developer experience, not just code.

### Step 3: Dashboard Page (Day 4-5)

This is the main page developers see. It pulls from your existing endpoints.

**Layout:**
```
┌──────────────────────────────────────────────────────────┐
│  AgentLens                    [Settings] [Logout]        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Total    │ │ Total    │ │ Avg      │ │ Success  │   │
│  │ Runs: 47 │ │ Cost:$12 │ │ 2.3 sec  │ │ Rate:94% │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                          │
│  Recent Executions                    [Search] [Filter]  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Agent Name        Status  Cost   Duration  Time  │   │
│  │ CustomerSupport   ✅      $0.12  1.3s     2m ago │   │
│  │ ResearchAgent     ✅      $0.45  3.1s     5m ago │   │
│  │ CodeReviewer      ❌      $0.08  0.9s     12m ago│   │
│  │ ...                                              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Each row is clickable → navigates to `/executions/:id`.

### Step 4: Execution Detail Page (Day 6)

Shows everything about one agent run:

```
┌──────────────────────────────────────────────────────────┐
│  ← Back to Dashboard                                     │
│                                                          │
│  CustomerSupportAgent                   Status: ✅       │
│  Started: March 20, 2026 2:30 PM       Duration: 1.3s   │
│  Total Cost: $0.12                      Tokens: 450      │
│                                                          │
│  LLM Calls (2)                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │ #1  gpt-4o  Tokens: 280  Cost: $0.08  Dur: 900ms│   │
│  │ #2  gpt-4o  Tokens: 170  Cost: $0.04  Dur: 350ms│   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  Tool Calls (1)                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ #1  search_database  Status: ✅  Duration: 50ms  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Step 5: Analytics Page (Day 7-8)

Charts using Recharts:

- **Cost over time** (line chart) — last 7 / 14 / 30 days
- **Executions per day** (bar chart)
- **Cost by agent** (pie chart or horizontal bar)
- **Success vs failure** (donut chart)
- **Token usage trend** (line chart)

### Step 6: Settings Page (Day 9)

Simple page to manage API keys:

- List existing keys (masked: `al_...abc123`)
- "Generate New Key" button
- "Delete Key" button with confirmation
- Copy button for each key

### Step 7: Polish (Day 10)

- Loading spinners on all data-fetching pages
- Error messages when API calls fail
- Empty states ("No executions yet. Set up the SDK to get started!")
- Mobile-responsive layout
- Protected route wrapper (redirect to login if no token)

### Phase 4 Success Criteria

- [ ] Can sign up and receive an API key
- [ ] Can log in and see dashboard with own data only
- [ ] Onboarding page shows clear setup instructions
- [ ] Dashboard displays stat cards + execution list
- [ ] Execution detail page shows LLM and tool calls
- [ ] Analytics page has at least 3 working charts
- [ ] Settings page shows and manages API keys
- [ ] Unauthenticated users are redirected to login
- [ ] UI is clean and professional

---

## PHASE 5: Deployment + Seed Data + Polish (~1 Week)

**Goal:** Live demo URL that looks like a real product.

### Step 1: Seed Data Script (Day 1)

**Critical for portfolio impact.** Create `scripts/seed_data.py` that:

- Creates a demo user account (email: demo@agentlens.dev)
- Generates an API key for the demo user
- Creates 80-120 realistic executions across 5 agent names:
  - "CustomerSupportAgent" (most common, low cost)
  - "ResearchAssistant" (medium cost, longer duration)
  - "CodeReviewer" (high cost, uses GPT-4)
  - "ContentWriter" (variable cost)
  - "DataAnalyst" (occasional failures)
- Spreads data across the last 30 days
- Includes ~10% failure rate with realistic error messages
- Varies costs, token counts, and durations realistically
- Each execution has 1-4 LLM calls and 0-3 tool calls

When a recruiter visits your dashboard, they should see a month of data that looks like a real team is using the product.

**Optional:** Add a "demo mode" login. On the login page: "Try the demo → [View Demo Dashboard]" that logs in as the demo user. This removes friction for anyone checking out your project.

### Step 2: Backend Deployment — Render (Day 2-3)

1. Create `Dockerfile` for the backend (if not already done)
2. Create Render account, connect GitHub repo
3. Add PostgreSQL database on Render (free tier)
4. Set environment variables:
   - `DATABASE_URL` (Render provides this)
   - `JWT_SECRET` (generate a random string)
   - `CORS_ORIGINS` (your Vercel frontend URL)
5. Deploy, verify `/docs` works at your Render URL
6. Run seed data script against production database

**Important notes:**
- Free tier has 30-second cold starts. Add a note in README.
- Free PostgreSQL expires after 90 days. Set a calendar reminder.
- If you hit issues with WebSockets on free tier, polling is your fallback.

### Step 3: Frontend Deployment — Vercel (Day 3-4)

1. Create Vercel account, connect GitHub repo
2. Set environment variable: `VITE_API_URL=https://your-backend.onrender.com`
3. Deploy, verify all pages work
4. Test the full flow: signup → onboarding → see dashboard

### Step 4: End-to-End Production Test (Day 4-5)

Test this exact sequence on the live URLs:
1. Open the frontend URL in an incognito browser
2. Sign up with a new email
3. Copy the API key from onboarding
4. On your local machine, install the SDK and init with that key
5. Make a real OpenAI call (or simulated one)
6. Go back to the dashboard — does the data appear?
7. Log in as the demo user — do you see the seed data?
8. Log in as your new user — do you see ONLY your data?

### Step 5: Screenshots + Demo (Day 5-6)

Take high-quality screenshots for your README:
1. Login page
2. Onboarding page with API key
3. Dashboard with seed data (the money shot)
4. Execution detail page
5. Analytics charts

Optionally record a 2-minute video walkthrough showing the full flow.

### Phase 5 Success Criteria

- [ ] Backend live at `https://agentlens-api.onrender.com`
- [ ] Frontend live at `https://agentlens.vercel.app`
- [ ] Demo user has 30 days of realistic data
- [ ] Full signup → SDK → dashboard flow works in production
- [ ] Screenshots captured for README
- [ ] Multi-tenant isolation verified (User A can't see User B's data)

---

## PHASE 6: Documentation + Interview Prep (~0.5 Week)

### README.md

Structure:
1. Project name + tagline + screenshot of dashboard
2. "What is AgentLens?" — 3 sentences
3. "Quick Start" — signup, install, init, run
4. Architecture diagram (simple box diagram)
5. Tech stack
6. Local development setup
7. Link to live demo

### docs/architecture.md

Explain the full system. Describe how data flows from SDK to dashboard. Cover the auth system. Explain monkey-patching. Discuss multi-tenancy.

### docs/decisions.md

Write up your design decisions:
- Why FastAPI over Flask?
- Why monkey-patching for auto-capture?
- Why background sender thread instead of synchronous?
- Why JWT + API keys (two auth mechanisms)?
- What would you change with more time?

### Interview Prep — Write Answers To These

**"Walk me through what happens when a developer makes an OpenAI call with AgentLens installed."**

Your answer should trace: init patches the client → wrapped function calls original → captures response metadata → adds event to recorder → background thread flushes to backend → backend validates API key, resolves user_id, stores in DB → frontend polls the API → dashboard updates.

**"How do you ensure the SDK doesn't affect the developer's application?"**

Answer: try/finally in the wrapper (always returns/raises the original result), background thread for sending (non-blocking), broad except in sender (never crashes), daemon thread (exits with the program).

**"How does multi-tenancy work?"**

Answer: API key in header → lookup in api_keys table → resolve to user_id → tag execution → all queries filter by user_id. Explain that this is row-level security at the application layer.

**"What would you do differently at scale?"**

Answer: Message queue (Redis/Kafka) between SDK and backend, time-series database instead of PostgreSQL, connection pooling, rate limiting per API key, async ingestion endpoint.

---

## Updated Project Structure

```
agentlens/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── decisions.md
│   └── screenshots/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app + CORS + startup
│   │   ├── config.py                # Settings
│   │   ├── database.py              # SQLAlchemy engine + session
│   │   ├── models.py                # All models (existing + users, api_keys)
│   │   ├── schemas.py               # All Pydantic schemas
│   │   ├── auth.py                  # JWT creation/verification + API key lookup
│   │   ├── dependencies.py          # get_current_user, get_user_from_api_key
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── traces.py            # POST /api/traces (MODIFIED: add API key auth)
│   │       ├── executions.py        # GET endpoints (MODIFIED: add user filtering)
│   │       ├── stats.py             # GET /api/stats (MODIFIED: add user filtering)
│   │       ├── auth_routes.py       # NEW: signup, login, me
│   │       └── keys.py              # NEW: generate, list, delete API keys
│   ├── scripts/
│   │   └── seed_data.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js            # MODIFIED: attach JWT to all requests
│   │   ├── context/
│   │   │   └── AuthContext.jsx       # NEW: auth state management
│   │   ├── components/
│   │   │   ├── StatCard.jsx
│   │   │   ├── ExecutionTable.jsx
│   │   │   ├── ExecutionDetail.jsx
│   │   │   ├── CostChart.jsx
│   │   │   ├── ProtectedRoute.jsx   # NEW: redirects to login if not authed
│   │   │   └── ApiKeyDisplay.jsx    # NEW: shows API key with copy button
│   │   ├── pages/
│   │   │   ├── Login.jsx            # NEW
│   │   │   ├── Signup.jsx           # NEW
│   │   │   ├── Onboarding.jsx       # NEW
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ExecutionPage.jsx
│   │   │   ├── Analytics.jsx
│   │   │   └── Settings.jsx         # NEW: API key management
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── sdk/
│   ├── agentlens/
│   │   ├── __init__.py              # MODIFIED: AgentLens.init() with auto-capture
│   │   ├── client.py                # EXISTING: HTTP client
│   │   ├── trace.py                 # EXISTING: still works for manual mode
│   │   ├── sender.py                # NEW: background thread sender
│   │   ├── pricing.py               # NEW: model cost calculation
│   │   └── patchers/
│   │       ├── __init__.py
│   │       ├── openai_patcher.py    # NEW: monkey-patch OpenAI
│   │       └── anthropic_patcher.py # NEW: monkey-patch Anthropic (stretch)
│   ├── pyproject.toml
│   └── README.md
│
└── examples/
    ├── simple_agent.py              # EXISTING: still works
    ├── auto_capture_demo.py         # NEW: shows the 2-line experience
    └── seed_data.py
```

Files marked **EXISTING** = keep as-is.  
Files marked **MODIFIED** = small changes to add auth/filtering.  
Files marked **NEW** = build from scratch.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| JWT/auth is new territory | Use `python-jose` + `passlib` — well-documented, lots of FastAPI tutorials cover this exact pattern |
| Monkey-patching breaks with new OpenAI SDK versions | Pin OpenAI SDK version in your requirements; note compatible versions in README |
| Async OpenAI calls not captured | Start with sync only; add async patching as a stretch goal; document the limitation |
| Streaming responses not captured | Start with non-streaming only; document that streaming support is planned |
| Render cold starts ruin demo | Add "demo mode" button on login that skips the cold backend entirely (shows cached data) or add README note |
| Free PostgreSQL expires (90 days) | Keep seed script ready; set calendar reminder; budget $7/month if job-hunting |

---

**END OF UPDATED IMPLEMENTATION PLAN**
