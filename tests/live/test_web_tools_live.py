import pytest

from assistant.tools.builtin.weather import GetWeatherArgs, GetWeatherTool
from assistant.tools.builtin.web_search import FetchPageArgs, FetchPageTool, WebSearchArgs, WebSearchTool

pytestmark = pytest.mark.live


def test_live_web_search_returns_numbered_results() -> None:
    out = WebSearchTool().run(WebSearchArgs(query="Python programming language", max_results=3))
    assert out.splitlines()[1].startswith("1. ")


def test_live_fetch_page_reads_example_dot_com() -> None:
    assert "Example Domain" in FetchPageTool().run(FetchPageArgs(url="https://example.com"))


def test_live_home_weather() -> None:
    out = GetWeatherTool("Pimpri-Chinchwad", 18.6298, 73.7997).run(GetWeatherArgs())
    assert out.startswith("Pimpri-Chinchwad now: ") and "Tomorrow:" in out