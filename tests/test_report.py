def test_report_generation(client):
    create = client.post("/api/runs", json={
        "instruction": "Sort vials",
        "scene_id": "safe_sorting_scene",
    })
    run_id = create.json()["run_id"]
    client.post(f"/api/runs/{run_id}/execute?background=false")

    json_report = client.get(f"/api/runs/{run_id}/report?format=json")
    assert json_report.status_code == 200
    data = json_report.json()
    assert data["run_id"] == run_id
    assert "latency_metrics" in data

    md_report = client.get(f"/api/runs/{run_id}/report?format=markdown")
    assert md_report.status_code == 200
    assert "VialPilot Run Report" in md_report.text