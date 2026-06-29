from src.vialpilot.services.workflow import _metrics


def test_metrics_includes_speed_summary():
    outputs = [
        {"agent_name": "VisionLabAgent", "latency_ms": 120.0, "mode": "real"},
        {"agent_name": "TaskDecomposerAgent", "latency_ms": 80.0, "mode": "real"},
        {"agent_name": "LabNotebookAgent", "latency_ms": 0.0, "mode": "mock"},
    ]
    m = _metrics(outputs, {"VisionLabAgent": 120.0}, replan_count=1)
    assert m["agent_calls"] == 3
    assert m["real_llm_calls"] == 2
    assert m["replan_count"] == 1
    assert "speed_summary" in m
    assert m["avg_llm_latency_ms"] == 100.0