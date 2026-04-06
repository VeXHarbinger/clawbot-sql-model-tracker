# clawbot-sql-model-tracker

Track, analyze, and visualize AI model usage across Oblio agents.

Backed by the `memory.ModelUsageLog` SQL table on the local SQL Server instance (`10.0.0.110`).

---

## The `memory.ModelUsageLog` Table

Every time an Oblio agent calls a model (Ollama, OpenAI, Copilot, etc.), a row is written here automatically via `OblioAgent._log_model_usage()`.

### Schema

| Column              | Type           | Description                                     |
|---------------------|----------------|-------------------------------------------------|
| `id`                | INT (PK)       | Auto-increment row ID                           |
| `agent_name`        | NVARCHAR(100)  | Agent that made the call (e.g. `facs_agent`)    |
| `task_id`           | INT (nullable) | TaskQueue row ID, if the call was task-driven   |
| `task_type`         | NVARCHAR(100)  | Task type string (e.g. `facs_train`)            |
| `model_name`        | NVARCHAR(200)  | Model identifier (e.g. `gemma3:4b`, `gpt-4o`)  |
| `model_type`        | NVARCHAR(50)   | Backend type (`ollama`, `openai`, `copilot`, …) |
| `prompt_tokens`     | INT (nullable) | Input token count (when available)              |
| `completion_tokens` | INT (nullable) | Output token count (when available)             |
| `latency_ms`        | INT (nullable) | Milliseconds from request to response           |
| `success`           | BIT            | 1 = success, 0 = failure                        |
| `logged_at`         | DATETIME       | UTC timestamp of the call                       |

---

## How to Query It

### Via SQL (SSMS / sqlcmd)

```sql
-- Top models by usage in the last 7 days
SELECT model_name, COUNT(*) AS calls, SUM(CAST(success AS INT)) AS successes
FROM memory.ModelUsageLog
WHERE logged_at >= DATEADD(day, -7, GETUTCDATE())
GROUP BY model_name
ORDER BY calls DESC;

-- Agent activity breakdown
SELECT agent_name, model_name, COUNT(*) AS calls
FROM memory.ModelUsageLog
WHERE logged_at >= DATEADD(day, -30, GETUTCDATE())
GROUP BY agent_name, model_name
ORDER BY agent_name, calls DESC;

-- Average latency per model
SELECT model_name, AVG(latency_ms) AS avg_latency_ms, COUNT(*) AS calls
FROM memory.ModelUsageLog
WHERE latency_ms IS NOT NULL
GROUP BY model_name
ORDER BY avg_latency_ms;

-- Failure rate per model
SELECT model_name,
       SUM(CAST(success AS INT)) AS successes,
       SUM(1 - CAST(success AS INT)) AS failures,
       COUNT(*) AS total,
       ROUND(100.0 * SUM(CAST(success AS INT)) / COUNT(*), 1) AS success_pct
FROM memory.ModelUsageLog
GROUP BY model_name
ORDER BY total DESC;
```

### Via Python (`model_tracker.py`)

`model_tracker.py` lives in `oblio-heart-and-soul/infrastructure/` and exposes two functions:

```python
from model_tracker import query_model_usage, paid_vs_free_ratio

# Usage breakdown for last 7 days
usage = query_model_usage(days=7)
print(usage)
# {
#   "period_days": 7,
#   "total_calls": 312,
#   "by_model": { "gemma3:4b": {"calls": 220, "success": 218, "fail": 2}, ... },
#   "by_agent": { "facs_agent": {"calls": 45}, ... },
#   "by_type":  { "ollama": {"calls": 290}, "copilot": {"calls": 22} }
# }

# Paid vs free model ratio (last 30 days)
ratio = paid_vs_free_ratio(days=30)
print(ratio)
# { "paid": 44, "free": 268, "ratio": 0.1642 }
```

### Paid vs Free Classification

Models are classified as **paid** if their name starts with:
`gpt-`, `claude-`, `gemini-`, `o1`, `o3`, `github-copilot/`, `openai/`, `anthropic/`

Everything else (Ollama models, local models) is **free**.

---

## How Tracking Works

1. Any agent inheriting from `OblioAgent` gets `_log_model_usage()` for free.
2. It is called automatically by `ollama_generate()`, `ollama_chat()`, and `ollama_embed()`.
3. For external API calls (Copilot, OpenAI), agents call `_log_model_usage()` manually.
4. Non-fatal — tracking failures are silently swallowed so they never block execution.

### Adding tracking to a new model call

```python
t0 = time.monotonic()
result = call_some_model(prompt)
latency = int((time.monotonic() - t0) * 1000)

self._log_model_usage(
    model_name="my-model",
    model_type="custom",
    task_id=task.get("id"),
    task_type="my_task_type",
    latency_ms=latency,
    success=True,
)
```

---

## Dashboard / Reporting

The `oblio-heart-and-soul` repo ships an agent reporter that can pull this data
into weekly Markdown/JSON reports via `AgentReport`. To include model usage in a
report, call `query_model_usage()` and pass results to `report_metric()` or
`report_enrichment()`.

---

## Related

- `oblio-heart-and-soul/infrastructure/model_tracker.py` — Python analytics functions
- `oblio-heart-and-soul/infrastructure/agent_base.py` — Base class with `_log_model_usage()`
- `oblio-heart-and-soul/infrastructure/sql_memory_connector.py` — DB connector
- `memory.TaskQueue` — Task rows stamped with `worker_model` from this table

---

*Part of the Oblio Agent Framework — VeXHarbinger / clawbot*
