"""Read-only HTTP composition. No ambient auth, inventory or provider executor."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from home_device_fabric.home_queries import HomeQueryError, HomeQueryService, QueryResult
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from state_schema.home_inventory import CANONICAL_ID_PATTERN

from .auth import AuthenticationError, RoleError, TokenVerifier
from .models import Area, Device, DeviceDetail, Error, Found, Home, Missing, Snapshot


class ApiError(Exception):
    def __init__(self, status: int, code: str):
        self.status, self.code = status, code
        super().__init__(code)


def _error(status: int, code: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code}},
        status_code=status,
        headers={"WWW-Authenticate": "Bearer"} if status == 401 else None,
    )


def _data(result: QueryResult) -> object:
    return result.to_dict()["data"]


def _found(data: object) -> dict[str, object]:
    return {"status": "found", "data": data}


def _response(result: QueryResult) -> dict[str, object] | JSONResponse:
    if result.status == "not_found":
        return JSONResponse(result.to_dict(), status_code=404)
    return result.to_dict()


def _parameters(*names: str) -> dict[str, object]:
    return {
        "parameters": [
            {
                "name": name,
                "in": "query",
                "required": name == "home_id",
                "schema": {"type": "string", "pattern": "^[a-z][a-z0-9_-]{0,63}$"},
            }
            for name in names
        ]
    }


@dataclass(frozen=True)
class Scope:
    context: dict[str, str]
    home_id: str


def create_app(
    *,
    service: HomeQueryService,
    verifier: TokenVerifier,
    clock_ms: Callable[[], int] | None = None,
    max_age_ms: int = 30000,
) -> FastAPI:
    """Supply trusted service/grants and pinned OIDC verifier. Nothing dispatches.

    Default clock uses Unix milliseconds. Store writes must use that same time
    domain; callers cannot choose now/max_age. This factory installs no live HA
    ingestion; absent observations stay uninitialized.
    """
    if (
        type(service) is not HomeQueryService
        or type(verifier) is not TokenVerifier
        or type(max_age_ms) is not int
        or not 0 <= max_age_ms <= 86400000
        or (clock_ms is not None and not callable(clock_ms))
    ):
        raise ValueError("invalid_api_configuration")
    clock = clock_ms if clock_ms is not None else lambda: time.time_ns() // 1000000
    app = FastAPI(
        title="Canonical Home Query API",
        version="1.0.0",
        debug=False,
        redirect_slashes=False,
        description="Authenticated canonical reads; stale data remains explicit. No device writes.",
    )
    bearer = HTTPBearer(auto_error=False)

    @app.middleware("http")
    async def protect_responses(request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
        except Exception:
            response = _error(500, "internal_error")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(ApiError)
    async def api_error(request: Request, error: ApiError) -> JSONResponse:
        return _error(error.status, error.code)

    @app.exception_handler(HomeQueryError)
    async def query_error(request: Request, error: HomeQueryError) -> JSONResponse:
        if error.code in ("forbidden", "invalid_context"):
            return _error(403, "forbidden")
        if error.code == "clock_regression":
            return _error(503, "state_unavailable")
        if error.code == "invalid_selector":
            return _error(400, "invalid_request")
        return _error(503, "state_unavailable")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        return _error(400, "invalid_request")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        return _error(
            error.status_code,
            "method_not_allowed"
            if error.status_code == 405
            else "not_found"
            if error.status_code == 404
            else "invalid_request",
        )

    async def scope(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> Scope:
        headers = request.headers.getlist("authorization")
        if len(headers) != 1 or credentials is None or credentials.scheme.lower() != "bearer":
            raise ApiError(401, "unauthenticated")
        try:
            identity = await run_in_threadpool(verifier.verify, credentials.credentials)
        except AuthenticationError:
            raise ApiError(401, "unauthenticated") from None
        except RoleError:
            raise ApiError(403, "forbidden") from None
        homes = request.query_params.getlist("home_id")
        if len(homes) != 1:
            raise ApiError(400, "invalid_request")
        home_id = homes[0]
        # Authorize before diagnostics for device IDs, filters, time or extra fields.
        context = identity.context(home_id)
        await run_in_threadpool(service.home, context, home_id=home_id)
        allowed = {"home_id"}
        if request.url.path == "/api/devices":
            allowed.add("area_id")
        params = request.query_params
        if any(key not in allowed or len(params.getlist(key)) != 1 for key in params) or any(
            CANONICAL_ID_PATTERN.fullmatch(value) is None for value in params.values()
        ):
            raise ApiError(400, "invalid_request")
        async for chunk in request.stream():
            if chunk:
                raise ApiError(400, "invalid_request")
        return Scope(context, home_id)

    def now() -> int:
        failed = False
        value = 0
        try:
            value = clock()
            if type(value) is not int or value < 0:
                failed = True
        except Exception:
            failed = True
        if failed:
            raise ApiError(503, "state_unavailable")
        return value

    # Scope is a local dependency, so avoid postponed-annotation references to
    # a local alias (FastAPI resolves annotations against module globals).
    responses: dict[int | str, dict[str, object]] = {
        "default": {"model": Error},
        400: {"model": Error},
        401: {"model": Error},
        403: {"model": Error},
        404: {"model": Missing},
        500: {"model": Error},
        503: {"model": Error},
    }

    @app.get(
        "/api/home",
        response_model=Found[Home],
        responses=responses,
        openapi_extra=_parameters("home_id"),
    )
    def home(caller: Annotated[Scope, Depends(scope)]) -> object:
        return _response(service.home(caller.context, home_id=caller.home_id))

    @app.get(
        "/api/areas",
        response_model=Found[list[Area]],
        responses=responses,
        openapi_extra=_parameters("home_id"),
    )
    def areas(caller: Annotated[Scope, Depends(scope)]) -> object:
        return _response(service.areas(caller.context, home_id=caller.home_id))

    @app.get(
        "/api/devices",
        response_model=Found[list[Device]],
        responses=responses,
        openapi_extra=_parameters("home_id", "area_id"),
    )
    def devices(request: Request, caller: Annotated[Scope, Depends(scope)]) -> object:
        return _response(
            service.devices(
                caller.context,
                home_id=caller.home_id,
                area_id=request.query_params.get("area_id"),
            )
        )

    @app.get(
        "/api/twin/snapshot",
        response_model=Found[Snapshot],
        responses=responses,
        openapi_extra=_parameters("home_id"),
    )
    def snapshot(caller: Annotated[Scope, Depends(scope)]) -> object:
        context, home_id = caller.context, caller.home_id
        return _found(
            {
                "home": _data(service.home(context, home_id=home_id)),
                "areas": _data(service.areas(context, home_id=home_id)),
                "devices": _data(service.devices(context, home_id=home_id)),
                "states": _data(
                    service.states(
                        context,
                        home_id=home_id,
                        now_ms=now(),
                        max_age_ms=max_age_ms,
                    )
                ),
            }
        )

    @app.get(
        "/api/devices/{device_id}",
        response_model=Found[DeviceDetail],
        responses=responses,
        openapi_extra=_parameters("home_id"),
    )
    def device(device_id: str, caller: Annotated[Scope, Depends(scope)]) -> object:
        context, home_id = caller.context, caller.home_id
        result = service.device(context, home_id=home_id, device_id=device_id)
        if result.status == "not_found":
            return _response(result)
        return _found(
            {
                "device": _data(result),
                "state": _data(
                    service.state(
                        context,
                        home_id=home_id,
                        device_id=device_id,
                        now_ms=now(),
                        max_age_ms=max_age_ms,
                    )
                ),
                "capabilities": service.capabilities(
                    context,
                    home_id=home_id,
                    device_id=device_id,
                ).to_dict(),
            }
        )

    return app
