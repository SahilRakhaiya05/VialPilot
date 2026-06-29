import io

from PIL import Image


def test_image_upload_path(client, upload_dir):
    create = client.post("/api/runs", json={"instruction": "Upload test"})
    run_id = create.json()["run_id"]

    img = Image.new("RGB", (64, 64), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    res = client.post(
        f"/api/runs/{run_id}/upload",
        files={"image": ("test.png", buf, "image/png")},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["files"]) == 1
    assert (upload_dir / run_id).exists()