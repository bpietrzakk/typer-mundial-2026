# crest proxy: host check, memory + disk cache, upstream errors (no network, httpx.MockTransport)

import httpx
import pytest
from fastapi.testclient import TestClient

import main as main_module
from domain.crests import is_allowed_crest_url
from services.crest_cache import CrestCache, CrestNotAllowed, CrestUpstreamError, get_crest_cache

PL = "https://crests.football-data.org/PL.png"
PNG = b"\x89PNG\r\n\x1a\nfake"


def png_transport(calls: list):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
    return httpx.MockTransport(handler)


@pytest.mark.parametrize("url", [
    PL,
    "https://crests.football-data.org/57.svg",
    "https://crests.football-data.org:443/PL.png",
])
def test_football_data_crests_are_allowed(url):
    assert is_allowed_crest_url(url)


@pytest.mark.parametrize("url", [
    "",
    None,
    "http://crests.football-data.org/PL.png",          # no plain http
    "https://evil.example.com/PL.png",
    "https://crests.football-data.org.evil.com/PL.png",
    "https://user@crests.football-data.org/PL.png",
    "https://crests.football-data.org:8080/PL.png",
    "https://crests.football-data.org/",
    "https://crests.football-data.org",
    "file:///etc/passwd",
    "https://crests.football-data.org/" + "a" * 400 + ".png",
])
def test_other_urls_are_refused(url):
    assert not is_allowed_crest_url(url)


def test_second_get_comes_from_memory(tmp_path):
    calls = []
    cache = CrestCache(tmp_path, transport=png_transport(calls))
    assert cache.get(PL) == (PNG, "image/png")
    assert cache.get(PL) == (PNG, "image/png")
    assert len(calls) == 1


def test_new_process_reads_the_disk_instead_of_upstream(tmp_path):
    first = CrestCache(tmp_path, transport=png_transport([]))
    first.get(PL)

    calls = []
    second = CrestCache(tmp_path, transport=png_transport(calls))
    assert second.get(PL) == (PNG, "image/png")
    assert calls == []


def test_memory_keeps_only_the_newest_items(tmp_path):
    calls = []
    cache = CrestCache(tmp_path / "x", max_items=2, transport=png_transport(calls))
    for code in ("A", "B", "C"):
        cache.get(f"https://crests.football-data.org/{code}.png")
    assert len(cache._memory) == 2
    # A fell out of memory, but the disk still has it
    cache.get("https://crests.football-data.org/A.png")
    assert len(calls) == 3


def test_refused_url_never_hits_upstream(tmp_path):
    calls = []
    cache = CrestCache(tmp_path, transport=png_transport(calls))
    with pytest.raises(CrestNotAllowed):
        cache.get("https://evil.example.com/x.png")
    assert calls == []


@pytest.mark.parametrize("response", [
    httpx.Response(404, content=b"nope", headers={"content-type": "text/plain"}),
    httpx.Response(500),
    httpx.Response(200, content=b"<html>", headers={"content-type": "text/html"}),
    httpx.Response(302, headers={"location": "https://evil.example.com/x.png"}),
])
def test_bad_upstream_answer_is_an_error_and_is_not_cached(tmp_path, response):
    cache = CrestCache(tmp_path, transport=httpx.MockTransport(lambda req: response))
    with pytest.raises(CrestUpstreamError):
        cache.get(PL)
    assert list(tmp_path.iterdir()) == []


def test_timeout_is_an_upstream_error(tmp_path):
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)
    cache = CrestCache(tmp_path, transport=httpx.MockTransport(handler))
    with pytest.raises(CrestUpstreamError):
        cache.get(PL)


# ---------- endpoint ----------

@pytest.fixture
def client_with(tmp_path):
    def make(transport):
        cache = CrestCache(tmp_path, transport=transport)
        main_module.app.dependency_overrides[get_crest_cache] = lambda: cache
        return TestClient(main_module.app)
    yield make
    main_module.app.dependency_overrides.pop(get_crest_cache, None)


def test_endpoint_returns_the_image_with_long_cache(client_with):
    client = client_with(png_transport([]))
    resp = client.get("/img/crest", params={"url": PL})
    assert resp.status_code == 200
    assert resp.content == PNG
    assert resp.headers["content-type"] == "image/png"
    assert resp.headers["cache-control"] == "public, max-age=604800, immutable"


def test_endpoint_answers_head_with_the_same_headers(client_with):
    client = client_with(png_transport([]))
    resp = client.head("/img/crest", params={"url": PL})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == b""


def test_endpoint_refuses_other_hosts_with_400(client_with):
    calls = []
    client = client_with(png_transport(calls))
    resp = client.get("/img/crest", params={"url": "https://evil.example.com/x.png"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Niedozwolony adres obrazka"
    assert calls == []


def test_endpoint_returns_502_when_upstream_fails(client_with):
    client = client_with(httpx.MockTransport(lambda req: httpx.Response(503)))
    resp = client.get("/img/crest", params={"url": PL})
    assert resp.status_code == 502
    assert "cache-control" not in resp.headers or "immutable" not in resp.headers["cache-control"]
