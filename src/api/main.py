from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.auth import ApiPasswordMiddleware
from api.routes import apps, automation, health


WEBSITE_PATH = Path(__file__).resolve().parents[1] / "website"

app = FastAPI(
    title="Marketing Bot API",
    description="API for inspecting and managing the Marketing Bot.",
    version="0.1.0",
)
app.add_middleware(ApiPasswordMiddleware)
app.mount(
    "/website/static",
    StaticFiles(directory=WEBSITE_PATH),
    name="website-static",
)

app.include_router(health.router)
app.include_router(apps.router, prefix="/apps", tags=["apps"])
app.include_router(
    automation.router,
    prefix="/automation",
    tags=["automation"],
)


@app.get("/website", include_in_schema=False)
@app.get("/website/", include_in_schema=False)
def website() -> FileResponse:
    return FileResponse(WEBSITE_PATH / "index.html")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/website", status_code=307)
