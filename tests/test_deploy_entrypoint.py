import json
from pathlib import Path

from fastapi.routing import APIRoute

from api.index import app


def test_vercel_entrypoint_exports_existing_fastapi_routes() -> None:
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}

    assert app.title == "Wu Yu Personal Knowledge Agent"
    assert "/health" in paths
    assert "/api/health" in paths
    assert "/api/chat" in paths


def test_vercel_function_includes_backend_and_knowledge_files() -> None:
    config = json.loads(Path("vercel.json").read_text(encoding="utf-8"))

    function = config["functions"]["api/index.py"]
    assert function["maxDuration"] == 60
    assert function["includeFiles"] == ["backend/**", "knowledge/**"]
