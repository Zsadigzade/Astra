"""Read-only setup checks must fail clearly without disclosing credentials."""

from dataclasses import replace

import httpx
import pytest

from scripts.masumi_check import check
from app.core.config import Settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def settings():
    return Settings(masumi_payment_url="https://node.example/api/v1", masumi_api_key="secret-test-key",
                    masumi_network="Preprod", masumi_agent_id="a" * 60, seller_vkey="b" * 56,
                    payments_mode="simulated")


def response(data):
    return httpx.Response(200, json={"status": "success", "data": data})


def source(**changes):
    return {"id": "src-1", "network": "Preprod", "paymentSourceType": "Web3CardanoV2",
            "smartContractAddress": "addr_test_contract", **changes}


async def run_check(settings, handler, **kwargs):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await check(settings, client, **kwargs)


@pytest.mark.anyio
@pytest.mark.parametrize("changes", [
    {"masumi_payment_url": ""},
    {"masumi_payment_url": "https://node.example/admin"},
    {"masumi_payment_url": "https://secret-test-key@node.example/api/v1"},
    {"masumi_payment_url": "https://node.example/api/v1?key=secret-test-key"},
    {"masumi_payment_url": "https://[broken"},
    {"masumi_api_key": ""},
    {"masumi_network": "Mainnet"},
    {"masumi_agent_id": ""},
    {"seller_vkey": "secret-test-key"},
])
async def test_bad_configuration_never_contacts_node(settings, changes, capsys):
    def handler(request):
        pytest.fail("invalid local configuration must not make HTTP requests")

    assert await run_check(replace(settings, **changes), handler) == 1
    assert "secret-test-key" not in capsys.readouterr().out


@pytest.mark.anyio
async def test_node_only_bootstrap_is_read_only(settings, capsys):
    requests = []

    def handler(request):
        requests.append((request.method, request.url.path))
        assert request.headers["token"] == settings.masumi_api_key
        if request.url.path.endswith("/health"):
            return response({"status": "ok"})
        return response({"PaymentSources": [source()]})

    settings = replace(settings, masumi_payment_url="http://localhost:3001/api/v1/",
                       masumi_agent_id="", seller_vkey="")
    assert await run_check(settings, handler, node_only=True) == 0
    assert requests == [("GET", "/api/v1/health"), ("GET", "/api/v1/payment-source")]
    output = capsys.readouterr().out
    assert "SIMULATED" in output
    assert "Not checked: on-chain registration" in output
    assert "secret-test-key" not in output


@pytest.mark.anyio
@pytest.mark.parametrize("sources", [[], [source(network="Mainnet")],
                                        [source(paymentSourceType="Unknown")],
                                        [source(smartContractAddress="")]])
async def test_missing_usable_preprod_source_fails(settings, sources):
    def handler(request):
        return response({"status": "ok"} if request.url.path.endswith("/health") else {"PaymentSources": sources})

    assert await run_check(settings, handler) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("bad_response", [
    httpx.Response(401, text="secret-test-key"),
    httpx.Response(500, text="secret-test-key"),
    httpx.Response(302, headers={"location": "https://other.example"}),
    httpx.Response(200, text="<html>secret-test-key</html>"),
    httpx.Response(200, json={"status": "error", "error": "secret-test-key"}),
    response({"PaymentSources": None}),
    response({"PaymentSources": [None]}),
])
async def test_api_failures_do_not_leak_response_bodies(settings, bad_response, capsys):
    def handler(request):
        return response({"status": "ok"}) if request.url.path.endswith("/health") else bad_response

    assert await run_check(settings, handler) == 1
    assert "secret-test-key" not in capsys.readouterr().out


@pytest.mark.anyio
async def test_connection_failure_is_actionable(settings, capsys):
    def handler(request):
        raise httpx.ConnectError("secret-test-key", request=request)

    assert await run_check(settings, handler) == 1
    output = capsys.readouterr().out
    assert "cannot reach the node" in output
    assert "secret-test-key" not in output


@pytest.mark.anyio
async def test_unhealthy_node_does_not_pass(settings):
    assert await run_check(settings, lambda request: response({"status": "unhealthy"})) == 1


@pytest.mark.anyio
async def test_source_on_later_page_is_found(settings, capsys):
    def handler(request):
        if request.url.path.endswith("/health"):
            return response({"status": "ok"})
        assert request.url.params["take"] == "100"
        if "cursorId" not in request.url.params:
            return response({"PaymentSources": [source(id=str(i), network="Mainnet") for i in range(100)]})
        assert request.url.params["cursorId"] == "99"
        return response({"PaymentSources": [source()]})

    assert await run_check(settings, handler) == 0
    assert "node and local seller configuration checks" in capsys.readouterr().out


@pytest.mark.anyio
async def test_broken_pagination_fails(settings):
    def handler(request):
        return response({"status": "ok"} if request.url.path.endswith("/health") else
                        {"PaymentSources": [source(id=str(i)) for i in range(100)]})

    assert await run_check(settings, handler) == 1
