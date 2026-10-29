"""A web page into Markdown-ish text: headings as `#` lines, paragraphs and list items as
paragraphs. Navigation, footers, scripts, tables and reference lists are dropped.

The server fetches a URL the user typed, so it must be a public address, and every
redirect is checked again (otherwise a public link could bounce to localhost or a cloud
metadata address).
"""

import ipaddress
import re
import socket
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup, Tag

from app.config import settings


class FetchError(Exception):
    pass


DROP = [
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "iframe",
    "svg",
    "button",
    "table",
    "figure",
    "sup",
]
DROP_CLASS = re.compile(
    r"(?:[\w-]*[_-])?(nav|navbar|navigation|menu|footer|sidebar|cookies?|banner|advert|ads|"
    r"share|social|related|comments?|breadcrumbs?|toc|editsection|reflist|references|"
    r"hatnote|navbox|metadata|infobox|noprint)(?:[_-][\w-]*)?",
    re.I,
)
KEEP = {"html", "body", "main", "article"}
# Sections that are lists of links, not content
SKIP_SECTIONS = re.compile(
    r"^(references|external links|see also|further reading|notes|bibliography|sources|"
    r"citations|footnotes)$",
    re.I,
)
BLOCKS = {"p", "li", "blockquote", "pre", "dd", "dt"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def check_public_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FetchError("Only http(s) links work here")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise FetchError(f"Couldn't resolve {parts.hostname}") from e
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise FetchError(f"{parts.hostname} is not a public address")


def fetch(url: str, transport: httpx.BaseTransport | None = None, max_hops: int = 5) -> str:
    with httpx.Client(
        transport=transport,
        timeout=20,
        headers={"User-Agent": settings.user_agent, "Accept": "text/html,*/*;q=0.5"},
    ) as client:
        for _ in range(max_hops):
            check_public_url(url)
            try:
                res = client.get(url, follow_redirects=False)
            except httpx.TransportError as e:
                raise FetchError(f"Couldn't load the page ({type(e).__name__})") from e
            if res.is_redirect:
                url = urljoin(url, res.headers.get("location", ""))
                continue
            if res.status_code >= 400:
                raise FetchError(f"The page answered {res.status_code}")
            kind = res.headers.get("content-type", "")
            if "html" not in kind and "text" not in kind:
                raise FetchError(
                    f"That link isn't a web page ({kind.split(';')[0] or 'unknown type'})"
                )
            return res.text
    raise FetchError("Too many redirects")


def _text(el: Tag) -> str:
    # No separator: these are innermost blocks, so their children are inline (<a>, <b>,
    # <code>); joining them with spaces would turn "language, simple" into "language , simple"
    text = re.sub(r"\s+", " ", el.get_text()).strip()
    # Permalink markers some docs sites append to headings
    return re.sub(r"\s*[¶#🔗]$", "", text)


def extract(html: str, url: str = "") -> tuple[str, str]:
    """(title, markdown text)"""
    soup = BeautifulSoup(html, "lxml")
    og = soup.find("meta", property="og:title")
    title = (og.get("content", "") if og else "") or (soup.title.string if soup.title else "")
    title = re.sub(r"\s+", " ", title or "").strip()

    for el in soup.find_all(DROP):
        el.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for el in soup.find_all(attrs={"role": ["navigation", "banner", "contentinfo"]}):
        el.decompose()
    for el in soup.find_all(True):
        if el.attrs is None or el.name in KEEP:  # removed with a parent / page containers
            continue
        # Judge each class name on its own: <body class="vector-toc-available"> is a page,
        # not a table of contents
        names = [*el.get("class", []), el.get("id") or ""]
        if any(DROP_CLASS.fullmatch(n) for n in names if n):
            el.decompose()

    root = (
        soup.find("article")
        or soup.find("main")
        or soup.find(attrs={"role": "main"})
        or soup.find(id=re.compile(r"^(content|main|mw-content-text)$"))
        or soup.body
        or soup
    )
    lines: list[str] = []
    skipping_level: int | None = None
    for el in root.find_all(list(BLOCKS | HEADINGS)):
        if el.name in HEADINGS:
            level = int(el.name[1])
            text = _text(el)
            if skipping_level is not None and level > skipping_level:
                continue
            skipping_level = level if SKIP_SECTIONS.match(text) else None
            if skipping_level is None and text:
                lines.append(f"{'#' * level} {text}")
            continue
        if skipping_level is not None:
            continue
        # Nested blocks (a <p> inside an <li>) would repeat text; keep the innermost
        if el.find(list(BLOCKS)):
            continue
        text = _text(el)
        if len(text) >= 2:
            lines.append(f"- {text}" if el.name == "li" else text)
    body = "\n\n".join(lines)
    if not title:
        h1 = root.find("h1") if isinstance(root, Tag) else None
        title = _text(h1) if h1 else urlsplit(url).hostname or "Web page"
    # A page title is often "Article - Site name"; keep both, it helps retrieval
    return title[:500], body[: settings.max_chars]
