#!/usr/bin/env python3
"""Emit assets/hero.svg: the question the page answers, and the three locks with their sources of truth.

    python3 tools/render_hero.py --write    regenerate the committed file
    python3 tools/render_hero.py --check    exit 1 if the committed file differs
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import ACCENT, BG0, BG1, CARD, DIM, EDGE, INK, fits, text  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "hero.svg")
W, H = 1200, 460
CARDS = [
    ("ROUTE", ["Which agent answers,", "or ask the user?"], "the column map", "changes with the schema"),
    ("CONSTRAIN", ["What SQL may run", "against the table?"], "a four-column map", "Phase 2 swaps in a model"),
    ("REDACT", ["What may leave", "in the answer?"], "four regex patterns", "read on the way out"),
]
TITLE = "Docs, or the database?"
SUB = "Three locks on one question, each with its own source of truth."
FOOT = "guard then classify then route then select then validate then redact"


def render():
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{TITLE} {SUB}">',
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{BG0}"/><stop offset="100%" stop-color="{BG1}"/></linearGradient>',
        f'<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="{INK}" stroke-opacity=".045" stroke-width="1"/></pattern></defs>',
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
        f'<rect width="{W}" height="{H}" fill="url(#grid)"/>',
        f'<rect x="0" y="0" width="{W}" height="3" fill="{ACCENT}"/>',
    ]
    fits(TITLE, 50, W, pad=40, bold=True)
    fits(SUB, 27, W, pad=40)
    o.append(text(W / 2, 76, TITLE, 50, INK, bold=True, anchor="middle"))
    o.append(text(W / 2, 118, SUB, 27, DIM, anchor="middle"))
    cw, ch, y = 360, 242, 150
    for i, (name, q, truth, when) in enumerate(CARDS):
        x = 40 + i * (cw + 20)
        cx = x + cw / 2
        o.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="12" fill="{CARD}" fill-opacity=".92" stroke="{EDGE}"/>')
        o.append(f'<rect x="{x}" y="{y}" width="7" height="{ch}" rx="3.5" fill="{ACCENT}" fill-opacity=".6"/>')
        fits(name, 24, cw, bold=True, mono=True)
        o.append(text(cx, y + 42, name, 24, ACCENT, bold=True, mono=True, anchor="middle", spacing=2))
        for j, ln in enumerate(q):
            fits(ln, 25, cw, bold=True)
            o.append(text(cx, y + 84 + j * 30, ln, 25, INK, bold=True, anchor="middle"))
        o.append(text(cx, y + 156, "SOURCE OF TRUTH", 22, DIM, mono=True, anchor="middle", spacing=1.5))
        fits(truth, 26, cw, bold=True)
        o.append(text(cx, y + 188, truth, 26, INK, bold=True, anchor="middle"))
        fits(when, 22, cw, mono=True)
        o.append(text(cx, y + 222, when, 22, DIM, mono=True, anchor="middle"))
    fits(FOOT, 22, W, mono=True)
    o.append(text(W / 2, 432, FOOT, 22, DIM, mono=True, anchor="middle"))
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
            print("assets/hero.svg differs from its generator; run --write")
            sys.exit(1)
        print("assets/hero.svg matches its generator")
    else:
        sys.stdout.write(svg)
