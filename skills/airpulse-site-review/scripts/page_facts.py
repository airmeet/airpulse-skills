#!/usr/bin/env python3
"""Extract the facts the AirPulse site review checks need from pages.

Reads built HTML files, a folder of them, or live URLs, and prints one JSON
object per line: one per page, one for the site (with --site) and one with
near-duplicate pairs (when more than one page is read).

Standard library only. Needs Python 3.9 or newer. On Windows run it with `py`.

    python3 page_facts.py https://example.com/ https://example.com/pricing
    python3 page_facts.py --site https://example.com --rendered https://example.com/
    python3 page_facts.py dist/ --base https://example.com --max-pages 50

Network use: plain GET requests to the URLs you pass and to robots.txt,
llms.txt, agents.md and the sitemaps of --site. With --rendered it opens the
URLs in a local headless Chrome or Edge. Nothing else is contacted.
"""

from __future__ import annotations

import argparse
import gzip
import html as htmllib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

USER_AGENT = "AirPulseSiteReview/1.1 (+https://airpulse.ai)"
AI_CRAWLERS = [
    "Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot",
    "Claude-SearchBot", "Claude-User", "anthropic-ai", "PerplexityBot", "Perplexity-User",
    "Google-Extended", "GoogleOther", "Applebot", "Applebot-Extended", "Meta-ExternalAgent",
    "FacebookBot", "Amazonbot", "CCBot", "cohere-ai", "Bytespider",
]
SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}
HEAD_TAGS = {"html", "head", "title", "meta", "link", "script", "style", "base", "noscript", "template"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
             "source", "track", "wbr"}
BOILER_TAGS = {"nav", "header", "footer", "aside"}
MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
DATE_RE = re.compile(rf"\b(20\d\d-\d\d-\d\d|(?:{MONTHS})[a-z]*\.? \d{{1,2}},? 20\d\d|\d{{1,2}} (?:{MONTHS})[a-z]* 20\d\d)\b")
SPA_ROOT_RE = re.compile(r"id=[\"']?(root|app|__next|__nuxt|main-app|app-root|svelte)[\"'\s>]")
HIDDEN_STYLE_RE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)
BYLINE_RE = re.compile(r"\b(author|byline|writer)\b", re.I)
PRONOUNS = {"it", "they", "them", "their", "this", "that", "these", "those", "he", "she", "his", "her"}
LEAD_RE = re.compile(r"^(It|This|That|These|Those|They|He|She|But|However|And|So|Also)\b")
SENT_RE = re.compile(r"(?<=[.!?])\s+")
DEF_RE = re.compile(r"\b(is an?|are|refers to|means|is defined as|is the)\b", re.I)
STAT_RE = re.compile(r"\d[\d,.]*\s*(%|percent|x\b|million|billion|crore|lakh)|[$€£₹]\s?\d|\b(19|20)\d\d\b", re.I)
RESEARCH_RE = re.compile(r"\b(our (research|survey|study|data|analysis|benchmark)|we (surveyed|analy[sz]ed|measured|tested|found))\b", re.I)
FILLER = ["in conclusion", "moreover,", "furthermore,", "it's worth noting", "it is worth noting",
          "in today's fast-paced", "in the digital age", "delve into", "navigate the complexities",
          "leverage the power of", "in the realm of", "unlock the potential", "a testament to",
          "game-changer", "ever-evolving landscape"]


# --------------------------------------------------------------------------- fetching

def fetch_bytes(url: str, timeout: int = 20) -> tuple[int, dict, bytes]:
    for attempt in range(2):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read(20_000_000)
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                hdrs["x-final-url"] = resp.geturl()
                if data[:2] == b"\x1f\x8b":
                    data = gzip.decompress(data)
                return resp.status, hdrs, data
        except urllib.error.HTTPError as e:
            hdrs = {k.lower(): v for k, v in (e.headers or {}).items()}
            if e.code in (429, 503) and attempt == 0:
                wait = hdrs.get("retry-after", "5")
                time.sleep(min(int(wait) if wait.isdigit() else 5, 10))
                continue
            return e.code, hdrs, b""
        except Exception as e:  # network errors are reported, not raised
            return 0, {"error": f"{type(e).__name__}: {e}"}, b""
    return 0, {"error": "retry failed"}, b""


