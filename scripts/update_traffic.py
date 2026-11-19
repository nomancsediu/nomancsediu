"""Build the project cards in assets/.

Default run (used by the GitHub Action):
    Fetches 30-day traffic from the Cloudflare GraphQL Analytics API and writes
    assets/traffic.svg  (the Admission Informer card, with live numbers).
    Env: CF_API_TOKEN (Zone > Analytics > Read), CF_ZONE_ID

Static run (no API, no secrets):
    python3 scripts/update_traffic.py --static
    Rewrites the two static cards: assets/card-ailab.svg, assets/card-boardsnap.svg
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

GREEN, AMBER, PURPLE = "#4ade80", "#fbbf24", "#a78bfa"

ADMISSION = dict(
    title="Admission Informer",
    badge="Live",
    desc="Bangla university admission portal. Gemma Vision reads circulars from images.",
    stack="Django REST Framework · Next.js · Gemma Vision · AWS · Cloudflare",
    accent=GREEN,
)
STATIC_CARDS = {
    "assets/card-ailab.svg": dict(
        title="AI Assisted Programming Lab Evaluation Platform",
        badge="Pilot at DIU",
        desc="AI-assisted evaluation of programming lab submissions.",
        stack="Django REST Framework · PostgreSQL · Redis · Celery · AWS · Cloudflare",
        meta="# Final Year Design Project · Daffodil International University",
        accent=AMBER,
    ),
    "assets/card-boardsnap.svg": dict(
        title="BoardSnap",
        badge="2nd Place",
        desc="Turns a whiteboard photo into notes, code, flashcards and a quiz.",
        stack="FastAPI · React · Gemma Vision",
        meta="# Team Leader · Build With Gemma @ Bangladesh",
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


def live_meta(s):
    v = lambda t: f'<tspan fill="#ffffff" font-weight="700">{t}</tspan>'
    return (
        f"# {v(fmt(s['requests']))} requests &#183; {v(fmt(s['pageViews']))} page views"
        f" &#183; {v(fmt(s['visitors']))} visitors (daily total) &#183; last 30 days"
    )


def project_card(title, badge, desc, stack, meta_svg, accent):
    w, h = 760, 160
    bw = len(badge) * 7.4 + 28
    bx = w - 24 - bw
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{SANS}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0f0c29"/>
      <stop offset="0.55" stop-color="#25214f"/>
      <stop offset="1" stop-color="#1b1b33"/>
    </linearGradient>
  </defs>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="url(#bg)" stroke="#ffffff" stroke-opacity="0.12"/>
  <rect x="0.5" y="26" width="4" height="108" rx="2" fill="{accent}"/>
  <text x="28" y="44" font-size="21" font-weight="700" fill="#ffffff">{esc(title)}</text>
  <rect x="{bx:.0f}" y="24" width="{bw:.0f}" height="26" rx="13" fill="{accent}" fill-opacity="0.16" stroke="{accent}" stroke-opacity="0.6"/>
  <text x="{bx + bw / 2:.0f}" y="41.5" text-anchor="middle" font-size="12" font-weight="600" fill="{accent}">{esc(badge)}</text>
  <text x="28" y="74" font-size="13.5" fill="#cfcdf5">{esc(desc)}</text>
  <text x="28" y="102" font-size="12" font-family="{MONO}" fill="#a9a5d9">{esc(stack)}</text>
  <line x1="28" y1="120" x2="{w - 28}" y2="120" stroke="#ffffff" stroke-opacity="0.08"/>
  <text x="28" y="144" font-size="12" font-family="{MONO}" fill="#8f8bc7">{meta_svg}</text>
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
        a = ADMISSION
        write(
            "assets/traffic.svg",
            project_card(a["title"], a["badge"], a["desc"], a["stack"], live_meta(stats), a["accent"]),
        )
