import httpx
import pytest
from pydantic import ValidationError

from assistant.config import Settings
from assistant.tools.builtin import build_default_registry
from assistant.tools.builtin.weather import GetWeatherArgs, GetWeatherTool
from assistant.tools.builtin.web_search import (
    UNTRUSTED_HEADER, FetchPageArgs, FetchPageTool, WebSearchArgs, WebSearchTool,
)

PUBLIC = lambda host: ["93.184.215.14"]  # noqa: E731


def test_web_search_formats_results_and_marks_them_untrusted() -> None:
    def fake(query: str, count: int):
        assert (query, count) == ("jarvis", 2)
        return [{"title": "A", "body": "alpha", "href": "https://a.test"},
                {"title": "B", "body": "beta", "href": "https://b.test"}]

    out = WebSearchTool(search=fake).run(WebSearchArgs(query="jarvis", max_results=2))
    assert out.splitlines() == [UNTRUSTED_HEADER, "1. A - alpha (https://a.test)", "2. B - beta (https://b.test)"]


def test_web_search_empty_and_failure() -> None:
    assert WebSearchTool(search=lambda q, n: []).run(WebSearchArgs(query="zzz")) == "No web results found for 'zzz'."

    def failing(q: str, n: int):
        raise RuntimeError("rate limited")

    assert WebSearchTool(search=failing).run(WebSearchArgs(query="x")) == "ERROR: web search failed: rate limited"


def test_web_search_result_count_is_bounded() -> None:
    with pytest.raises(ValidationError):
        WebSearchTool().parse_args({"query": "x", "max_results": 50})


def html_transport(body: str, status: int = 200, content_type: str = "text/html; charset=utf-8",
                   headers: dict | None = None) -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda request: httpx.Response(status, text=body, headers={"content-type": content_type} | (headers or {}))
    )


def test_fetch_page_returns_readable_text_only() -> None:
    html = ("<html><head><style>x{}</style><script>evil()</script></head>"
            "<body><nav>menu</nav><h1>Title</h1><p>Hello   world.</p></body></html>")
    out = FetchPageTool(transport=html_transport(html), resolver=PUBLIC).run(FetchPageArgs(url="https://example.test/page"))
    assert out.splitlines() == [UNTRUSTED_HEADER, "Source: https://example.test/page", "Title Hello world."]


@pytest.mark.parametrize("url", ["file:///C:/secrets.txt", "ftp://example.test/x", "notaurl"])
def test_fetch_page_rejects_non_http_urls(url: str) -> None:
    tool = FetchPageTool(transport=html_transport("x"), resolver=PUBLIC)
    assert tool.run(FetchPageArgs(url=url)) == "ERROR: only http and https URLs are allowed"


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.5", "192.168.1.5", "169.254.169.254", "::1"])
def test_fetch_page_blocks_private_and_local_addresses(address: str) -> None:
    tool = FetchPageTool(transport=html_transport("<p>x</p>"), resolver=lambda host: [address])
    assert tool.run(FetchPageArgs(url="http://sneaky.test/")) == "ERROR: refusing to fetch a private or local address"


def test_fetch_page_http_error_redirect_and_binary() -> None:
    url = FetchPageArgs(url="https://example.test/")
    assert FetchPageTool(transport=html_transport("gone", status=404), resolver=PUBLIC).run(url) == \
        "ERROR: https://example.test/ returned HTTP 404"
    redirect = html_transport("", status=302, headers={"location": "http://127.0.0.1/"})
    assert FetchPageTool(transport=redirect, resolver=PUBLIC).run(url) == \
        "ERROR: page redirects to http://127.0.0.1/; fetch that URL instead"
    pdf = html_transport("%PDF", content_type="application/pdf")
    assert FetchPageTool(transport=pdf, resolver=PUBLIC).run(url) == "ERROR: unsupported content type application/pdf"


FORECAST = {
    "current": {"temperature_2m": 27.4, "apparent_temperature": 29.6, "relative_humidity_2m": 70,
                "weather_code": 2, "wind_speed_10m": 12.2},
    "daily": {"temperature_2m_max": [30.2, 31.0], "temperature_2m_min": [23.8, 24.1],
              "precipitation_probability_max": [40, None], "weather_code": [61, 3]},
}


def weather_transport(seen: list) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        if request.url.host == "geocoding-api.open-meteo.com":
            name = request.url.params["name"]
            if name == "Atlantis":
                return httpx.Response(200, json={})
            return httpx.Response(200, json={"results": [{"name": "Mumbai", "admin1": "Maharashtra", "country": "India",
                                                          "latitude": 19.07, "longitude": 72.88}]})
        return httpx.Response(200, json=FORECAST)

    return httpx.MockTransport(handler)


def test_home_weather_uses_configured_coordinates() -> None:
    seen: list = []
    out = GetWeatherTool("Pimpri-Chinchwad", 18.6298, 73.7997, transport=weather_transport(seen)).run(GetWeatherArgs())
    assert out == ("Pimpri-Chinchwad now: 27°C (feels like 30°C), partly cloudy, humidity 70%, wind 12 km/h. "
                   "Today: 24-30°C, light rain, rain chance 40%. Tomorrow: 24-31°C, overcast, rain chance unknown.")
    assert len(seen) == 1 and seen[0].params["latitude"] == "18.6298"


def test_named_location_is_geocoded_first() -> None:
    seen: list = []
    out = GetWeatherTool("Home", 1.0, 2.0, transport=weather_transport(seen)).run(GetWeatherArgs(location="Mumbai"))
    assert out.startswith("Mumbai, Maharashtra, India now: 27°C")
    assert [u.host for u in seen] == ["geocoding-api.open-meteo.com", "api.open-meteo.com"]
    assert seen[1].params["latitude"] == "19.07"


def test_unknown_place_and_service_failure() -> None:
    tool = GetWeatherTool("Home", 1.0, 2.0, transport=weather_transport([]))
    assert tool.run(GetWeatherArgs(location="Atlantis")) == "ERROR: could not find a place called 'Atlantis'"

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    offline = GetWeatherTool("Home", 1.0, 2.0, transport=httpx.MockTransport(down))
    assert offline.run(GetWeatherArgs()).startswith("ERROR: weather service unavailable")


def test_default_registry_includes_web_tools() -> None:
    names = set(build_default_registry(Settings(_env_file=None)).names())
    assert {"web_search", "fetch_page", "get_weather"} <= names