def fetch(url: str, timeout: int = 20) -> tuple[int, dict, str]:
    st, hdrs, data = fetch_bytes(url, timeout)
    m = re.search(r"charset=([\w-]+)", hdrs.get("content-type", ""))
    try:
        text = data.decode(m.group(1) if m else "utf-8", "replace")
    except LookupError:
        text = data.decode("utf-8", "replace")
    return st, hdrs, text.lstrip("\ufeff")


# --------------------------------------------------------------------------- HTML parsing

class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool]] = []  # (tag, hidden)
        self.title_parts: list[str] = []
        self.title_count = 0
        self.metas: list[dict] = []
        self.links: list[dict] = []
        self.headings: list[dict] = []
        self._heading: dict | None = None
        self.jsonld_raw: list[str] = []
        self._jsonld: list[str] | None = None
        self._in_script = False
        self.script_bytes = 0
        self.text_parts: list[str] = []
        self.hidden_parts: list[str] = []
        self.main_parts: list[str] = []
        self.content_parts: list[str] = []  # not boilerplate, not hidden
        self.after_h1_parts: list[str] = []  # content after the first visible H1
        self._seen_h1 = False
        self.noscript_text: list[str] = []
        self.imgs: list[dict] = []
        self.anchors: list[dict] = []
        self._anchor: dict | None = None
        self.html_lang: str | None = None
        self.tables: list[dict] = []
        self._tables: list[dict] = []
        self.ul = 0
        self.ol_items: list[int] = []
        self._lists: list[list] = []
        self.details = 0
        self.times: list[str] = []
        self.sections: list[dict] = [{"heading": "", "text": []}]
        self.paragraphs: list[tuple[str, bool]] = []  # (text, in_main)
        self._p: list[str] | None = None
        self.bylines: list[str] = []
        self._captures: list[dict] = []

    # helpers
    def _tags(self):
        return [t for t, _ in self.stack]

    def _hidden(self) -> bool:
        return any(h for _, h in self.stack)

    def _in(self, names) -> bool:
        return any(t in names for t, _ in self.stack)

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag not in HEAD_TAGS and self._in({"head"}):
            # optional </head> omitted: the body has started
            self.stack = [(t, h) for t, h in self.stack if t != "head"]
        hidden = ("hidden" in a or a.get("aria-hidden", "").lower() == "true"
                  or bool(HIDDEN_STYLE_RE.search(a.get("style", ""))) or tag == "template")
        if tag not in VOID_TAGS:
            self.stack.append((tag, hidden))
            cls = " ".join([a.get("class", ""), a.get("itemprop", ""), a.get("rel", ""), a.get("id", "")])
            if BYLINE_RE.search(cls) and len(self._captures) < 50:
                self._captures.append({"depth": len(self.stack), "text": []})
        if tag == "html":
            self.html_lang = a.get("lang")
        elif tag == "title" and not self._in({"svg"}):
            self.title_count += 1
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading = {"level": int(tag[1]), "text": "", "hidden": self._hidden()}
            if tag in ("h2", "h3"):
                self.sections.append({"heading": None, "text": []})
        elif tag == "script":
            if "ld+json" in a.get("type", "").lower():
                self._jsonld = []
            else:
                self._in_script = True
        elif tag == "img":
            self.imgs.append({"src": a.get("src", "")[:200], "alt": a.get("alt"), "loading": a.get("loading")})
        elif tag == "a":
            self._anchor = {"href": a.get("href", ""), "text": "", "rel": a.get("rel", "")}
        elif tag == "table":
            self._tables.append({"has_th": False, "rows": 0, "caption": ""})
        elif tag == "th" and self._tables:
            self._tables[-1]["has_th"] = True
        elif tag == "tr" and self._tables:
            self._tables[-1]["rows"] += 1
        elif tag == "ul":
            self.ul += 1
            self._lists.append(["ul", 0])
        elif tag == "ol":
            self._lists.append(["ol", 0])
        elif tag == "li" and self._lists:
            self._lists[-1][1] += 1
        elif tag == "details":
            self.details += 1
        elif tag == "time" and a.get("datetime"):
            self.times.append(a["datetime"])
        elif tag == "p":
            self._p = []

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._heading:
            self._heading["text"] = " ".join(self._heading["text"].split())
            self.headings.append(self._heading)
            if self._heading["level"] == 1 and not self._heading["hidden"]:
                self._seen_h1 = True
            if self._heading["level"] in (2, 3) and self.sections[-1]["heading"] is None:
                self.sections[-1]["heading"] = self._heading["text"]
            self._heading = None
        elif tag == "script":
            if self._jsonld is not None:
                self.jsonld_raw.append("".join(self._jsonld))
                self._jsonld = None
            self._in_script = False
        elif tag == "a" and self._anchor is not None:
            self._anchor["text"] = " ".join(self._anchor["text"].split())
            self.anchors.append(self._anchor)
            self._anchor = None
        elif tag == "table" and self._tables:
            self.tables.append(self._tables.pop())
        elif tag in ("ul", "ol") and self._lists:
            kind, n = self._lists.pop()
            if kind == "ol":
                self.ol_items.append(n)
        elif tag == "p" and self._p is not None:
            self.paragraphs.append((" ".join("".join(self._p).split()), self._in({"main", "article"})))
            self._p = None
        tags = self._tags()
        if tag in tags:
            depth = len(tags) - tags[::-1].index(tag)
            while self._captures and self._captures[-1]["depth"] >= depth:
                cap = self._captures.pop()
                txt = " ".join(" ".join(cap["text"]).split())
                if 2 <= len(txt) <= 120:
                    self.bylines.append(txt)
            self.stack = self.stack[:depth - 1]

    def handle_data(self, data):
        if self._jsonld is not None:
            self._jsonld.append(data)
            return
        if self._in_script:
            self.script_bytes += len(data)
            return
        tags = self._tags()
        if tags and tags[-1] == "title" and "svg" not in tags:
            self.title_parts.append(data)
            return
        if "noscript" in tags:
            self.noscript_text.append(data)
            return
        if any(t in SKIP_TEXT_TAGS for t in tags) or "head" in tags:
            return
        if self._hidden():
            self.hidden_parts.append(data)
            return
        self.text_parts.append(data)
        boiler = any(t in BOILER_TAGS for t in tags)
        in_main = "main" in tags or "article" in tags
        if in_main and not boiler:
            self.main_parts.append(data)
        if not boiler:
            self.content_parts.append(data)
            if self._seen_h1 and self._heading is None:
                self.after_h1_parts.append(data)
        if self._heading is not None:
            self._heading["text"] += data
        elif not boiler:
            self.sections[-1]["text"].append((data, in_main))
        if self._p is not None:
            self._p.append(data)
        if self._anchor is not None:
            self._anchor["text"] += data
        if self._tables and "caption" in tags:
            self._tables[-1]["caption"] += data
        for cap in self._captures:
            cap["text"].append(data)


