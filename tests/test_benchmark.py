def test_speed_benchmark_endpoint(client):
    res = client.post("/api/benchmark/speed?iterations=2")
    assert res.status_code == 200
    data = res.json()
    assert "latencies_ms" in data
    assert len(data["latencies_ms"]) == 2
    assert "headline" in data
    assert "avg_ms" in data