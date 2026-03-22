# AgentLens -- Design Decisions

This document explains the key architectural and engineering decisions behind AgentLens, an AI agent observability platform. Each section covers what was chosen, what alternatives exist, and why the chosen approach fits this system.

---

## 1. FastAPI over Flask or Django

**Decision:** Use FastAPI as the backend framework.

**Why:**

- **Async-native.** LLM observability involves receiving bursts of telemetry data from SDKs. FastAPI's async request handling (built on Starlette and uvicorn) allows the ingestion endpoint to handle concurrent requests without blocking on I/O, which matters when writing to a database while accepting new events.
- **Automatic OpenAPI documentation.** Every endpoint gets a generated OpenAPI spec and interactive Swagger UI with zero additional code. This is valuable for a platform where third-party SDKs need to know the exact request/response contracts.
- **Pydantic validation built in.** Request and response models are validated and serialized automatically. This eliminates an entire class of bugs around malformed telemetry payloads -- if an SDK sends bad data, FastAPI rejects it before it reaches application code.
- **Dependency injection.** FastAPI's `Depends()` system cleanly handles cross-cutting concerns like authentication, database sessions, and tenant resolution without decorators stacking up or global state.
- **Performance.** FastAPI consistently benchmarks faster than Flask and Django for JSON-heavy workloads, which is the primary traffic pattern for a telemetry ingestion API.

**Why not Flask:** Flask lacks native async support and requires extensions for validation, OpenAPI docs, and dependency injection. For a new project with no legacy constraints, there is no reason to assemble those pieces manually.

**Why not Django:** Django's ORM, admin panel, and template engine are designed for traditional web applications. AgentLens is an API-first platform with a separate React frontend -- Django's batteries would be overhead rather than an advantage.

---

## 2. Monkey-patching for Auto-Capture Instead of Decorators or Wrappers

**Decision:** The AgentLens SDK captures LLM calls by monkey-patching the `openai` and `anthropic` client libraries at import time, rather than requiring developers to use custom wrapper functions or decorators.

**Why:**

- **Zero-change developer experience.** The integration requires exactly two lines of code: `import agentlens` and `agentlens.init(api_key="...")`. After that, every `openai.ChatCompletion.create()` or `anthropic.Anthropic().messages.create()` call is automatically captured. Developers do not modify their existing LLM calls at all.
- **Captures everything automatically.** With decorators or wrappers, developers must remember to annotate every call site. In a codebase with LLM calls spread across multiple modules (agents, chains, tools), it is easy to miss one. Monkey-patching intercepts at the library level, so nothing is missed.
- **Industry-standard pattern.** This is the same approach used by Datadog (`ddtrace`), New Relic, Sentry, and OpenTelemetry auto-instrumentation. It is a well-understood technique with known tradeoffs, not a novel hack.
- **Preserves the original API.** The patched methods call the original implementation and return the same objects. From the developer's perspective, the SDK is invisible -- `openai.chat.completions.create()` still returns a `ChatCompletion` object with all the same attributes.

**Tradeoff acknowledged:** Monkey-patching is fragile across library version changes. If OpenAI restructures their client internals, the patch points may break. This is mitigated by pinning supported library versions and testing against them in CI.

---

## 3. Background Sender Thread Instead of Synchronous HTTP

**Decision:** Captured LLM events are queued in memory and sent to the AgentLens backend by a background daemon thread, rather than being sent synchronously after each LLM call.

**Why:**

- **Never slows down the developer's code.** The primary design constraint is that adding observability must not increase the latency of LLM calls. If the SDK sent telemetry synchronously after each call, a slow network or a backend outage would directly impact the developer's application. The background thread decouples capture from transmission entirely.
- **Batching for efficiency.** The sender thread accumulates events and sends them in batches rather than one HTTP request per event. This reduces connection overhead and is friendlier to both the network and the backend ingestion endpoint.
- **Daemon thread lifecycle.** The sender thread is marked as a daemon thread, which means it exits automatically when the main program exits. This prevents the SDK from keeping a process alive after the developer's code has finished.
- **atexit hook for final flush.** Python's `atexit` module registers a callback that flushes any remaining queued events before the process terminates. This ensures that the last batch of events is not silently lost.
- **Failure isolation.** If the AgentLens backend is unreachable, events are dropped silently (with a logged warning) rather than raising exceptions in the developer's code. Observability should never break the system it observes.