# --------------------------------------------------------------------------- JSON-LD helpers

def jsonld_nodes(node):
    """Every dict in a JSON-LD value, walking lists and @graph (list or object)."""
    if isinstance(node, list):
        for n in node:
            yield from jsonld_nodes(n)
    elif isinstance(node, dict):
        yield node
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                yield from jsonld_nodes(v)


def node_types(n: dict) -> list[str]:
    t = n.get("@type")
    return [t] if isinstance(t, str) else [x for x in t if isinstance(x, str)] if isinstance(t, list) else []


def top_level_types(blocks: list) -> list[str]:
    out = []
    for b in blocks:
        items = b if isinstance(b, list) else [b]
        for it in items:
            if not isinstance(it, dict):
                continue
            g = it.get("@graph")
            members = g if isinstance(g, list) else [g] if isinstance(g, dict) else []
            out += node_types(it)
            for m in members:
                if isinstance(m, dict):
                    out += node_types(m)
    return out


# --------------------------------------------------------------------------- sections and content

def block_score(words: int, text: str, sentences: int) -> int:
    """Rough 0-100 heuristic for how quotable a section is: length, definition, figures,
    first-hand research and sentence count. A guide for editors, not a ranking factor."""
    length = 30 if 134 <= words <= 167 else 20 if 100 <= words <= 220 else 10 if 40 <= words <= 400 else 0
    definition = 25 if DEF_RE.search(" ".join(text.split()[:40])) else 0
    stats = len(STAT_RE.findall(text))
    stat = 20 if stats >= 3 else 10 if stats >= 1 else 0
    research = 15 if RESEARCH_RE.search(text) else 0
    sent = 10 if 3 <= sentences <= 12 else 0
    return length + definition + stat + research + sent


