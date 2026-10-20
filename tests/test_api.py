"""API tests against the mock provider and seed data (alice/dave=payments, bob=hr)."""


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# --- auth ---------------------------------------------------------------


def test_missing_user_header_is_401(client):
    resp = client.get("/vms")
    assert resp.status_code == 401
    assert "X-User" in resp.json()["detail"]


def test_unknown_user_is_401(as_user):
    assert as_user("mallory", "/vms").status_code == 401


# --- listing and ownership ----------------------------------------------


def test_list_vms_only_returns_callers_team(as_user):
    vms = as_user("alice", "/vms").json()
    assert len(vms) == 5
    assert {vm["owner_team"] for vm in vms} == {"payments"}


def test_list_vms_filters_by_app_and_environment(as_user):
    vms = as_user("alice", "/vms", app="payments-api", environment="prod").json()
    assert [vm["name"] for vm in vms] == ["payments-api-prod-01", "payments-api-prod-02"]


def test_list_vms_app_filter_is_case_insensitive(as_user):
    assert len(as_user("bob", "/vms", app="PAYROLL").json()) == 3


def test_list_vms_rejects_invalid_environment(as_user):
    assert as_user("alice", "/vms", environment="staging").status_code == 422


def test_get_vm_returns_spec_from_size_catalog(as_user):
    vm = as_user("bob", "/vms/payroll-01").json()
    assert (vm["size"], vm["vcpu"], vm["memory_gb"], vm["disk_gb"]) == ("medium", 4, 16, 100)


def test_other_teams_vm_is_404_not_403(as_user):
    resp = as_user("alice", "/vms/payroll-01")
    assert resp.status_code == 404
    # The message must not hint that the VM exists elsewhere.
    assert "Did you mean" not in resp.json()["detail"]


def test_typo_gets_did_you_mean_suggestion(as_user):
    resp = as_user("bob", "/vms/payrol-01")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No VM named 'payrol-01'. Did you mean 'payroll-01'?"


# --- usage --------------------------------------------------------------


def test_usage_summary_shape(as_user):
    resp = as_user("alice", "/vms/payments-api-prod-01/usage", period="7d")
    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "7d"
    assert body["sizing_hint"] in {"under-utilized", "ok", "over-utilized"}
    assert body["cpu_peak_pct"] >= body["cpu_avg_pct"]
    assert body["mem_peak_pct"] >= body["mem_avg_pct"]


def test_usage_is_deterministic(as_user):
    first = as_user("alice", "/vms/payments-api-prod-01/usage", period="30d").json()
    second = as_user("alice", "/vms/payments-api-prod-01/usage", period="30d").json()
    assert first == second


def test_usage_defaults_to_24h(as_user):
    assert as_user("alice", "/vms/payments-api-dev-01/usage").json()["period"] == "24h"


def test_usage_rejects_invalid_period(as_user):
    assert as_user("alice", "/vms/payments-api-dev-01/usage", period="1y").status_code == 422


def test_usage_for_provisioning_vm_is_409(as_user):
    resp = as_user("bob", "/vms/hr-portal-test-01/usage")
    assert resp.status_code == 409
    assert "provisioning" in resp.json()["detail"]


def test_usage_for_other_teams_vm_is_404(as_user):
    assert as_user("alice", "/vms/payroll-01/usage").status_code == 404


# --- sizes and quota ----------------------------------------------------


def test_sizes_catalog(client):
    sizes = {s["name"]: s for s in client.get("/sizes").json()}
    assert sizes["small"] == {"name": "small", "vcpu": 2, "memory_gb": 4, "disk_gb": 50}
    assert sizes["large"]["vcpu"] == 8


def test_quota_counts_all_team_vms_including_stopped(as_user):
    quota = as_user("alice", "/quota").json()
    # payments: 2x large (8/32) + 1x medium (4/16) + 2x small (2/4), one of them stopped
    assert quota == {
        "team": "payments",
        "max_vcpu": 40,
        "max_memory_gb": 160,
        "max_vms": 10,
        "used_vcpu": 24,
        "used_memory_gb": 88,
        "used_vms": 5,
    }
