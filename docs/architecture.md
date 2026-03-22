# AgentLens Architecture

## 1. System Overview

AgentLens is an observability platform for AI agents. It captures telemetry from LLM API calls (OpenAI, Anthropic) in a developer's application and surfaces that data through a web dashboard for cost tracking, performance analysis, and debugging.

The system consists of three components:

- **SDK** (`sdk/agentlens/`): A Python package installed in the developer's application. It monkey-patches LLM client libraries to transparently intercept API calls, record token usage, cost, and latency, then ship the data to the backend via a background thread.
- **Backend** (`backend/app/`): A FastAPI service that ingests telemetry from the SDK, stores it in a relational database, and serves it to the frontend through REST endpoints. It handles two authentication mechanisms: API keys for the SDK and Auth0 JWTs for the dashboard.
- **Frontend** (`frontend/src/`): A React single-page application that authenticates via Auth0, fetches data from the backend, and renders dashboards, execution detail views, analytics charts, and settings management.

### High-Level Data Flow

```
Developer's Python Code
        |
        | AgentLens.init(api_key="al_xxx")
        v
+------------------+
|  SDK (in-process) |
|  - Monkey-patches |
|    OpenAI/Anthropic|
|  - EventRecorder  |
|  - BackgroundSender|
+--------+---------+
         |
         | POST /api/traces (X-API-Key header)
         | every 5 seconds (batched)
         v
+------------------+
|  FastAPI Backend  |
|  - Validates key  |
|  - Resolves user  |
|  - Stores in DB   |
+--------+---------+
         |
         | SQLAlchemy ORM
         v
+------------------+
|  Database         |
|  SQLite (dev)     |
|  PostgreSQL (prod)|
+--------+---------+
         ^
         |
         | GET /api/executions, /api/stats
         | (Authorization: Bearer <Auth0 JWT>)
         |
+------------------+
|  React Frontend   |
|  - Auth0 login    |
|  - Dashboard      |
|  - Analytics      |
|  - Settings       |
+------------------+
```

---

## 2. Data Flow

This section traces a single LLM call from the developer's code to the dashboard.

### Step 1: SDK Initialization

The developer calls `AgentLens.init(api_key="al_xxx")` at application startup. This is a class method that:

1. Creates a singleton `AgentLens` instance.
2. Instantiates an `EventRecorder` (thread-safe event buffer).
3. Instantiates a `BackgroundSender` (daemon thread for shipping events).
4. Calls `patch_openai(recorder)` and `patch_anthropic(recorder)` to monkey-patch installed LLM libraries.

### Step 2: Monkey-Patching

The SDK patches the `__init__` method of `openai.OpenAI` (and `openai.AsyncOpenAI`, `anthropic.Anthropic`, `anthropic.AsyncAnthropic`). When the developer instantiates an LLM client, the patched `__init__`:

1. Calls the original `__init__` to create the client normally.
2. Saves a reference to the original `chat.completions.create` (OpenAI) or `messages.create` (Anthropic).
3. Replaces it with a wrapper function that intercepts calls.

The developer's code is unaware of the patch. All calls behave identically from the developer's perspective.

### Step 3: LLM Call Interception

When the developer calls `client.chat.completions.create(model="gpt-4o", ...)`, the wrapper function:

1. Records `time.monotonic()` at the start.
2. Calls the original function.
3. Extracts token usage from the response object (`response.usage.prompt_tokens`, `response.usage.completion_tokens`). For Anthropic, the fields are `input_tokens` and `output_tokens`.
4. Calculates cost using a pricing lookup table in `pricing.py` (per-1K-token rates for each model).
5. Computes `duration_ms` from the monotonic clock delta.
6. Calls `recorder.record_llm_call(provider, model, tokens, cost, duration_ms, error)`.

If the LLM call raises an exception, the wrapper records the error string and re-raises the exception. The developer's error handling is never disrupted.