---

## 4. Two Authentication Mechanisms: Auth0 JWT and API Keys

**Decision:** The platform supports two distinct authentication paths -- Auth0 JWT tokens for the frontend dashboard, and static API keys (prefixed with `al_`) for the SDK.

**Why:**

- **Different contexts demand different auth flows.** A user logging into the web dashboard expects an OAuth flow: click "Sign in with Google," get redirected, land on their dashboard. A developer integrating the SDK into their Python script expects to paste a static string into their code or environment variable. These are fundamentally different interaction patterns.
- **Both resolve to the same identity.** Whether a request arrives with a JWT Bearer token or an `X-API-Key` header, the backend resolves it to the same `user_id`. This means the SDK sends events attributed to a user, and the dashboard queries events for that same user. The two auth paths converge at the data layer.
- **API key prefix (`al_`) for identification.** The `al_` prefix serves two purposes: it makes AgentLens keys visually distinguishable from other API keys in a developer's environment (OpenAI keys start with `sk-`, Anthropic keys start with `sk-ant-`), and it allows secret scanning tools like GitHub's to identify leaked keys by prefix pattern.
- **Separation of concerns in middleware.** The backend uses a single `get_current_user` dependency that checks for a JWT first, then falls back to API key lookup. This keeps route handlers completely unaware of which auth mechanism was used.

---

## 5. Auth0 Instead of Custom Authentication

**Decision:** Delegate authentication to Auth0 rather than building a custom username/password system.

**Why:**

- **No password storage liability.** Storing passwords means handling hashing (bcrypt/argon2), salting, reset flows, brute-force protection, and breach notification obligations. Auth0 handles all of this. For a portfolio project that may be deployed publicly, eliminating this attack surface is significant.
- **Social logins with zero code.** Google and GitHub OAuth are configured in the Auth0 dashboard, not in application code. Adding a new identity provider (e.g., Microsoft) requires no backend changes.
- **Industry-standard OAuth2/OIDC.** Auth0 issues standard JWTs with standard claims. The backend validates them using the JWKS endpoint, which is a well-documented, widely-understood pattern. Any developer reading the code will recognize the flow immediately.
- **Free tier covers the relevant scale.** Auth0's free tier supports up to 25,000 monthly active users, which is far beyond what a portfolio project will encounter. There is no cost pressure to build a custom alternative.

**Tradeoff acknowledged:** Auth0 introduces a third-party dependency and requires network calls to validate tokens (or JWKS caching). For this project's scale, the operational simplicity outweighs the latency cost of token validation.

---

## 6. SQLite for Development

**Decision:** Use SQLite as the development database, with PostgreSQL for production, both accessed through the same SQLAlchemy models.

**Why:**

- **Zero setup for local development.** SQLite requires no server process, no Docker container, no credentials. Running the backend locally creates a single `.db` file. This reduces the barrier to contribution and makes the test suite fast to run.
- **Easy to reset.** Deleting the `.db` file and restarting the application gives a clean database. During active development and testing, this is faster than truncating tables or rebuilding a PostgreSQL container.
- **Same ORM, different engine.** SQLAlchemy abstracts the database engine behind a connection URL. The models, queries, and relationships are identical between SQLite and PostgreSQL. Switching between them is a one-line configuration change (`DATABASE_URL`).
- **Works everywhere.** SQLite is included in Python's standard library. There are no platform-specific installation steps, which matters when development happens across different machines.

**Tradeoff acknowledged:** SQLite lacks concurrent write support, JSON operators, and some PostgreSQL-specific features. Any query that relies on PostgreSQL-specific syntax must be tested against PostgreSQL in CI before deployment.

---

## 7. Row-Level Multi-Tenancy Instead of Database-Per-Tenant

**Decision:** All tenants (users) share a single database. Tenant isolation is enforced by adding `WHERE user_id = :current_user` to every query.

**Why:**

- **Simplicity at this scale.** Database-per-tenant requires dynamic connection management, per-tenant migrations, and operational tooling to provision and tear down databases. For a platform with tens to hundreds of users, this complexity is not justified.
- **Single migration path.** Schema changes are applied once to one database. With database-per-tenant, every migration must be applied to every tenant database, which introduces coordination complexity and failure modes.
- **Single connection pool.** The backend maintains one database connection pool rather than one per tenant. This is simpler to configure, monitor, and scale.
- **Query simplicity.** The `get_current_user` dependency injects the authenticated user ID, and every database query filters by it. This pattern is easy to audit -- grep for queries that are missing the `user_id` filter.

