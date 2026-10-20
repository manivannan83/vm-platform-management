"""JSON-backed mock provider with deterministic, generated metrics.

This is a full implementation of VMProvider, not test-only code: the app runs on
it until a real provider (vSphere/OpenStack) is added, and tests rely on it too.
"""

import json
import random
from pathlib import Path

from app.models import (
    SIZE_CATALOG,
    VM,
    Period,
    QuotaLimits,
    SizeName,
    UsageMetrics,
)

DEFAULT_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.json"

# Each VM gets a stable load profile so the sizing hints vary across the inventory.
# Values are (cpu_avg range, mem_avg range) in percent.
_PROFILES: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
    "idle": ((2, 12), (10, 25)),
    "normal": ((25, 55), (35, 65)),
    "busy": ((72, 88), (80, 92)),
}


class MockProvider:
    def __init__(self, seed_path: Path = DEFAULT_SEED_PATH) -> None:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        self._vms: dict[str, VM] = {}
        for raw in data["vms"]:
            vm = _build_vm(raw)
            self._vms[vm.name] = vm
        self._quotas: dict[str, QuotaLimits] = {
            team: QuotaLimits(**limits) for team, limits in data["quotas"].items()
        }

    def list_vms(self, owner_team: str) -> list[VM]:
        return [vm for vm in self._vms.values() if vm.owner_team == owner_team]

    def get_vm(self, name: str) -> VM | None:
        return self._vms.get(name)

    def get_usage(self, name: str, period: Period) -> UsageMetrics:
        # Seeding with a string is stable across processes (unlike hash()),
        # so the same VM + period always yields the same numbers.
        profile = random.Random(name).choice(sorted(_PROFILES))
        (cpu_lo, cpu_hi), (mem_lo, mem_hi) = _PROFILES[profile]
        rng = random.Random(f"{name}:{period.value}")

        cpu_avg = rng.uniform(cpu_lo, cpu_hi)
        mem_avg = rng.uniform(mem_lo, mem_hi)
        return UsageMetrics(
            cpu_avg_pct=round(cpu_avg, 1),
            cpu_peak_pct=round(min(100.0, cpu_avg + rng.uniform(5, 25)), 1),
            mem_avg_pct=round(mem_avg, 1),
            mem_peak_pct=round(min(100.0, mem_avg + rng.uniform(3, 15)), 1),
            disk_used_pct=round(rng.uniform(15, 85), 1),
        )

    def get_quota_limits(self, team: str) -> QuotaLimits | None:
        return self._quotas.get(team)


def _build_vm(raw: dict) -> VM:
    """Fill in vcpu/memory/disk from the size catalog so seed data can't drift from it."""
    size = SIZE_CATALOG[SizeName(raw["size"])]
    return VM(**raw, vcpu=size.vcpu, memory_gb=size.memory_gb, disk_gb=size.disk_gb)