### Step 4: Event Recording

`EventRecorder.record_llm_call()` creates a dict with all telemetry fields (UUID, execution_id, agent_name, provider, model, tokens, cost, duration, timestamp) and appends it to an internal list under a `threading.Lock`. This is thread-safe for multi-threaded applications.

Events are grouped by execution. The developer can explicitly group calls using the `AgentLens.execution("AgentName")` context manager, which sets `_current_execution_id` and `_current_agent_name` on the recorder. If no context manager is used, a default execution ID is auto-generated.

### Step 5: Background Flush

`BackgroundSender` runs a daemon thread that wakes every `flush_interval` seconds (default: 5). On each tick:

1. Calls `recorder.flush()` to atomically drain the event buffer.
2. Groups events by `execution_id`.
3. For each execution, constructs a trace payload: execution metadata (agent_name, status, started_at, completed_at, duration_ms, total_cost, total_tokens) plus arrays of `llm_calls` and `tool_calls`.
4. Sends the payload via `POST /api/traces` with the `X-API-Key` header.

An `atexit` hook calls `_final_flush()` to ship any remaining events when the program exits. All send operations are wrapped in bare `except` blocks to guarantee the SDK never crashes the developer's code.

### Step 6: Backend Ingestion

The `POST /api/traces` endpoint (`backend/app/routes/traces.py`):

1. Extracts the `X-API-Key` header via the `get_user_from_api_key` dependency.
2. Looks up the key in the `api_keys` table. If invalid or inactive, returns 401.
3. Resolves the `user_id` from the API key record.
4. Checks for duplicate `execution.id` (idempotency guard, returns 409 if exists).
5. Creates an `Execution` row with the resolved `user_id`.
6. Creates `LLMCall` rows and `ToolCall` rows linked to the execution.
7. Commits the transaction.

### Step 7: Frontend Display

The React frontend authenticates via Auth0 and obtains an access token. The `ApiClient` attaches this token as `Authorization: Bearer <token>` on all requests. The backend's `get_current_user` dependency verifies the JWT using Auth0's JWKS (RS256) and resolves the local `User` record.

Dashboard pages fetch data from:

- `GET /api/stats` -- aggregate metrics (total executions, total cost, avg duration, success rate, LLM calls count, executions today).
- `GET /api/executions` -- paginated list of executions with their LLM calls and tool calls.
- `GET /api/executions/:id` -- single execution detail with all child records.

All queries filter by `user_id = current_user.id`, enforcing multi-tenancy at the application layer.

---

## 3. Authentication Architecture

AgentLens uses two independent authentication mechanisms that converge on the same `user_id`.

### Auth0 JWT (Frontend/Dashboard)

Used by the React frontend to authenticate human users.

**Flow:**

1. User clicks "Login with Google" or "Login with GitHub" on the Login page.
2. `Auth0Provider` (from `@auth0/auth0-react`) redirects to Auth0's Universal Login page.
3. Auth0 authenticates the user via the selected social provider.
4. Auth0 redirects back to the app with an authorization code.
5. The Auth0 SDK exchanges the code for an access token (RS256 JWT).
6. `AuthContext` calls `getAccessTokenSilently()` to obtain the token.
7. `api.setToken(token)` stores the token on the API client singleton.
8. `api.getMe()` calls `GET /api/auth/me` with `Authorization: Bearer <token>`.
9. The backend's `get_current_user` dependency:
   - Strips the "Bearer " prefix.
   - Calls `verify_auth0_token(token)` which fetches Auth0's JWKS endpoint (`/.well-known/jwks.json`), finds the signing key matching the token's `kid` header, and verifies the RS256 signature against Auth0's public key.
   - Validates `audience` (must match `AUTH0_AUDIENCE`) and `issuer` (must match `AUTH0_ISSUER`).
   - Extracts the `sub` claim (e.g., `"google-oauth2|12345"`).
   - Queries `users` table by `auth0_sub`.
   - If no user exists (first login), performs JIT provisioning: creates a `User` row and a default `ApiKey`, commits, and returns the new user.

