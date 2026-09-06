"""One palette for every generated figure: graphite, off-white ink, one steel-blue accent, brick only where something is refused."""
import html

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG0, BG1 = "#14171c", "#1c2027"
INK, DIM, EDGE, CARD = "#e7e5e0", "#9a9a93", "#3a3f47", "#20242b"
ACCENT, FAIL = "#7aa6d8", "#d0705a"


def fits(text, size, box_w, pad=14, bold=False, mono=False):
    k = 0.62 if bold else (0.60 if mono else 0.55)
    need = len(text) * size * k
    if need > box_w - 2 * pad:
        raise SystemExit(f"text overflows its card by {need - (box_w - 2*pad):.0f} units: {text!r}")


def text(x, y, s, size, fill, bold=False, mono=False, anchor="start", spacing=None):
    fam = MONO if mono else SANS
    extra = f' letter-spacing="{spacing}"' if spacing else ""
    weight = ' font-weight="700"' if bold else ""
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{fam}" font-size="{size}"{weight}{extra} fill="{fill}">{html.escape(s)}</text>'
