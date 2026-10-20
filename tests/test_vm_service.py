"""Unit tests for logic that lives in the service layer, independent of HTTP."""

import pytest

from app.models import Period, SizingHint, UsageMetrics, User
from app.providers.mock import MockProvider
from app.services.vm_service import NotFoundError, VMService, _sizing_hint

ALICE = User(username="alice", team="payments")


def metrics(cpu_avg: float, cpu_peak: float, mem_avg: float, mem_peak: float) -> UsageMetrics:
    return UsageMetrics(
        cpu_avg_pct=cpu_avg,
        cpu_peak_pct=cpu_peak,
        mem_avg_pct=mem_avg,
        mem_peak_pct=mem_peak,
        disk_used_pct=50,
    )


@pytest.mark.parametrize(
    ("m", "expected"),
    [
        (metrics(5, 15, 15, 25), SizingHint.under_utilized),
        (metrics(40, 60, 50, 60), SizingHint.ok),
        (metrics(75, 95, 50, 60), SizingHint.over_utilized),
        (metrics(30, 50, 85, 90), SizingHint.over_utilized),
        # Low average but a high peak means the headroom is real: not under-utilized.
        (metrics(5, 45, 15, 25), SizingHint.ok),
    ],
)
def test_sizing_hint(m, expected):
    assert _sizing_hint(m) is expected


def test_mock_produces_a_mix_of_sizing_hints():
    service = VMService(MockProvider())
    hints = {
        service.get_usage(ALICE, vm.name, Period.last_7d).sizing_hint
        for vm in service.list_vms(ALICE)
    }
    assert len(hints) >= 2


def test_not_found_without_close_match_points_to_listing():
    service = VMService(MockProvider())
    with pytest.raises(NotFoundError, match="Use GET /vms"):
        service.get_vm(ALICE, "zzz-nothing-like-it")
