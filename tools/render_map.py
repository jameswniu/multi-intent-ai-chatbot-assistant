#!/usr/bin/env python3
"""Emit assets/system-map.svg from a declared step list, with a text-fit guard.

    python3 tools/render_map.py --write    regenerate the committed file
    python3 tools/render_map.py --check    exit 1 if the committed file differs
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import ACCENT, BG0, BG1, CARD, DIM, EDGE, FAIL, INK, fits, text  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "system-map.svg")
W, H = 1200, 1000
STEPS = [
    ("Guard", "seven phrases refused on the way in", "guardrails/prompt_injection_guard.py", FAIL),
    ("Classify", "two vocabularies, whole words, no model", "app/intent_classifier.py", ACCENT),
    ("Route", "a strict winner routes, a tie asks again", "app/router.py", ACCENT),
    ("Retrieve", "FAISS over the guide, top two paragraphs", "app/chains.py", ACCENT),
    ("Select", "SQL chosen from a four-column map", "app/contract_agent.py", ACCENT),
    ("Validate", "one SELECT, one table, four columns", "guardrails/sql_validator.py", FAIL),
]
TIERS = [
    ("ROUTE", ["the column map's own words", "plus billing, one stemmer", "a tie asks the user again"]),
    ("CONSTRAIN", ["user words never reach SQL", "allowlist, then denylist", "the only lock in Phase 2"]),
    ("REDACT", ["four patterns, output side", "SSN, email, phone, card", "dashed phones slip through"]),
]
PHASES = [
    ("Pilot", "runs and is measured here", True),
    ("Production", "a model behind the locks", False),
    ("Scaling", "Helm and Argo manifests", False),
]


def render():
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="System map: one question through six steps, guard, classify, route, retrieve, select, validate, and the three locks that own them.">',
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{BG0}"/><stop offset="100%" stop-color="{BG1}"/></linearGradient></defs>',
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
        f'<rect x="0" y="0" width="7" height="{H}" fill="{ACCENT}"/>',
    ]
    o.append(text(60, 58, "SYSTEM MAP", 22, ACCENT, bold=True, mono=True, spacing=3))
    o.append(text(60, 104, "One question, three locks", 40, INK, bold=True))
    sub = "A question reaches the table only when every lock in front of it says yes."
    fits(sub, 23, W - 120, pad=0)
    o.append(text(60, 140, sub, 23, DIM))
    o.append(f'<rect x="{W - 480}" y="36" width="420" height="52" rx="8" fill="none" stroke="{EDGE}"/>')
    stat = "6 steps  3 locks  4 patterns"
    fits(stat, 22, 420, mono=True)
    o.append(text(W - 270, 69, stat, 22, INK, mono=True, anchor="middle"))

    o.append(text(60, 196, "01  THE PATH", 22, ACCENT, bold=True, mono=True, spacing=2))
    o.append(text(230, 196, "top to bottom, the order a question meets them", 22, DIM))
    cw, ch, gap, x0 = 533, 100, 14, 60
    for i, (title, detail, foot, color) in enumerate(STEPS):
        row, col = divmod(i, 2)
        x = x0 + col * (cw + gap)
        y = 216 + row * (ch + gap)
        for s, sz, b, m in ((title, 24, True, False), (detail, 22, False, False), (foot, 22, False, True)):
            fits(s, sz, cw, bold=b, mono=m)
        o.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="10" fill="{CARD}" fill-opacity=".92" stroke="{EDGE}"/>')
        o.append(f'<rect x="{x}" y="{y}" width="5" height="{ch}" rx="2.5" fill="{color}"/>')
        o.append(text(x + 18, y + 34, title, 24, INK, bold=True))
        o.append(text(x + 18, y + 62, detail, 22, DIM))
        o.append(text(x + 18, y + 88, foot, 22, color, mono=True))

    o.append(text(60, 592, "02  WHO OWNS THE LOCK", 22, ACCENT, bold=True, mono=True, spacing=2))
    o.append(text(370, 592, "each lock answers to its own source of truth", 22, DIM))
    tw, th, ty = 352, 150, 612
    for i, (name, lines) in enumerate(TIERS):
        x = 60 + i * (tw + 14)
        o.append(f'<rect x="{x}" y="{ty}" width="{tw}" height="{th}" rx="10" fill="{CARD}" fill-opacity=".92" stroke="{EDGE}"/>')
        o.append(f'<rect x="{x}" y="{ty}" width="5" height="{th}" rx="2.5" fill="{ACCENT}"/>')
        fits(name, 24, tw, bold=True, mono=True)
        o.append(text(x + 18, ty + 36, name, 24, ACCENT, bold=True, mono=True, spacing=2))
        for j, ln in enumerate(lines):
            fits(ln, 22, tw)
            o.append(text(x + 18, ty + 70 + j * 32, ln, 22, INK))

    o.append(text(60, 822, "03  THE STAGED PATH", 22, ACCENT, bold=True, mono=True, spacing=2))
    o.append(text(340, 822, "what runs here, and what is only designed", 22, DIM))
    pw, ph, py = 352, 92, 842
    for i, (name, detail, live) in enumerate(PHASES):
        x = 60 + i * (pw + 14)
        fill, stroke, c1, c2 = (ACCENT, ACCENT, BG0, BG0) if live else (CARD, EDGE, INK, DIM)
        o.append(f'<rect x="{x}" y="{py}" width="{pw}" height="{ph}" rx="10" fill="{fill}" fill-opacity="{1 if live else .92}" stroke="{stroke}"/>')
        fits(name, 24, pw, bold=True)
        fits(detail, 22, pw)
        o.append(text(x + 18, py + 36, name, 24, c1, bold=True))
        o.append(text(x + 18, py + 68, detail, 22, c2))

    o.append(text(W / 2, H - 14, "python3 tools/render_map.py --check   regenerates and compares this figure in CI", 22, DIM, mono=True, anchor="middle"))
    o.append("</svg>")
    return "\n".join(o) + "\n"


if __name__ == "__main__":
    svg = render()
    if "--write" in sys.argv:
        open(OUT, "w").write(svg)
        print("wrote", os.path.relpath(OUT, ROOT))
    elif "--check" in sys.argv:
        cur = open(OUT).read() if os.path.exists(OUT) else ""
        if cur != svg:
            print("assets/system-map.svg differs from its generator; run --write")
            sys.exit(1)
        print("assets/system-map.svg matches its generator")
    else:
        sys.stdout.write(svg)
