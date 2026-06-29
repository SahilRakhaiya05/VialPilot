def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["llm_mode"] == "mock"


def test_create_run(client):
    res = client.post("/api/runs", json={
        "instruction": "Move red vial to safe tray",
        "scene_id": "safe_sorting_scene",
    })
    assert res.status_code == 200
    data = res.json()
    assert "run_id" in data
    assert data["status"] == "created"


def test_list_and_get_run(client):
    create = client.post("/api/runs", json={"instruction": "Test instruction"})
    run_id = create.json()["run_id"]

    listing = client.get("/api/runs")
    assert listing.status_code == 200
    assert any(r["run_id"] == run_id for r in listing.json())

    detail = client.get(f"/api/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["instruction"] == "Test instruction"


def test_html_run_detail_page(client):
    create = client.post("/api/runs", json={"instruction": "HTML page test"})
    run_id = create.json()["run_id"]
    res = client.get(f"/runs/{run_id}")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "run-shell" in res.text
    assert run_id in res.text


def test_html_history_page(client):
    res = client.get("/runs")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "Run History" in res.text


def test_html_settings_page(client):
    res = client.get("/settings")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "Settings" in res.text


def test_html_landing_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "<title>VialPilot</title>" in res.text
    assert "VIMA" not in res.text
    assert "vision-input" in res.text or "Vision Input" in res.text


def test_html_dashboard_page(client):
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "<title>Dashboard</title>" in res.text
    assert "dash-vision-input" in res.text
    assert "VIMA" not in res.text


def test_removed_legacy_routes_404(client):
    for path in ("/vima", "/mallvi"):
        res = client.get(path)
        assert res.status_code == 404