def section_facts(p: PageParser) -> dict:
    sections = []
    has_main = bool(" ".join(p.main_parts).strip())
    for sec in p.sections:
        text = " ".join(" ".join(t for t, m in sec["text"] if m or not has_main).split())
        words = len(text.split())
        if sec["heading"] is None and words == 0:
            continue
        sents = [x for x in SENT_RE.split(text) if x.strip()]
        first = sents[0] if sents else ""
        toks = [t.strip(".,;:!?()\"'").lower() for t in text.split()]
        sections.append({
            "heading": (sec["heading"] or "(intro)")[:100],
            "words": words,
            "sentences": len(sents),
            "first_sentence": first[:200],
            "first_40_words": " ".join(text.split()[:40]),
            "pronoun_led": bool(LEAD_RE.match(first)),
            "pronoun_ratio": round(sum(t in PRONOUNS for t in toks) / words, 3) if words else 0,
            "score": block_score(words, text, len(sents)) if words >= 20 else None,
        })
    scored = sorted((s["score"] for s in sections if s["score"] is not None), reverse=True)[:5]
    headed = [s for s in sections if s["heading"] != "(intro)" and s["words"]]
    paras = [t for t, m in p.paragraphs if m or not has_main]
    long_p = [x[:80] for x in paras if len(x.split()) > 120 or len(SENT_RE.split(x)) > 5]
    return {
        "sections": sections[:40],
        "answer_blocks_134_167": sum(1 for s in sections if 134 <= s["words"] <= 167),
        "max_section_words": max((s["words"] for s in sections), default=0),
        "pronoun_led_section_ratio": round(sum(s["pronoun_led"] for s in headed) / len(headed), 2) if headed else 0,
        "citability_score": round(sum(scored) / len(scored)) if scored else None,
        "first_paragraph": next((x for x in paras if len(x.split()) >= 8), None),
        "long_paragraphs": long_p[:10],
        "paragraph_count": len(paras),
    }


