def test_pipeline_logs_export(client):
    create = client.post("/api/runs", json={
        "instruction": "Move vials",
        "scene_id": "safe_sorting_scene",
    })
    run_id = create.json()["run_id"]
    client.post(f"/api/runs/{run_id}/execute?background=false")

    resp = client.get(f"/api/runs/{run_id}/pipeline-logs")
    assert resp.status_code == 200
    text = resp.text
    assert "Graph execution started" in text
    assert "Node started:" in text or "Node completed:" in text
    assert "Graph execution completed" in text