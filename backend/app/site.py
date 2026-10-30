"""One-host deploys (Render): the API also serves the landing page at / and the built app at /app/.

Only used when SITE_DIR points at a checkout where `landing/out` and `frontend/dist` were built;
local dev and Docker Compose leave it unset and serve the frontend with Vite or nginx.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles


def mount_site(app: FastAPI, root: str) -> None:
    landing = Path(root, "landing", "out").resolve()
    spa = Path(root, "frontend", "dist").resolve()

    @app.get("/app", include_in_schema=False)
    def app_root() -> RedirectResponse:
        return RedirectResponse("/app/", status_code=308)

    app.mount("/app/assets", StaticFiles(directory=spa / "assets"), name="app-assets")

    @app.get("/app/{path:path}", include_in_schema=False)
    def app_page(path: str) -> FileResponse:
        # Real files (favicon) as-is; every other path is a client-side route
        file = (spa / path).resolve()
        if path and file.is_file() and spa in file.parents:
            return FileResponse(file)
        return FileResponse(spa / "index.html")

    # Last, so it only catches what no API route matched
    app.mount("/", StaticFiles(directory=landing, html=True), name="landing")
