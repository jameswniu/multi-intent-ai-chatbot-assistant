"""One palette for every generated figure: graphite, off-white ink, one steel-blue accent, brick only where something is refused."""
import html

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG0, BG1 = "#0f1216", "#171b21"
INK, DIM, EDGE, CARD = "#e6e8eb", "#8b929c", "#2b3138", "#1a1f26"
ACCENT, FAIL = "#7f9bb8", "#b5654a"


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