def facts_from_html(html: str, url: str = "", status: int | None = None, headers: dict | None = None,
                    host: str = "", keep_text: bool = False) -> dict:
    p = PageParser()
    p.feed(html)
    p.close()
    headers = headers or {}
    meta: dict = {}
    meta_counts: dict = {}
    for m in p.metas:
        key = (m.get("name") or m.get("property") or m.get("http-equiv") or "").lower()
        if key and "content" in m:
            meta.setdefault(key, m["content"])
            meta_counts[key] = meta_counts.get(key, 0) + 1
    link_rel: dict = {}
    hreflang = []
    for l in p.links:
        rel = l.get("rel", "").lower()
        if rel == "alternate" and l.get("hreflang"):
            hreflang.append({"hreflang": l["hreflang"], "href": l.get("href")})
        elif rel:
            link_rel.setdefault(rel, []).append(l.get("href"))

    jsonld, errors = [], []
    for raw in p.jsonld_raw:
        try:
            jsonld.append(json.loads(raw))
        except json.JSONDecodeError as e:
            errors.append(f"{e.msg} at line {e.lineno} col {e.colno}")
    nodes = list(jsonld_nodes(jsonld))
    all_types = [t for n in nodes for t in node_types(n)]
    type_counts: dict = {}
    for t in top_level_types(jsonld):
        type_counts[t] = type_counts.get(t, 0) + 1
    dates: dict = {}
    authors_ld = []
    faq_answers = []
    for n in nodes:
        for k in ("datePublished", "dateModified"):
            if n.get(k) and k not in dates and isinstance(n[k], str):
                dates[k] = n[k]
        if "author" in n:
            au = n["author"]
            for x in (au if isinstance(au, list) else [au]):
                name = x.get("name") if isinstance(x, dict) else x if isinstance(x, str) else None
                if name:
                    authors_ld.append(name)
        if "Question" in node_types(n):
            ans = n.get("acceptedAnswer")
            ans = ans[0] if isinstance(ans, list) and ans else ans
            if isinstance(ans, dict) and isinstance(ans.get("text"), str):
                faq_answers.append(len(re.sub(r"<[^>]+>", " ", ans["text"]).split()))

    text = " ".join(" ".join(p.text_parts).split())
    content = " ".join(" ".join(p.content_parts).split())
    main = " ".join(" ".join(p.main_parts).split())
    words = len(text.split())
    canonical = (link_rel.get("canonical") or [None])[0]
    host = host or urlparse(url).netloc or urlparse(canonical or "").netloc
    norm = lambda h: h.lower().removeprefix("www.")
    internal, external = [], []
    for a in p.anchors:
        href = a["href"]
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full = urljoin(url, href) if url else href
        net = urlparse(full).netloc
        item = {"href": full[:300], "text": a["text"][:80], "rel": a["rel"]}
        (internal if (not net or (host and norm(net) == norm(host))) else external).append(item)

    title = " ".join("".join(p.title_parts).split()) or None
    visible_headings = [h for h in p.headings if not h["hidden"]]
    h1s = [h["text"] for h in visible_headings if h["level"] == 1]
    skips, prev = [], 0
    for h in visible_headings:
        if prev and h["level"] > prev + 1:
            skips.append(f"h{prev}->h{h['level']}: {h['text'][:60]}")
        prev = h["level"]
    question_headings = [h["text"] for h in visible_headings if h["level"] in (2, 3) and h["text"].rstrip().endswith("?")]
    after_h1 = " ".join(" ".join(p.after_h1_parts).split())
    opening = after_h1 or main or content or text
    low = (main or content).lower()
    filler = {f: low.count(f) for f in FILLER if f in low}
    lead_words = len((main or content).split())
    modified = (meta.get("article:modified_time") or meta.get("og:updated_time")
                or dates.get("dateModified") or headers.get("last-modified"))

    out = {
        "url": url or None,
        "final_url": headers.get("x-final-url"),
        "status": status,
        "content_type": headers.get("content-type"),
        "x_robots_tag": headers.get("x-robots-tag"),
        "last_modified_header": headers.get("last-modified"),
        "lang": p.html_lang,
        "title": title,
        "title_length": len(title) if title else 0,
        "title_count": p.title_count,
        "meta_description": meta.get("description"),
        "meta_description_length": len(meta.get("description") or ""),
        "meta_description_count": meta_counts.get("description", 0),
        "robots_meta": meta.get("robots"),
        "bot_robots_meta": {k: v for k, v in meta.items() if k in ("googlebot", "bingbot", "gptbot", "claudebot", "perplexitybot")},
        "viewport": meta.get("viewport"),
        "viewport_count": meta_counts.get("viewport", 0),
        "canonical": canonical,
        "canonical_count": len(link_rel.get("canonical") or []),
        "hreflang": hreflang,
        "og": {k: v for k, v in meta.items() if k.startswith("og:")},
        "twitter": {k: v for k, v in meta.items() if k.startswith("twitter:")},
        "author_meta": meta.get("author") or meta.get("article:author"),
        "author_visible": list(dict.fromkeys(p.bylines))[:5],
        "author_jsonld": list(dict.fromkeys(authors_ld))[:5],
        "published_meta": meta.get("article:published_time"),
        "modified_meta": meta.get("article:modified_time") or meta.get("og:updated_time"),
        "jsonld_date_published": dates.get("datePublished"),
        "jsonld_date_modified": dates.get("dateModified"),
        "last_modified": modified,
        "time_datetimes": p.times[:10],
        "dates_in_text": sorted(set(DATE_RE.findall(content)))[:10],
        "h1_count": len(h1s),
        "h1": h1s[:3],
        "headings": [f"h{h['level']}: {h['text'][:100]}" for h in visible_headings][:60],
        "heading_skips": skips,
        "question_headings": question_headings[:20],
        "jsonld_count": len(p.jsonld_raw),
        "jsonld_types": sorted(set(all_types)),
        "jsonld_type_counts": type_counts,
        "jsonld_errors": errors,
        "jsonld": jsonld,
        "word_count": words,
        "main_word_count": len(main.split()) or None,
        "content_word_count": len(content.split()),
        "hidden_word_count": len(" ".join(p.hidden_parts).split()),
        "first_60_words": " ".join(opening.split()[:60]),
        "script_bytes": p.script_bytes,
        "looks_client_rendered": words < 80 and (p.script_bytes > 20_000 or bool(SPA_ROOT_RE.search(html))),
        "noscript_words": len(" ".join(p.noscript_text).split()),
        "has_noscript_content": len(" ".join(p.noscript_text).split()) >= 20,
        "images": len(p.imgs),
        "image_list": p.imgs[:60],
        "img_without_alt": [i["src"] for i in p.imgs if i["alt"] is None][:20],
        "img_empty_alt": sum(1 for i in p.imgs if i["alt"] == ""),
        "tables": [{"has_th": t["has_th"], "rows": t["rows"], "caption": " ".join(t["caption"].split())[:80]} for t in p.tables][:20],
        "lists": {"ul": p.ul, "ol": len(p.ol_items), "ol_item_counts": p.ol_items[:20]},
        "details_blocks": p.details,
        "faq": {"details": p.details, "question_headings": len(question_headings),
                "jsonld_questions": all_types.count("Question"), "jsonld_answer_words": faq_answers[:30]},
        "internal_links": len(internal),
        "external_links": len(external),
        "internal_link_list": internal[:300],
        "external_link_list": external[:150],
        "nofollow_internal": sum(1 for a in internal if "nofollow" in a["rel"]),
        "filler_phrases": filler,
        "filler_per_1k": round(sum(filler.values()) / lead_words * 1000, 1) if lead_words >= 400 else None,
        **section_facts(p),
        "_text": main or content,
    }
    if keep_text:
        out["main_text"] = (main or content)[:20000]
    return out