**JWKS caching:** The JWKS response is cached via `@lru_cache(maxsize=1)`. On key mismatch (e.g., after Auth0 key rotation), the cache is cleared and the JWKS is re-fetched once.

### API Key (SDK/Telemetry)

Used by the Python SDK to authenticate programmatic telemetry ingestion.

**Flow:**

1. The SDK sends `X-API-Key: al_k7x9m2abc123` on every `POST /api/traces` request.
2. The backend's `get_user_from_api_key` dependency queries the `api_keys` table for a matching `key_value` where `is_active = True`.
3. Returns the associated `User` via the `ApiKey.user` relationship.

**Key format:** All API keys use an `al_` prefix (similar to Stripe's `sk_` convention) for easy identification.

### Convergence

Both mechanisms resolve to the same `User` record. A developer who logs into the dashboard via Auth0 and sends telemetry via an API key sees a unified view -- the `user_id` on executions (written via API key auth) matches the `user_id` used in dashboard queries (resolved via JWT auth).

---

## 4. Multi-Tenancy

AgentLens implements multi-tenancy through application-layer row-level filtering. There is no database-level row-level security (RLS) policy; instead, every query explicitly includes a `user_id` filter.

### Isolation Mechanism

Every database query that returns user-facing data includes a `WHERE user_id = :current_user_id` clause:

- `GET /api/executions`: `db.query(Execution).filter(Execution.user_id == user.id)`
- `GET /api/stats`: All aggregate functions filter by `Execution.user_id == user.id`
- `GET /api/keys`: `db.query(ApiKey).filter(ApiKey.user_id == user.id)`

### Write-Side Isolation

When the SDK sends a trace via `POST /api/traces`, the backend resolves the API key to a `user_id` and stamps it on the `Execution` record. There is no way for the SDK to specify a different `user_id` -- it is always derived from the authenticated API key.

### Access Control

- Users can only read their own executions, stats, and API keys.
- Users can only create and delete their own API keys.
- There is no admin role or cross-tenant access at this time.

---

## 5. SDK Architecture

The SDK lives in `sdk/agentlens/` and is designed to be installed alongside the developer's application as a pip package.

### Core Design Principles

1. **Zero-code instrumentation**: After `AgentLens.init()`, all LLM calls are automatically captured. The developer writes no logging code.
2. **Silent failure**: The SDK never throws exceptions that could crash the developer's application. All network calls and event processing are wrapped in broad `except` blocks.
3. **Non-blocking**: Telemetry is shipped in a background daemon thread. LLM call latency is unaffected (the only overhead is the in-memory event recording, which is sub-millisecond).

### Module Breakdown

**`client.py` -- AgentLens class**

- `AgentLens.init(api_key, endpoint, flush_interval)`: Class method. Creates a singleton instance, initializes the recorder and sender, and patches LLM libraries. Returns the instance.
- `AgentLens.execution(agent_name)`: Class method returning an `_ExecutionContext` context manager. Sets `_current_execution_id` and `_current_agent_name` on the recorder for the duration of the `with` block.
- `AgentLens.shutdown()`: Stops the background sender and performs a final flush.
- Manual mode: `AgentLens(api_key=...)` instance with `lens.trace("AgentName")` context manager for explicit logging.

**`recorder.py` -- EventRecorder**

- Thread-safe event buffer using `threading.Lock`.
- `record_llm_call(provider, model, tokens, cost, duration_ms, error)`: Appends an event dict to the internal list.
- `record_tool_call(tool_name, duration_ms, status, error_message)`: Same pattern for tool calls.
- `flush()`: Atomically drains and returns all buffered events.
- `start_execution(agent_name)` / `end_execution()`: Manage the current execution context for event grouping.

**`sender.py` -- BackgroundSender**

- Daemon thread (`threading.Thread(daemon=True)`) that sleeps for `flush_interval` seconds between flushes.
- Groups flushed events by `execution_id` and constructs one trace payload per execution.
- Sends via `httpx.Client.post()` to `POST /api/traces`.
- `atexit.register(self._final_flush)` ensures remaining events are sent on program exit.
- All HTTP errors are silently swallowed.

**`patchers/openai_patcher.py`**

- `patch_openai(recorder)`: Replaces `openai.OpenAI.__init__` with a version that, after calling the original init, wraps `self.chat.completions.create` with a tracking wrapper.
- `_wrap_create(original_fn, recorder, provider, *args, **kwargs)`: The wrapper function. Records start time, calls the original, extracts `response.usage`, calculates cost via `pricing.calculate_cost()`, and calls `recorder.record_llm_call()`.
- Async variant: Similarly patches `openai.AsyncOpenAI.__init__` and wraps with an async wrapper.

**`patchers/anthropic_patcher.py`**

- Same pattern as the OpenAI patcher, adapted for Anthropic's API surface:
  - Patches `anthropic.Anthropic.__init__` to wrap `self.messages.create`.
  - Token fields: `response.usage.input_tokens` and `response.usage.output_tokens` (vs. OpenAI's `prompt_tokens` / `completion_tokens`).

**`pricing.py`**

- `MODEL_PRICING` dict mapping model names to per-1K-token input/output rates.
- `calculate_cost(model, prompt_tokens, completion_tokens)`: Looks up pricing by exact match, then by prefix match (e.g., `gpt-4o-2024-08-06` matches `gpt-4o`). Returns `0.0` for unknown models.

---

## 6. Database Schema

The database uses five tables. SQLite is used for local development; PostgreSQL is used in production. SQLAlchemy ORM provides database-agnostic access.

### Tables

**`users`**

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | String | PK | UUID as string |
| email | String | UNIQUE, NOT NULL | User email |
| password_hash | String | NULLABLE | Unused for Auth0 users |
| auth0_sub | String | UNIQUE, NULLABLE | Auth0 user ID (e.g., `google-oauth2|12345`) |
| name | String | NULLABLE | Display name |
| created_at | DateTime | server_default=now() | Account creation timestamp |

**`api_keys`**

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | String | PK | UUID |
| user_id | String | FK -> users.id, NOT NULL | Owning user |
| key_value | String | UNIQUE, NOT NULL | The key string (e.g., `al_k7x9m2...`) |
| name | String | default="Default" | Human-readable label |
| is_active | Boolean | default=True | Soft-delete flag |
| created_at | DateTime | server_default=now() | Creation timestamp |

Indexes: `idx_api_keys_key_value` (key lookup), `idx_api_keys_user_id` (user's keys).

**`executions`**

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | String | PK | UUID (generated by SDK) |
| user_id | String | FK -> users.id, NULLABLE | Owning user (resolved from API key) |
| agent_name | String | NOT NULL | e.g., "CustomerSupportAgent" |
| status | String | default="running" | running, completed, or failed |
| started_at | DateTime | NOT NULL | First event timestamp |
| completed_at | DateTime | NULLABLE | Last event timestamp |
| duration_ms | Integer | NULLABLE | Total execution duration |
| total_cost | Float | default=0.0 | Sum of all LLM call costs |
| total_tokens | Integer | default=0 | Sum of all token usage |
| error_message | Text | NULLABLE | Error details if failed |
| metadata_json | Text | NULLABLE | Arbitrary JSON metadata |
| created_at | DateTime | server_default=now() | Record creation timestamp |

Indexes: `idx_executions_agent_name`, `idx_executions_started_at`, `idx_executions_user_id`.

**`llm_calls`**

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | String | PK | UUID (generated by SDK) |
| execution_id | String | FK -> executions.id, NOT NULL | Parent execution |
| provider | String | NULLABLE | openai, anthropic, etc. |
| model | String | NULLABLE | gpt-4o, claude-3-5-sonnet, etc. |
| prompt_tokens | Integer | NULLABLE | Input token count |
| completion_tokens | Integer | NULLABLE | Output token count |
| total_tokens | Integer | NULLABLE | Sum of input + output |
| cost | Float | NULLABLE | Calculated cost in USD |
| duration_ms | Integer | NULLABLE | Call latency |
| timestamp | DateTime | NULLABLE | When the call was made |
| created_at | DateTime | server_default=now() | Record creation timestamp |

Index: `idx_llm_calls_execution_id`.

**`tool_calls`**

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | String | PK | UUID |
| execution_id | String | FK -> executions.id, NOT NULL | Parent execution |
| tool_name | String | NULLABLE | e.g., "search_database" |
| duration_ms | Integer | NULLABLE | Call duration |
| status | String | NULLABLE | success or error |
| error_message | Text | NULLABLE | Error details |
| timestamp | DateTime | NULLABLE | When the call was made |
| created_at | DateTime | server_default=now() | Record creation timestamp |

Index: `idx_tool_calls_execution_id`.

### Relationships

```
User 1──* ApiKey
User 1──* Execution
Execution 1──* LLMCall
Execution 1──* ToolCall
```

Cascade delete is configured on `User -> ApiKey` and `Execution -> LLMCall/ToolCall`.

---

## 7. Frontend Architecture

The frontend is a React 18 SPA built with Vite, using JSX components and TailwindCSS for styling.

### Component Hierarchy

```
main.jsx
  BrowserRouter
    Auth0Provider (domain, clientId, audience from env vars)
      AuthProvider (context/AuthContext.jsx)
        App (App.jsx — route definitions)
          /login          -> Login
          ProtectedRoute
            Layout (sidebar + outlet)
              /onboarding   -> Onboarding
              /dashboard    -> Dashboard
              /executions/:id -> ExecutionPage
              /analytics    -> Analytics
              /settings     -> Settings
          /*              -> Navigate to /login
```

### Authentication Flow

1. `main.jsx` wraps the app in `Auth0Provider` with configuration from `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, and `VITE_AUTH0_AUDIENCE` environment variables.
2. `AuthProvider` (in `context/AuthContext.jsx`) bridges Auth0 with the application:
   - Listens for `isAuthenticated` state from the `useAuth0` hook.
   - On authentication, calls `getAccessTokenSilently()` to obtain the Auth0 access token.
   - Calls `api.setToken(token)` to configure the API client.
   - Calls `api.getMe()` to sync with the backend (triggers JIT user creation on first login).
   - Merges Auth0 profile data (name, picture) with backend user data (id, created_at).
   - Falls back to Auth0-only data if the backend is unreachable.
3. `ProtectedRoute` checks `isAuthenticated` and redirects to `/login` if not authenticated.

### API Client

`api/client.js` exports a singleton `ApiClient` instance. Key behavior:

- `setToken(token)`: Called by `AuthContext` after Auth0 login.
- `request(path, options)`: Attaches `Authorization: Bearer <token>` to all requests. Parses error responses and throws with the `detail` field.
- Methods: `getMe()`, `getExecutions()`, `getExecution(id)`, `getStats()`, `getApiKeys()`, `createApiKey(name)`, `deleteApiKey(id)`.

### Pages

- **Login**: Social login buttons (Google, GitHub) that trigger Auth0 redirect.
- **Dashboard**: Summary stats (via `getStats()`) displayed in `StatCard` components, plus a recent executions table (`ExecutionTable`).
- **ExecutionPage**: Detail view for a single execution, showing its LLM calls and tool calls.
- **Analytics**: Charts and trends across executions.
- **Settings**: API key management (create, view, delete) and profile information.
- **Onboarding**: First-time user setup guide showing the API key and SDK installation instructions.
