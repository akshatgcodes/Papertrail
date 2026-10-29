from pathlib import Path

import httpx
import pytest

from app.ingest import web

WIKI = (Path(__file__).parent / "fixtures" / "wiki.html").read_text()


def test_extract_keeps_content_and_drops_chrome():
    title, body = web.extract(WIKI, "https://en.wikipedia.org/wiki/Python")
    assert title == "Python (programming language) - Wikipedia"
    assert body.startswith("# Python (programming language)\n\nPython is a high-level")
    assert "## History" in body and "[edit]" not in body
    assert "- Python 3.0 was released on December 3, 2008." in body
    assert "\n\nIt was a major revision." in body  # the innermost block is kept
    for gone in (
        "Main menu",
        "Main page",
        "Contents:",
        "For other uses",
        "Paradigm",
        "[1]",
        "van Rossum",
        "Official website",
        "last edited",
        "navigation box",
    ):
        assert gone not in body, gone


def test_inline_children_keep_their_spacing():
    _, body = web.extract("<p>A language, <a>simple</a> and <code>fast</code>.</p>")
    assert body == "A language, simple and fast."


def test_title_falls_back_to_h1_then_host():
    assert web.extract("<h1>Heading</h1><p>text body</p>")[0] == "Heading"
    assert web.extract("<p>text body</p>", "https://example.com/x")[0] == "example.com"


@pytest.mark.parametrize(
    "url", ["ftp://example.com/x", "http://127.0.0.1/", "http://10.0.0.5/admin", "http://[::1]/"]
)
def test_private_and_odd_urls_are_refused(url):
    with pytest.raises(web.FetchError):
        web.check_public_url(url)


def _transport(routes):
    return httpx.MockTransport(lambda req: routes[str(req.url)])


def test_redirects_are_checked_each_hop(public_dns, monkeypatch):
    routes = {
        "https://example.com/a": httpx.Response(302, headers={"location": "/b"}),
        "https://example.com/b": httpx.Response(
            200, text="<p>ok</p>", headers={"content-type": "text/html"}
        ),
    }
    assert web.fetch("https://example.com/a", _transport(routes)) == "<p>ok</p>"

    routes["https://example.com/a"] = httpx.Response(
        302, headers={"location": "http://169.254.169.254/"}
    )
    real = web.socket.getaddrinfo
    monkeypatch.setattr(
        web.socket,
        "getaddrinfo",
        lambda host, *a, **k: (
            [(0, 0, 0, "", ("169.254.169.254", 0))]
            if host.startswith("169.")
            else real(host, *a, **k)
            if host != "example.com"
            else [(0, 0, 0, "", ("93.184.215.14", 0))]
        ),
    )
    with pytest.raises(web.FetchError, match="not a public address"):
        web.fetch("https://example.com/a", _transport(routes))


def test_fetch_errors(public_dns):
    routes = {
        "https://example.com/404": httpx.Response(404),
        "https://example.com/img": httpx.Response(
            200, content=b"x", headers={"content-type": "image/png"}
        ),
        "https://example.com/loop": httpx.Response(301, headers={"location": "/loop"}),
    }
    with pytest.raises(web.FetchError, match="404"):
        web.fetch("https://example.com/404", _transport(routes))
    with pytest.raises(web.FetchError, match="image/png"):
        web.fetch("https://example.com/img", _transport(routes))
    with pytest.raises(web.FetchError, match="Too many"):
        web.fetch("https://example.com/loop", _transport(routes))
