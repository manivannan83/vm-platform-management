"""Pydantic models shared by the API, service, and provider layers."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Environment(StrEnum):
    dev = "dev"
    test = "test"
    prod = "prod"


class VMStatus(StrEnum):
    running = "running"
    stopped = "stopped"
    provisioning = "provisioning"


class SizeName(StrEnum):
    small = "small"
    medium = "medium"
    large = "large"


class Period(StrEnum):
    last_24h = "24h"
    last_7d = "7d"
    last_30d = "30d"


class SizingHint(StrEnum):
    under_utilized = "under-utilized"
    ok = "ok"
    over_utilized = "over-utilized"


class Size(BaseModel):
    name: SizeName
    vcpu: int
    memory_gb: int
    disk_gb: int


# The size catalog is a platform-wide fact, so it lives with the domain models
# rather than inside any one provider.
SIZE_CATALOG: dict[SizeName, Size] = {
    SizeName.small: Size(name=SizeName.small, vcpu=2, memory_gb=4, disk_gb=50),
    SizeName.medium: Size(name=SizeName.medium, vcpu=4, memory_gb=16, disk_gb=100),
    SizeName.large: Size(name=SizeName.large, vcpu=8, memory_gb=32, disk_gb=200),
}


class User(BaseModel):
    username: str
    team: str


class VM(BaseModel):
    name: str
    app_name: str
    environment: Environment
    status: VMStatus
    size: SizeName
    vcpu: int
    memory_gb: int
    disk_gb: int
    os: str
    ip: str | None
    cluster: str
    owner_team: str
    created_at: datetime


class UsageMetrics(BaseModel):
    """Raw utilisation numbers as reported by a provider (percentages, 0-100)."""

    cpu_avg_pct: float = Field(ge=0, le=100)
    cpu_peak_pct: float = Field(ge=0, le=100)
    mem_avg_pct: float = Field(ge=0, le=100)
    mem_peak_pct: float = Field(ge=0, le=100)
    disk_used_pct: float = Field(ge=0, le=100)


class UsageSummary(UsageMetrics):
    """Metrics plus the interpretation the service layer adds on top."""

    vm_name: str
    period: Period
    sizing_hint: SizingHint


class QuotaLimits(BaseModel):
    max_vcpu: int
    max_memory_gb: int
    max_vms: int


class Quota(QuotaLimits):
    team: str
    used_vcpu: int
    used_memory_gb: int
    used_vms: int
