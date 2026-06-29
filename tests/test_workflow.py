def test_mock_agent_workflow(client):
    create = client.post("/api/runs", json={
        "instruction": "Move the red sample vial to the safe tray",
        "scene_id": "safe_sorting_scene",
    })
    run_id = create.json()["run_id"]

    execute = client.post(f"/api/runs/{run_id}/execute?background=false")
    assert execute.status_code == 200
    assert execute.json()["status"] in ("completed", "blocked")

    detail = client.get(f"/api/runs/{run_id}").json()
    agent_names = [o["agent_name"] for o in detail["agent_outputs"]]
    assert "VisionLabAgent" in agent_names
    assert "TaskDecomposerAgent" in agent_names
    assert "LabNotebookAgent" in agent_names

    events = client.get(f"/api/runs/{run_id}/events").json()
    assert any(e["event_type"] == "workflow_started" for e in events)
    assert any(e["event_type"] == "workflow_completed" for e in events)


def test_bench_state_updates_after_robot_commands(client):
    create = client.post("/api/runs", json={
        "instruction": "Move the red sample vial to the safe tray",
        "scene_id": "safe_sorting_scene",
    })
    run_id = create.json()["run_id"]
    client.post(f"/api/runs/{run_id}/execute?background=false")
    detail = client.get(f"/api/runs/{run_id}").json()
    bench = detail.get("bench_state") or {}
    moved = [o for o in bench.get("objects", []) if o.get("state") == "moved"]
    assert moved, "bench_state should reflect robot moves"