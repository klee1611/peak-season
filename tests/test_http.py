import httpx
import pytest

from peakseason.http import get_json


async def test_http_errors_never_carry_the_api_key():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(401)))
    with pytest.raises(httpx.HTTPStatusError) as err:
        await get_json(
            client, "https://serpapi.com/account", params={"api_key": "SECRET"}, label="serpapi"
        )
    assert "SECRET" not in str(err.value)
    assert "401" in str(err.value)
