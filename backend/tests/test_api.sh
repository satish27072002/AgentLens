#!/bin/bash
# ─────────────────────────────────────────────
# AgentLens API Smoke Tests
# Run with: bash tests/test_api.sh
# Requires: server running on localhost:8000
# ─────────────────────────────────────────────

BASE_URL="http://localhost:8000"
PASS=0
FAIL=0

check() {
    local description="$1"
    local expected_code="$2"
    local actual_code="$3"

    if [ "$actual_code" -eq "$expected_code" ]; then
        echo "✅ PASS: $description (HTTP $actual_code)"
        PASS=$((PASS + 1))
    else
        echo "❌ FAIL: $description (expected $expected_code, got $actual_code)"
        FAIL=$((FAIL + 1))
    fi
}

echo "═══════════════════════════════════════"
echo "  AgentLens API Smoke Tests"
echo "═══════════════════════════════════════"
echo ""

# 1. Health check
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
check "GET /health" 200 "$CODE"

# 2. Stats (empty database)
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/stats")
check "GET /api/stats (empty db)" 200 "$CODE"

# 3. List executions (empty)
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/executions")
check "GET /api/executions (empty)" 200 "$CODE"

# 4. Post a trace
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "smoke-test-001",
    "agent_name": "SmokeTestAgent",
    "status": "completed",
    "started_at": "2026-03-20T10:00:00",
    "completed_at": "2026-03-20T10:00:03",
    "duration_ms": 3000,
    "total_cost": 0.005,
    "total_tokens": 600,
    "llm_calls": [
      {
        "id": "smoke-llm-001",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "prompt_tokens": 200,
        "completion_tokens": 400,
        "total_tokens": 600,
        "cost": 0.005,
        "duration_ms": 1500,
        "timestamp": "2026-03-20T10:00:01"
      }
    ],
    "tool_calls": [
      {
        "id": "smoke-tool-001",
        "tool_name": "web_search",
        "duration_ms": 800,
        "status": "success",
        "timestamp": "2026-03-20T10:00:02"
      }
    ]
  }')
check "POST /api/traces" 201 "$CODE"

# 5. Duplicate trace (should be 409 Conflict)
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "smoke-test-001",
    "agent_name": "SmokeTestAgent",
    "status": "completed",
    "started_at": "2026-03-20T10:00:00",
    "total_cost": 0,
    "total_tokens": 0
  }')
check "POST /api/traces (duplicate → 409)" 409 "$CODE"

# 6. Get the execution we just created
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/executions/smoke-test-001")
check "GET /api/executions/smoke-test-001" 200 "$CODE"

# 7. Get non-existent execution (should be 404)
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/executions/does-not-exist")
check "GET /api/executions/does-not-exist (→ 404)" 404 "$CODE"

# 8. List executions (should have 1 now)
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/executions")
check "GET /api/executions (with data)" 200 "$CODE"

# 9. Filter by agent_name
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/executions?agent_name=SmokeTestAgent")
check "GET /api/executions?agent_name=SmokeTestAgent" 200 "$CODE"

# 10. Stats (should show data now)
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/stats")
check "GET /api/stats (with data)" 200 "$CODE"

echo ""
echo "═══════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════"

exit $FAIL