# --------------------------------------------------------------------------- rendered comparison

CHROME_CANDIDATES = [
    os.environ.get("CHROME", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge",
]


def find_chrome() -> str | None:
    for c in CHROME_CANDIDATES:
        if not c:
            continue
        if os.path.isabs(c) and os.path.exists(c):
            return c
        if not os.path.isabs(c) and shutil.which(c):
            return shutil.which(c)
    return None


def rendered_dom(url: str, chrome: str) -> str | None:
    with tempfile.TemporaryDirectory() as profile:
        try:
            out = subprocess.run(
                [chrome, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}",
                 f"--user-agent={USER_AGENT}", "--virtual-time-budget=8000", "--dump-dom", url],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            return out.stdout or None
        except Exception:
            return None


def add_rendered(f: dict, url: str, chrome: str | None) -> None:
    if not chrome:
        f["rendered"] = "not run: no Chrome or Edge found (set CHROME=/path/to/browser)"
        return
    dom = rendered_dom(url, chrome)
    if not dom:
        f["rendered"] = "not run: the browser returned nothing"
        return
    r = facts_from_html(dom, url)
    f["rendered"] = "ok"
    f["rendered_word_count"] = r["word_count"]
    f["rendered_h1_count"] = r["h1_count"]
    f["text_in_initial_html_ratio"] = round(min(f["word_count"] / r["word_count"], 1.0), 2) if r["word_count"] else None
    f["rendered_jsonld_types"] = r["jsonld_types"]
    f["render_only_jsonld_types"] = sorted(set(r["jsonld_types"]) - set(f["jsonld_types"]))
    f["rendered_faq_questions"] = r["faq"]["jsonld_questions"]
    changed = {}
    for k in ("title", "meta_description", "canonical", "robots_meta"):
        if r[k] != f[k]:
            changed[k] = {"server": f[k], "rendered": r[k]}
    og_diff = {k: v for k, v in r["og"].items() if f["og"].get(k) != v}
    if og_diff:
        changed["og"] = og_diff
    f["changed_by_javascript"] = changed


# --------------------------------------------------------------------------- duplicates

def shingles(text: str, n: int = 5) -> set:
    w = re.findall(r"\w+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def duplicate_pairs(pages: list[tuple[str, str]], threshold: float = 0.80) -> list[dict]:
    sh = [(u, shingles(t)) for u, t in pages if len(t.split()) >= 200]
    out = []
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            a, b = sh[i][1], sh[j][1]
            if a and b:
                jac = len(a & b) / len(a | b)
                if jac >= threshold:
                    out.append({"url_a": sh[i][0], "url_b": sh[j][0], "jaccard": round(jac, 3),
                                "level": "fail" if jac >= 0.85 else "warn"})
    return sorted(out, key=lambda x: -x["jaccard"])


# --------------------------------------------------------------------------- robots.txt and site files

def parse_robots(text: str) -> list[tuple[list[str], list[tuple[str, str]]]]:
    groups, agents, rules, last_was_agent = [], [], [], False
    for line in text.lstrip("\ufeff").splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = (s.strip() for s in line.split(":", 1))
        k = k.lower()
        if k == "user-agent":
            if not last_was_agent and agents:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(v.lower())
            last_was_agent = True
        elif k in ("allow", "disallow"):
            if agents:
                rules.append((k, v))
            last_was_agent = False
        else:
            last_was_agent = False
    if agents:
        groups.append((agents, rules))
    return groups


def _rule_re(pattern: str):
    rx = re.escape(pattern).replace(r"\*", ".*")
    if rx.endswith(r"\$"):
        rx = rx[:-2] + "$"
    return re.compile(rx)


def path_allowed(rules: list[tuple[str, str]], path: str) -> bool:
    """RFC 9309: the longest matching rule wins; on a tie, allow wins."""
    best = None
    for kind, pat in rules:
        if not pat:
            continue
        if _rule_re(pat).match(path):
            key = (len(pat), kind == "allow")
            if best is None or key > best[0]:
                best = (key, kind)
    return best is None or best[1] == "allow"


def crawler_access(groups, bot: str) -> dict:
    name = bot.lower()
    own = [g for g in groups if name in g[0]]
    match = own or [g for g in groups if "*" in g[0]]
    rules = [r for g in match for r in g[1]]
    root = path_allowed(rules, "/")
    page = path_allowed(rules, "/airpulse-sample-page")
    disallowed = [v for k, v in rules if k == "disallow" and v]
    status = "BLOCKED" if not (root and page) else "RESTRICTED" if disallowed else "ALLOWED"
    return {"bot": bot, "status": status, "root_allowed": root, "pages_allowed": page,
            "group": "own" if own else "*" if match else "none",
            "disallowed_paths": disallowed[:20]}


def site_facts(base: str, max_sitemaps: int = 50) -> dict:
    base = base.rstrip("/")
    host = urlparse(base).netloc.lower().removeprefix("www.")
    out: dict = {"site": base}
    st, hdr, robots = fetch(base + "/robots.txt")
    is_html = robots.lstrip()[:15].lower().startswith(("<!doctype", "<html"))
    out["robots_txt_status"] = st
    out["robots_txt_content_type"] = hdr.get("content-type")
    out["robots_txt_is_html"] = is_html
    groups = parse_robots(robots) if st == 200 and not is_html else []
    out["crawlers"] = [crawler_access(groups, b) for b in AI_CRAWLERS] if st == 200 and not is_html else []
    out["crawl_delays"] = re.findall(r"(?im)^\s*crawl-delay:\s*(\S+)", robots or "")
    out["sitemaps_in_robots"] = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots or "")
    for name in ("llms.txt", "llms-full.txt"):
        st, hdr, body = fetch(f"{base}/{name}")
        links = re.findall(r"\]\((https?://[^)\s]+)\)", body)
        own = sum(1 for l in links if urlparse(l).netloc.lower().removeprefix("www.") == host)
        out[name] = {"status": st, "final_url": hdr.get("x-final-url"), "content_type": hdr.get("content-type"),
                     "bytes": len(body), "lines": len(body.splitlines()),
                     "starts_with_h1": body.lstrip().startswith("# "),
                     "has_blockquote_summary": bool(re.search(r"(?m)^> \S", body)),
                     "h2_sections": len(re.findall(r"(?m)^## ", body)), "links": len(links),
                     "own_domain_links": own,
                     "looks_like_platform_default": ("Universal Commerce Protocol" in body or "shop.app" in body) and own < 5,
                     "looks_like_html": body.lstrip()[:15].lower().startswith(("<!doctype", "<html"))}
    st, _h, _b = fetch(f"{base}/agents.md")
    out["agents.md"] = {"status": st}

    sm_url = (out["sitemaps_in_robots"] or [base + "/sitemap.xml"])[0]
    st, _h, sm = fetch(sm_url)
    is_index = "<sitemapindex" in (sm or "")
    loc = lambda body: [htmllib.unescape(x) for x in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body or "")]
    url_lastmods = lambda body: re.findall(r"<url>.*?<lastmod>\s*([^<\s]+)\s*</lastmod>.*?</url>", body or "", re.S)
    children, urls, lastmods = [], [], []
    if is_index:
        child_urls = loc(sm)
        for child in child_urls[:max_sitemaps]:
            cst, _h2, cbody = fetch(child)
            clocs = loc(cbody)
            children.append({"url": child, "status": cst, "urls": len(clocs)})
            urls += clocs
            lastmods += url_lastmods(cbody)
        truncated = len(child_urls) > max_sitemaps
    else:
        urls, lastmods, truncated = loc(sm), url_lastmods(sm), False
    out["sitemap"] = {"url": sm_url, "status": st, "is_index": is_index, "children": children,
                      "children_truncated": truncated, "urls": len(urls), "url_with_lastmod": len(lastmods),
                      "distinct_lastmods": len(set(lastmods)), "latest_lastmod": max(lastmods) if lastmods else None,
                      "off_host_urls": sum(1 for u in urls if urlparse(u).netloc.lower().removeprefix("www.") != host),
                      "sample": urls[:50]}
    return out


