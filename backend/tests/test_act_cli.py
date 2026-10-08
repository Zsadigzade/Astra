"""Terminal demo runner follows the current deal through replay without stale approvals."""

import json

import httpx
import pytest

from scripts import act


def event(deal_id, kind):
    return {"deal_id": deal_id, "type": kind, "data": {}, "simulated": True, "staged": False}


def deal(deal_id="new", status="released", **fields):
    return {"deal_id": deal_id, "status": status, "approved": 0, "escrow_ref": None, **fields}


class Buyer:
    def __init__(self, deals, events, approval_status=200):
        self.deals, self.events = deals, events
        self.approval_status = approval_status
        self.calls = []

    def __call__(self, request):
        self.calls.append(request)
        if request.url.path == "/deals":
            return httpx.Response(200, json=self.deals)
        if request.url.path == "/tasks":
            return httpx.Response(200, json={"deal_id": "new"})
        if request.url.path.startswith("/approvals/"):
            self.deals[0]["status"] = "released"
            return httpx.Response(self.approval_status, json={"ok": True})
        assert request.url.path == "/events"
        body = "".join(f"data: {json.dumps(item)}\n\n" for item in self.events)
        return httpx.Response(200, text=body)

    def client(self):
        return httpx.Client(base_url="http://buyer", transport=httpx.MockTransport(self),
                            timeout=act.REQUEST_TIMEOUT)


def test_watch_pins_newest_deal_before_replaying_old_terminal_events(capsys):
    buyer = Buyer([deal(), deal("old")], [
        event("old", "task_created"), event("old", "released"),
        event("new", "task_created"), event("new", "error"),
        event("new", "already_paid"), event("new", "released"),
    ])
    with buyer.client() as client:
        assert act.run(client, "honest", watch=True) == 0
    output = capsys.readouterr().out
    assert output.count("TASK_CREATED") == 1
    assert output.count("RELEASED") == 1
    assert "ALREADY_PAID" in output and "[SIMULATED]" in output
    assert all(request.method == "GET" for request in buyer.calls)


@pytest.mark.parametrize("current", [deal(), deal(status="agreed", approved=1),
                                     deal(status="locked", escrow_ref="SIM-new")])
def test_stale_approval_does_not_prompt_or_post(monkeypatch, current):
    buyer = Buyer([current], [event("new", "needs_approval")])
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("stale approval prompted"))
    with buyer.client() as client:
        assert act.run(client, "honest", watch=True) == 1  # Finite test stream, no new terminal event.
    assert all(request.method == "GET" for request in buyer.calls)


@pytest.mark.parametrize("approval_status", [200, 404])
def test_pending_approval_prompts_once_and_tolerates_resolution_race(monkeypatch, approval_status, capsys):
    buyer = Buyer([deal(status="agreed")], [event("new", "needs_approval"),
                                           event("new", "needs_approval"), event("new", "released")],
                  approval_status=approval_status)
    prompts = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "y")
    with buyer.client() as client:
        assert act.run(client, "honest", watch=True) == 0
    assert len(prompts) == 1
    approval = [request for request in buyer.calls if request.method == "POST"]
    assert len(approval) == 1 and json.loads(approval[0].content) == {"approve": True}
    if approval_status == 404:
        assert "already resolved or expired" in capsys.readouterr().out


def test_empty_watch_waits_for_first_task_and_does_not_switch(capsys):
    buyer = Buyer([], [event(None, "controls_updated"), event("new", "task_created"),
                       event("other", "task_created"), event("other", "error"), event("new", "released")])
    with buyer.client() as client:
        assert act.run(client, "honest", watch=True) == 0
    output = capsys.readouterr().out
    assert output.count("TASK_CREATED") == 1 and "ERROR" not in output


def test_start_mode_keeps_created_deal_and_bounds_nonstream_requests():
    buyer = Buyer([deal()], [event("old", "released"), event("new", "released")])
    with buyer.client() as client:
        assert act.run(client, "junk", watch=False) == 0
    task = buyer.calls[0]
    assert json.loads(task.content) == {"demo_mode": "junk"}
    for request in buyer.calls:
        timeout = request.extensions["timeout"]
        assert timeout["connect"] == act.REQUEST_TIMEOUT
        assert timeout["read"] == (None if request.url.path == "/events" else act.REQUEST_TIMEOUT)


@pytest.mark.parametrize("status", [423, 500])
def test_main_http_failure_is_concise(monkeypatch, capsys, status):
    request = httpx.Request("POST", "http://buyer/tasks")

    def fail(*args, **kwargs):
        httpx.Response(status, text="private server response", request=request).raise_for_status()

    monkeypatch.setattr(act, "run", fail)
    monkeypatch.setattr("sys.argv", ["act.py", "honest"])
    assert act.main() == 1
    output = capsys.readouterr().out
    assert "private server response" not in output and "Traceback" not in output
    assert ("paused" if status == 423 else "HTTP 500") in output
