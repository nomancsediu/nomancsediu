"""Build the SVG cards in assets/.

Default run (used by the GitHub Action):
    Fetches 30-day traffic from the Cloudflare GraphQL Analytics API and writes
    assets/traffic.svg (a small live-numbers strip for Admission Informer).
    Env: CF_API_TOKEN (Zone > Analytics > Read), CF_ZONE_ID

Static run (no API, no secrets):
    python3 scripts/update_traffic.py --static
    Rewrites assets/card-admission.svg, assets/card-ailab.svg, assets/card-boardsnap.svg
"""
import datetime as dt
import html
import json
import os
import sys
import urllib.request

GQL = "https://api.cloudflare.com/client/v4/graphql"
QUERY = """
query ($zone: string!, $from: Date!, $to: Date!) {
  viewer {
    zones(filter: { zoneTag: $zone }) {
      httpRequests1dGroups(limit: 40, filter: { date_geq: $from, date_leq: $to }) {
        dimensions { date }
        sum { requests pageViews }
        uniq { uniques }
      }
    }
  }
}
"""

SANS = "'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif"
MONO = "'JetBrains Mono','Fira Code',Consolas,'DejaVu Sans Mono',monospace"
BG, BORDER = "#110e2b", "#ffffff"
W = 760

GREEN, AMBER, PURPLE, CYAN = "#4ade80", "#fbbf24", "#a78bfa", "#22d3ee"

STATIC_CARDS = {
    "assets/card-admission.svg": dict(
        title="Admission Informer",
        badge="Live",
        desc="Bangla university admission portal. Gemma Vision reads circulars from images.",
        stack="Django REST Framework · Next.js · Gemma Vision · AWS · Cloudflare",
        meta="admissioninformer.com",
        accent=GREEN,
    ),
    "assets/card-ailab.svg": dict(
        title="AI Assisted Programming Lab Evaluation Platform",
        badge="Pilot at DIU",
        desc="AI-assisted evaluation of programming lab submissions.",
        stack="Django REST Framework · PostgreSQL · Redis · Celery · AWS · Cloudflare",
        meta="Final Year Design Project · Daffodil International University",
        accent=AMBER,
    ),
    "assets/card-boardsnap.svg": dict(
        title="BoardSnap",
        badge="2nd Place",
        desc="Turns a whiteboard photo into notes, code, flashcards and a quiz.",
        stack="FastAPI · React · Gemma Vision",
        meta="Team Leader · Build With Gemma @ Bangladesh",
        accent=PURPLE,
    ),
}


def esc(t):
    return html.escape(t, quote=False).replace("·", "&#183;")


def fmt(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}".rstrip("0").rstrip(".") + "K"
    return str(n)


def fetch(token, zone):
    to = dt.date.today()
    frm = to - dt.timedelta(days=29)
    body = json.dumps(
        {"query": QUERY, "variables": {"zone": zone, "from": str(frm), "to": str(to)}}
    ).encode()
    req = urllib.request.Request(
        GQL,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    try:
        groups = data["data"]["viewer"]["zones"][0]["httpRequests1dGroups"]
    except (KeyError, IndexError, TypeError):
        raise SystemExit(f"Cloudflare API error: {data.get('errors')}")
    return {
        "requests": sum(g["sum"]["requests"] for g in groups),
        "pageViews": sum(g["sum"]["pageViews"] for g in groups),
        "visitors": sum(g["uniq"]["uniques"] for g in groups),  # sum of daily uniques
    }


def project_card(title, badge, desc, stack, meta_svg, accent):
    h = 136
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" font-family="{SANS}">
  <rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="10" fill="{BG}" stroke="{BORDER}" stroke-opacity="0.10"/>
  <text x="24" y="38" font-size="19" font-weight="700" fill="#ffffff">{esc(title)}</text>
  <text x="{W - 24}" y="38" text-anchor="end" font-size="12" font-weight="600" fill="{accent}">{esc(badge)}</text>
  <text x="24" y="66" font-size="13" fill="#cfcdf5">{esc(desc)}</text>
  <text x="24" y="92" font-size="11.5" font-family="{MONO}" fill="#8f8bc7">{esc(stack)}</text>
  <text x="24" y="116" font-size="11.5" font-family="{MONO}" fill="#a9a5d9">{meta_svg}</text>
</svg>
"""


def traffic_strip(stats):
    w, h = 460, 44
    v = lambda t: f'<tspan fill="#ffffff" font-weight="700">{t}</tspan>'
    text = (
        f"{v(fmt(stats['requests']))} requests &#183; {v(fmt(stats['pageViews']))} views"
        f" &#183; {v(fmt(stats['visitors']))} visitors"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{MONO}">
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" fill="{BG}" stroke="{BORDER}" stroke-opacity="0.10"/>
  <circle cx="20" cy="22" r="4" fill="{GREEN}"/>
  <text x="34" y="26" font-size="11.5" fill="#a9a5d9">{text}</text>
  <text x="{w - 18}" y="26" text-anchor="end" font-size="10.5" fill="#8f8bc7">30d</text>
</svg>
"""


def write(path, svg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{path} updated")


def build_static():
    for path, c in STATIC_CARDS.items():
        write(
            path,
            project_card(c["title"], c["badge"], c["desc"], c["stack"], esc(c["meta"]), c["accent"]),
        )


if __name__ == "__main__":
    if "--static" in sys.argv:
        build_static()
    else:
        stats = fetch(os.environ["CF_API_TOKEN"], os.environ["CF_ZONE_ID"])
        write("assets/traffic.svg", traffic_strip(stats))
