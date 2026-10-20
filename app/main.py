"""FastAPI app factory and router registration."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import vms
from app.auth import UserDirectory
from app.providers.base import VMProvider
from app.providers.mock import MockProvider
from app.services.vm_service import ConflictError, NotFoundError, VMService


def create_app(provider: VMProvider | None = None, users: UserDirectory | None = None) -> FastAPI:
    """Build the app. Tests (and later, config) can inject a different provider."""
    app = FastAPI(title="VM Platform Management", version="0.1.0")
    app.state.service = VMService(provider or MockProvider())
    app.state.users = users or UserDirectory()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Service errors become HTTP responses here, so the service stays HTTP-agnostic
    # and can be reused unchanged by the MCP server.
    @app.exception_handler(NotFoundError)
    def not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    def conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    app.include_router(vms.router)
    return app


app = create_app()
