"""Business logic: ownership scoping, usage interpretation, quota consumption.

Routes call this; this calls the provider. Every method takes the caller as a
`User` so ownership is enforced here, in one place, for every entry point
(REST today, MCP tools later).
"""

import difflib

from app.models import (
    SIZE_CATALOG,
    VM,
    Environment,
    Period,
    Quota,
    Size,
    SizingHint,
    UsageMetrics,
    UsageSummary,
    User,
    VMStatus,
)
from app.providers.base import VMProvider


class ServiceError(Exception):
    """Base class for errors whose message is safe and useful to show the caller."""


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


class VMService:
    def __init__(self, provider: VMProvider) -> None:
        self._provider = provider

    def list_vms(
        self, user: User, app: str | None = None, environment: Environment | None = None
    ) -> list[VM]:
        vms = self._provider.list_vms(owner_team=user.team)
        if app is not None:
            vms = [vm for vm in vms if vm.app_name.lower() == app.lower()]
        if environment is not None:
            vms = [vm for vm in vms if vm.environment == environment]
        return sorted(vms, key=lambda vm: vm.name)

    def get_vm(self, user: User, name: str) -> VM:
        vm = self._provider.get_vm(name)
        # Another team's VM is reported exactly like a missing one, so callers
        # can't probe for the existence of VMs they don't own.
        if vm is None or vm.owner_team != user.team:
            raise NotFoundError(self._not_found_message(user, name))
        return vm

    def get_usage(self, user: User, name: str, period: Period) -> UsageSummary:
        vm = self.get_vm(user, name)
        if vm.status == VMStatus.provisioning:
            raise ConflictError(
                f"VM '{name}' is still provisioning, so there is no usage data yet. "
                "Try again once its status is 'running'."
            )
        metrics = self._provider.get_usage(name, period)
        return UsageSummary(
            vm_name=vm.name,
            period=period,
            sizing_hint=_sizing_hint(metrics),
            **metrics.model_dump(),
        )

    def list_sizes(self) -> list[Size]:
        return list(SIZE_CATALOG.values())

    def get_quota(self, user: User) -> Quota:
        limits = self._provider.get_quota_limits(user.team)
        if limits is None:
            raise NotFoundError(
                f"No quota is configured for team '{user.team}'. "
                "Ask a platform admin to set one up."
            )
        # Stopped and provisioning VMs still hold their allocation, so they count.
        vms = self._provider.list_vms(owner_team=user.team)
        return Quota(
            team=user.team,
            used_vcpu=sum(vm.vcpu for vm in vms),
            used_memory_gb=sum(vm.memory_gb for vm in vms),
            used_vms=len(vms),
            **limits.model_dump(),
        )

    def _not_found_message(self, user: User, name: str) -> str:
        # Suggestions come only from the caller's own VMs, never the whole inventory.
        own_names = [vm.name for vm in self._provider.list_vms(owner_team=user.team)]
        matches = difflib.get_close_matches(name, own_names, n=1, cutoff=0.6)
        if matches:
            return f"No VM named '{name}'. Did you mean '{matches[0]}'?"
        return f"No VM named '{name}'. Use GET /vms to list your team's VMs."


def _sizing_hint(m: UsageMetrics) -> SizingHint:
    # Averages show sustained pressure; peaks show whether there is real headroom.
    if m.cpu_avg_pct >= 70 or m.mem_avg_pct >= 80:
        return SizingHint.over_utilized
    if m.cpu_peak_pct < 30 and m.mem_peak_pct < 40:
        return SizingHint.under_utilized
    return SizingHint.ok
