#!/usr/bin/env python3
"""
model_tracker.py — OB-111: Model Usage Analytics
=================================================
Queries memory.ModelUsageLog to provide usage breakdowns and
paid-vs-free ratios. Uses SQLMemoryConnector('local').

Usage:
    from model_tracker import query_model_usage, paid_vs_free_ratio
    print(query_model_usage(days=7))
    print(paid_vs_free_ratio(days=30))
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from sql_memory_connector import SQLMemoryConnector

# Models considered "paid" (cloud-hosted, API-key-based)
PAID_MODEL_PREFIXES = (
    "gpt-", "claude-", "gemini-", "o1", "o3",
    "github-copilot/", "openai/", "anthropic/",
)


def _is_paid(model_name: str) -> bool:
    """Return True if model_name is a paid/cloud model."""
    lower = (model_name or "").lower()
    return any(lower.startswith(p) for p in PAID_MODEL_PREFIXES)


def query_model_usage(days: int = 7) -> dict:
    """
    Return a breakdown of model usage over the past N days.

    Returns:
        {
            "period_days": int,
            "total_calls": int,
            "by_model": { model_name: {"calls": N, "success": N, "fail": N} },
            "by_agent": { agent_name: {"calls": N} },
            "by_type":  { model_type: {"calls": N} },
        }
    """
    mem = SQLMemoryConnector('local')
    rows = mem.query(
        """
        SELECT agent_name, model_name, model_type, success, COUNT(*) AS calls
        FROM memory.ModelUsageLog
        WHERE logged_at >= DATEADD(day, -%s, GETUTCDATE())
        GROUP BY agent_name, model_name, model_type, success
        """,
        (days,)
    )

    result = {
        "period_days": days,
        "total_calls": 0,
        "by_model": {},
        "by_agent": {},
        "by_type": {},
    }

    for row in (rows or []):
        agent      = row.get("agent_name") or "unknown"
        model      = row.get("model_name") or "unknown"
        mtype      = row.get("model_type") or "unknown"
        success    = bool(row.get("success", 1))
        calls      = int(row.get("calls", 0))

        result["total_calls"] += calls

        bm = result["by_model"].setdefault(model, {"calls": 0, "success": 0, "fail": 0})
        bm["calls"] += calls
        if success:
            bm["success"] += calls
        else:
            bm["fail"] += calls

        ba = result["by_agent"].setdefault(agent, {"calls": 0})
        ba["calls"] += calls

        bt = result["by_type"].setdefault(mtype, {"calls": 0})
        bt["calls"] += calls

    return result


def paid_vs_free_ratio(days: int = 30) -> dict:
    """
    Return the ratio of paid (cloud) vs free (local/open-source) model calls
    over the past N days.

    Returns:
        { "paid": N, "free": N, "ratio": X.XX }
        ratio = paid / free  (inf if free == 0, 0.0 if paid == 0)
    """
    mem = SQLMemoryConnector('local')
    rows = mem.query(
        """
        SELECT model_name, COUNT(*) AS calls
        FROM memory.ModelUsageLog
        WHERE logged_at >= DATEADD(day, -%s, GETUTCDATE())
        GROUP BY model_name
        """,
        (days,)
    )

    paid = 0
    free = 0
    for row in (rows or []):
        model = row.get("model_name") or ""
        calls = int(row.get("calls", 0))
        if _is_paid(model):
            paid += calls
        else:
            free += calls

    if free == 0:
        ratio = float("inf") if paid > 0 else 0.0
    else:
        ratio = round(paid / free, 4)

    return {"paid": paid, "free": free, "ratio": ratio}


if __name__ == "__main__":
    import json
    print("=== Model Usage (7 days) ===")
    print(json.dumps(query_model_usage(7), indent=2))
    print("\n=== Paid vs Free (30 days) ===")
    print(json.dumps(paid_vs_free_ratio(30), indent=2))