**Tradeoff acknowledged:** A bug that omits the `user_id` filter could leak data across tenants. This risk is mitigated by centralizing data access in repository functions that always accept `user_id` as a required parameter, making it hard to accidentally skip the filter.

---

## 8. React + Vite Instead of Next.js

**Decision:** The frontend dashboard is a React single-page application (SPA) built with Vite, not a Next.js application.

**Why:**

- **No server-side rendering needed.** The dashboard is a private, authenticated application. There is no public content to index, no SEO requirement, and no need for server-rendered HTML. SSR would add complexity (server management, hydration issues) without any benefit.
- **Faster development server.** Vite's hot module replacement (HMR) is near-instant, which matters during active frontend development. Next.js's dev server is slower due to its compilation pipeline for SSR and API routes.
- **Simpler deployment.** A Vite build produces static files (`dist/`) that can be served by any HTTP server or CDN. There is no Node.js runtime to manage in production. The frontend is served alongside the FastAPI backend or from a static file host.
- **Clear separation of concerns.** The frontend is purely a client-side application that communicates with the FastAPI backend via REST API calls. There is no blending of server and client code, which keeps the architecture easier to reason about.

---

## 9. Thread-Safe EventRecorder with Lock

**Decision:** The `EventRecorder` class in the SDK uses a `threading.Lock` to guard access to the internal events list.

**Why:**

- **Concurrent LLM calls are common.** Modern AI agent frameworks (LangGraph, CrewAI, AutoGen) make concurrent LLM calls -- for example, running multiple tool calls in parallel or evaluating multiple candidates simultaneously. The monkey-patched methods will be invoked from different threads or async tasks, all appending to the same events list.
- **Python lists are not thread-safe for compound operations.** While CPython's GIL protects individual list operations, the capture logic involves a read-modify-append pattern (check state, build event dict, append to list) that is not atomic. Without a lock, concurrent appends could interleave in ways that corrupt event data.
- **Lock overhead is negligible.** Acquiring an uncontested lock in Python takes microseconds. Compared to the latency of an LLM API call (typically 500ms to 5s), the lock acquisition time is effectively zero.
- **Correctness over cleverness.** A lock-free approach (e.g., using `queue.Queue`) was considered, but a simple `Lock` is more readable, easier to reason about, and sufficient for the expected concurrency level.

---

## 10. What Would Change at Scale

The current architecture is designed for a portfolio project and early-stage usage. At production scale (thousands of users, millions of events per day), several components would need to change:

**Message queue between SDK and backend.** Replace direct HTTP ingestion with a message queue (Redis Streams, Apache Kafka, or AWS SQS). This decouples event production from consumption, handles traffic spikes via buffering, and enables replay of failed events. The SDK would publish to the queue, and a separate consumer service would write to the database.

**Time-series database.** Replace PostgreSQL for event storage with a time-series optimized database (ClickHouse, TimescaleDB, or Apache Druid). LLM telemetry data is append-heavy and queried by time range -- workloads that time-series databases handle orders of magnitude more efficiently than general-purpose relational databases.

**Connection pooling.** Add PgBouncer or a similar connection pooler in front of the database to handle thousands of concurrent backend instances sharing a limited number of database connections.

**Rate limiting per API key.** Implement token bucket or sliding window rate limiting on the ingestion endpoint, keyed by API key. This prevents a single misconfigured SDK integration from overwhelming the backend. The current implementation has no rate limiting.

**Async ingestion endpoint.** Move the ingestion endpoint to a fully async pipeline: accept the event, validate it, enqueue it, and return 202 Accepted immediately. The actual database write happens asynchronously via a background worker. This reduces p99 latency on the ingestion path.

**WebSocket for real-time dashboard updates.** Replace polling-based dashboard updates with WebSocket connections. When a new event is ingested, push it to connected dashboard clients immediately. This enables real-time trace visualization without the latency and overhead of polling.

---

*This document reflects the state of the system as of March 2026. Decisions are revisited as requirements and scale evolve.*
