from unittest.mock import patch


def test_demo_race_endpoint(client):
    fake = {
        "prompt": "test",
        "llm_available": True,
        "wall_clock_ms": 100,
        "winner_id": "cerebras-gemma4",
        "speedup_factor": 18.5,
        "headline": "Gemma 4 finished in 850ms — 18.5× faster",
        "note": "simulated",
        "results": [
            {"id": "cerebras-gemma4", "latency_ms": 850, "live": True, "winner": True},
            {"id": "openai-gpt52", "latency_ms": 18000, "simulated": True},
            {"id": "gemini-20", "latency_ms": 12000, "simulated": True},
        ],
    }
    with patch("src.vialpilot.api.routes.run_llm_race", return_value=fake):
        res = client.post("/api/demo/race")
    assert res.status_code == 200
    data = res.json()
    assert data["winner_id"] == "cerebras-gemma4"
    assert len(data["results"]) == 3


def test_demo_page_loads(client):
    res = client.get("/demo")
    assert res.status_code == 200
    assert b"Start Speed Race" in res.content