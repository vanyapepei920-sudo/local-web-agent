# -*- coding: ascii -*-
"""MCP web-tools v10: search now self-prompts page-reading when snippets lack
the answer. read_page unchanged (multi-URL). No special tokens in strings."""
import re
import requests
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET
from mcp.server.fastmcp import FastMCP

MARGINALIA_KEY = "public"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Accept-Language": "ru,en;q=0.8"}
mcp = FastMCP("web")


def clean(s):
    return re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', s or '')).strip()


def _ddgs(q):
    try:
        from ddgs import DDGS
        with DDGS() as d:
            res = d.text(q, region="ru-ru", max_results=6)
        return [("ddgs", r.get("title", ""), clean(r.get("body", "")), r.get("href", "")) for r in res]
    except Exception:
        return []


def _marginalia(q):
    try:
        r = requests.get("https://api.marginalia.nu/public/search/" + quote_plus(q),
                         params={"key": MARGINALIA_KEY}, headers=UA, timeout=15)
        if r.status_code != 200:
            return []
        out = []
        for it in re.findall(r"<item>(.*?)</item>", r.text, re.S):
            t = re.search(r"<title>(.*?)</title>", it, re.S)
            l = re.search(r"<link>(.*?)</link>", it, re.S)
            d = re.search(r"<description>(.*?)</description>", it, re.S)
            if t and l:
                out.append(("marginalia", clean(t.group(1)), clean(d.group(1)) if d else "", clean(l.group(1))))
        return out[:5]
    except Exception:
        return []


def _gnews(q):
    try:
        r = requests.get("https://news.google.com/rss/search",
                         params={"q": q, "hl": "ru", "gl": "RU", "ceid": "RU:ru"}, headers=UA, timeout=15)
        root = ET.fromstring(r.content)
        out = []
        for item in root.iter("item"):
            t = item.findtext("title") or ""
            l = item.findtext("link") or ""
            s = item.findtext("source") or ""
            out.append(("gnews", clean(t), s, clean(l)))
        return out[:6]
    except Exception:
        return []


def _run(q, order):
    fns = {"ddgs": _ddgs, "marginalia": _marginalia, "gnews": _gnews}
    seen, lines = set(), []
    for name in order:
        fn = fns.get(name)
        if not fn:
            continue
        try:
            res = fn(q)
        except Exception:
            res = []
        for src, t, s, u in res:
            k = (t or "").lower()[:60]
            if not t or k in seen:
                continue
            seen.add(k)
            tag = ""
            if len(s) < 40:
                tag = " [SHORT SNIPPET - open this URL with read_page]"
            lines.append("- [" + src + "] " + t + " | URL: " + u + " | " + s[:150] + tag)
        if len(lines) >= 8:
            break
    if not lines:
        return "Nothing found"
    return "\n".join("[" + str(n) + "] " + line for n, line in enumerate(lines, 1))


def _fetch_one(u, max_chars):
    last_err = None
    for _ in range(2):
        try:
            r = requests.get(u, headers=UA, timeout=25, allow_redirects=True)
            r.raise_for_status()
            if not r.encoding or r.encoding.lower() == "iso-8859-1":
                r.encoding = r.apparent_encoding or "utf-8"
            html = r.text
            title = ""
            mt = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
            if mt:
                title = clean(mt.group(1))
            html = re.sub(r"(?is)<(script|style|noscript|svg|form|iframe|nav|footer|header|aside|button|figure).*?</\1>", " ", html)
            mm = re.search(r"(?is)<(article|main)[^>]*>(.*?)</\1>", html)
            body = mm.group(2) if mm else html
            text = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>|</h[1-6]>|</tr>|</blockquote>|</td>", "\n", body)
            text = re.sub(r"(?is)<[^>]+>", " ", text)
            text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            text = re.sub(r"&#\d+;", "", text)
            text = re.sub(r"[ \t\r\f\v]+", " ", text)
            text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
            head = "TITLE: " + (title or "(none)") + "\nURL: " + r.url + "\n---\n"
            if not text or len(text) < 80:
                return head + "NOTE: page opened but almost no text (JS-rendered site). Try a different source."
            return head + text[:max_chars] + ("\n...[truncated, total " + str(len(text)) + " chars]" if len(text) > max_chars else "")
        except Exception as e:
            last_err = e
    return "TITLE: (unknown)\nURL: " + u + "\nERROR: cannot open page: " + str(last_err)[:200]


@mcp.tool()
def read_page(url: str, max_chars: int = 6000) -> str:
    """Open one or more web pages by URL and return their clean readable text.
    ALWAYS use this tool when the user asks to open, read, view, summarize, check,
    look at, or 'go to' a link / URL / page / article. Also use it after web_search
    when the snippets did not contain a precise or approximate answer: pass the
    most promising URLs from the search list here. Accepts a single URL, or several
    URLs separated by spaces / newlines / commas. Returns per page: TITLE, final
    URL (after redirects), then article text with menus/ads/scripts stripped."""
    parts = re.split(r"[\s,]+", (url or "").strip())
    urls = [p for p in parts if p.startswith(("http://", "https://"))]
    if not urls:
        return "No valid URL given. Provide a link starting with http:// or https://"
    blocks = [_fetch_one(u, max_chars) for u in urls[:5]]
    return "\n\n===== PAGE BREAK =====\n\n".join(blocks)


ANSWER_CHECK = (
    "\n\n=== ANSWER CHECK (read before replying) ===\n"
    "Look at the snippets above. Do they contain a PRECISE or even APPROXIMATE "
    "answer to the user's question? If YES - answer from them. If NO, or if any "
    "line is marked [SHORT SNIPPET], or if the numbers/facts you need are missing "
    "- you MUST call read_page on the 1-3 most promising URLs listed above, then "
    "answer from the page text. Do NOT reply 'I could not find' while unopened "
    "URLs are still on this list."
)


@mcp.tool()
def web_search(query: str) -> str:
    """THE web search tool. Call this for ANY request to find / look up / search /
    'найди' / 'поищи' information about a person, company, place, product, event,
    term, name, or any fact - including encyclopedic 'who is X', 'what is Y'.
    This is the ONLY tool for searching; do NOT diagnose, do NOT check backends
    first, just search. The result ends with an ANSWER CHECK block: follow it -
    if the snippets do not answer the question, open the pages with read_page."""
    out = _run(query, ["ddgs", "marginalia"])
    if out == "Nothing found":
        out = ("Nothing found for: " + query +
               "\nBackends tried: ddgs, marginalia. All empty - they may be rate-limited. "
               "Retry, rephrase, or try news_search for time-sensitive topics.")
    else:
        out = out + ANSWER_CHECK
    return out


@mcp.tool()
def news_search(query: str) -> str:
    """Live news / current-events lookup via Google News RSS (no key). Call for
    anything time-sensitive: latest news, recent developments, today's prices,
    exchange rates, dates, scores, releases, announcements. Result also ends with
    an ANSWER CHECK block - open pages with read_page if snippets lack the answer."""
    out = _run(query, ["gnews", "ddgs"])
    if out == "Nothing found":
        return "Nothing found in news for: " + query
    return out + ANSWER_CHECK


def _health():
    rep = ["ddgs: " + ("alive" if _ddgs("test") else "down"),
           "marginalia: " + ("alive" if _marginalia("test") else "down"),
           "gnews: " + ("alive" if _gnews("test") else "down")]
    return "; ".join(rep)


if __name__ == "__main__":
    mcp.run()
