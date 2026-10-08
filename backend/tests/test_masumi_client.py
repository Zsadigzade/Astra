"""Provider diagnostics must stay useful without exposing response bodies."""

import httpx
import pytest

from app.core.masumi import MasumiClient, MasumiError


@pytest.mark.anyio
async def test_provider_error_does_not_echo_credentials():
    token = "private-node-token-for-regression"

    def handler(request):
        return httpx.Response(401, text=f"Invalid token: {request.headers['token']}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = MasumiClient("http://node", token, http=http)
        with pytest.raises(MasumiError) as error:
            await client.health()

    assert str(error.value) == "GET /health -> HTTP 401"
    assert token not in str(error.value)