# --------------------------------------------------------------------------- inputs and main

def iter_inputs(items: list[str], base: str | None, max_pages: int):
    n = 0
    for item in items:
        if item.startswith(("http://", "https://")):
            st, hdr, body = fetch(item)
            yield item, st, hdr, body, True
            n += 1
            continue
        path = Path(item)
        if not path.exists():
            yield item, None, {"error": "file or folder not found"}, None, False
            continue
        files = sorted(path.rglob("*.html")) if path.is_dir() else [path]
        for f in files:
            if n >= max_pages:
                yield str(f), None, {"error": f"skipped: --max-pages {max_pages} reached"}, None, False
                return
            url = ""
            if base:
                rel = f.relative_to(path).as_posix() if path.is_dir() else f.name
                rel = re.sub(r"(^|/)index\.html$", r"\1", rel).removesuffix(".html")
                url = urljoin(base.rstrip("/") + "/", rel)
            yield url or str(f), None, {}, f.read_text("utf-8", "replace"), False
            n += 1


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="*", help="URLs, .html files or folders of built HTML")
    ap.add_argument("--base", help="site origin, e.g. https://example.com (for files read from disk and link classification)")
    ap.add_argument("--site", help="also report robots.txt, llms.txt, agents.md and sitemaps for this origin")
    ap.add_argument("--rendered", action="store_true",
                    help="load each URL in headless Chrome or Edge and compare it with the server HTML")
    ap.add_argument("--max-pages", type=int, default=100, help="stop after this many pages (default 100)")
    ap.add_argument("--text", action="store_true", help="include main_text (up to 20,000 characters) per page")
    ap.add_argument("--no-jsonld-body", action="store_true", help="omit the parsed JSON-LD objects")
    ap.add_argument("--no-sections", action="store_true", help="omit the per-section list")
    ap.add_argument("--no-links", action="store_true", help="omit the internal and external link lists")
    args = ap.parse_args()
    if not args.inputs and not args.site:
        ap.error("give at least one URL, file or folder, or --site")
    if args.site:
        print(json.dumps({"kind": "site", **site_facts(args.site)}, ensure_ascii=False), flush=True)
    chrome = find_chrome() if args.rendered else None
    host = urlparse(args.base or args.site or "").netloc
    texts: list[tuple[str, str]] = []
    for url, st, hdr, body, is_url in iter_inputs(args.inputs, args.base, args.max_pages):
        if body is None or st not in (None, 200):
            print(json.dumps({"kind": "page", "url": url, "status": st, "error": hdr.get("error")}), flush=True)
            continue
        page_url = url if "://" in url else ""
        f = facts_from_html(body, page_url, st, hdr, host=host, keep_text=args.text)
        f["url"] = f["url"] or url
        if args.rendered:
            if is_url:
                add_rendered(f, url, chrome)
            else:
                f["rendered"] = "not run: local file (serve the build and pass URLs to compare)"
        texts.append((f["url"], f.pop("_text")))
        for flag, key in ((args.no_jsonld_body, "jsonld"), (args.no_sections, "sections")):
            if flag:
                f.pop(key)
        if args.no_links:
            f.pop("internal_link_list")
            f.pop("external_link_list")
        print(json.dumps({"kind": "page", **f}, ensure_ascii=False), flush=True)
    if len(texts) > 1:
        print(json.dumps({"kind": "duplicates", "threshold_warn": 0.80, "threshold_fail": 0.85,
                          "pairs": duplicate_pairs(texts)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
