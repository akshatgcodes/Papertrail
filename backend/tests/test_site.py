from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.site import mount_site


def test_site_serves_landing_app_and_api(tmp_path):
    (tmp_path / "landing" / "out").mkdir(parents=True)
    (tmp_path / "landing" / "out" / "index.html").write_text("landing")
    (tmp_path / "frontend" / "dist" / "assets").mkdir(parents=True)
    (tmp_path / "frontend" / "dist" / "index.html").write_text("spa")
    (tmp_path / "frontend" / "dist" / "favicon.svg").write_text("<svg/>")
    (tmp_path / "frontend" / "dist" / "assets" / "app.js").write_text("js")
    (tmp_path / "secret.txt").write_text("nope")

    app = FastAPI()

    @app.get("/api/ping")
    def ping() -> dict:
        return {"ok": True}

    mount_site(app, str(tmp_path))
    c = TestClient(app)

    assert c.get("/").text == "landing"
    assert c.get("/api/ping").json() == {"ok": True}
    assert c.get("/app", follow_redirects=False).headers["location"] == "/app/"
    assert c.get("/app/").text == "spa"
    assert c.get("/app/some/client/route").text == "spa"
    assert c.get("/app/favicon.svg").text == "<svg/>"
    assert c.get("/app/assets/app.js").text == "js"
    # No escaping the build folder
    assert c.get("/app/..%2F..%2Fsecret.txt").text == "spa"
    assert c.get("/missing").status_code == 404
