"""Read-only endpoints. Each route is a thin adapter: parse input, call the service."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth import CurrentUser
from app.models import VM, Environment, Period, Quota, Size, UsageSummary
from app.services.vm_service import VMService

router = APIRouter()


def get_service(request: Request) -> VMService:
    return request.app.state.service


Service = Annotated[VMService, Depends(get_service)]


@router.get("/vms")
def list_vms(
    user: CurrentUser,
    service: Service,
    app: str | None = None,
    environment: Environment | None = None,
) -> list[VM]:
    return service.list_vms(user, app=app, environment=environment)


@router.get("/vms/{name}")
def get_vm(name: str, user: CurrentUser, service: Service) -> VM:
    return service.get_vm(user, name)


@router.get("/vms/{name}/usage")
def get_vm_usage(
    name: str, user: CurrentUser, service: Service, period: Period = Period.last_24h
) -> UsageSummary:
    return service.get_usage(user, name, period)


@router.get("/sizes")
def list_sizes(service: Service) -> list[Size]:
    return service.list_sizes()


@router.get("/quota")
def get_quota(user: CurrentUser, service: Service) -> Quota:
    return service.get_quota(user)
