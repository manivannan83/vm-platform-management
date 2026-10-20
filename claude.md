# VM Platform — Agentic AI learning project

## Purpose
A private-cloud VM self-service platform that will be exposed to AI agents via MCP.
Users ask about the VMs hosting their applications, check usage, and request new VMs.
This is a learning + portfolio project: the owner is moving from private cloud automation
into agentic AI engineering. Favor clarity and good architecture over cleverness.

## Architecture (build in this order)
1. FastAPI service (app/) over a swappable provider interface  <-- CURRENT PHASE
2. MCP server (mcp_server/) wrapping the service with task-shaped tools
3. Write operations with plan/confirm, quota checks, audit log
4. Custom agent client (agent/) + evals in GitLab CI
5. Real provider (vSphere/OpenStack) replacing the mock via config

## Project layout
app/
  main.py              # FastAPI app factory, router registration
  models.py            # Pydantic models (VM, Usage, Size, Quota, VMRequestPlan, AuditEntry)
  auth.py              # Mock auth: X-User header -> user + team
  audit.py             # Append-only audit log
  api/
    vms.py             # read endpoints
    requests.py        # plan/confirm VM creation
  services/
    vm_service.py      # business logic, ownership scoping, quota/policy checks
  providers/
    base.py            # VMProvider Protocol (the swap point)
    mock.py            # in-memory/JSON-backed mock with generated metrics
  data/
    seed.json          # mock inventory, teams, users, quotas
tests/
mcp_server/            # later phase
agent/                 # later phase

## Domain model
- VM: name, app_name, environment (dev|test|prod), status (running|stopped|provisioning),
  size (small|medium|large), vcpu, memory_gb, disk_gb, os, ip, cluster, owner_team, created_at
- Size catalog: small=2vCPU/4GB/50GB, medium=4/16/100, large=8/32/200
- Usage summary (not raw series): cpu_avg/peak %, mem_avg/peak %, disk_used %, period,
  plus a sizing hint: under-utilized | ok | over-utilized
- Quota per team: max_vcpu, max_memory_gb, max_vms; plus current consumption
- VMRequestPlan: plan_id, requested spec, estimated quota after, expires_at, status

## API (v1)
GET  /health
GET  /vms?app=&environment=          # only VMs owned by caller's team
GET  /vms/{name}
GET  /vms/{name}/usage?period=24h|7d|30d
GET  /sizes
GET  /quota
POST /vm-requests                    # creates a PLAN only, no VM yet
POST /vm-requests/{plan_id}/confirm  # executes plan; idempotent
GET  /audit                          # caller's team only

## Non-negotiable rules
- Identity comes ONLY from auth context (X-User header), never from request body/params.
- Users see and act only on VMs owned by their team. Return 404 (not 403) for others' VMs.
- Quota and policy checks live in the service layer, never in routes or (later) the LLM.
- Creating a VM is always two steps: plan -> confirm. Confirm is idempotent; plans expire (15 min).
- Every write and every confirm is recorded in the audit log (who, what, when, result).
- Errors are actionable: e.g. "No VM named 'payrol-01'. Did you mean 'payroll-01'?"
- Routes stay thin; logic goes in services; data access goes through VMProvider.

## Conventions
- Python 3.13, managed with uv. Use `uv add` / `uv run`. Never pip install.
- Type hints everywhere; Pydantic v2 models for all request/response bodies.
- Mock metrics must be deterministic (seeded by VM name) so tests are stable.
- Small, focused modules. No premature abstractions beyond the provider interface.

## Commands
- Run:    uv run uvicorn app.main:app --reload
- Test:   uv run pytest -q
- Lint:   uv run ruff check . && uv run ruff format --check .
- Format: uv run ruff format .

## Working agreement with Claude
- The owner is learning: explain design decisions briefly when making them.
- Work one step at a time; propose a plan before large changes.
- Write or update tests with every feature; run tests + lint before declaring done.
- Do not start later phases (MCP, agent) until asked.