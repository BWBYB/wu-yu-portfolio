import json
import importlib.util
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

    function = config["functions"]["api/**/*.py"]
    assert function["maxDuration"] == 60
    assert function["includeFiles"] == "{backend/**,knowledge/**}"


def test_root_requirements_delegates_to_backend_requirements() -> None:
    requirements = Path("requirements.txt").read_text(encoding="utf-8").splitlines()
    assert requirements == [
        "fastapi>=0.115,<1",
        "httpx>=0.27,<1",
        "openai>=1.66,<2",
        "pydantic-settings>=2.6,<3",
    ]


def test_vercel_catch_all_entrypoint_exports_the_existing_app() -> None:
    entrypoint = Path("api/[...path].py")
    spec = importlib.util.spec_from_file_location("vercel_catch_all", entrypoint)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.app is app
