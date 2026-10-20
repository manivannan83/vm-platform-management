"""The provider interface: the single swap point between the platform and real infra.

The service layer only talks to this Protocol. Phase 5 adds a vSphere/OpenStack
implementation; nothing above this layer should need to change when it does.
"""

from typing import Protocol

from app.models import VM, Period, QuotaLimits, UsageMetrics


class VMProvider(Protocol):
    def list_vms(self, owner_team: str) -> list[VM]:
        """Return every VM owned by the given team."""
        ...

    def get_vm(self, name: str) -> VM | None:
        """Return the VM with this exact name, regardless of owner, or None."""
        ...

    def get_usage(self, name: str, period: Period) -> UsageMetrics:
        """Return utilisation metrics for an existing VM over the period."""
        ...

    def get_quota_limits(self, team: str) -> QuotaLimits | None:
        """Return the team's quota limits, or None if the team has none configured."""
        ...
