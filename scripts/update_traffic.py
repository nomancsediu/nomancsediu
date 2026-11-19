"""Build the SVG cards in assets/.

Default run (used by the GitHub Action):
    Fetches 30-day traffic from the Cloudflare GraphQL Analytics API and writes
    assets/traffic.svg (a small live-numbers strip for Admission Informer).
    Env: CF_API_TOKEN (Zone > Analytics > Read), CF_ZONE_ID

Static run (no API, no secrets):
    python3 scripts/update_traffic.py --static
    Rewrites assets/banner.svg
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

MONO = "'JetBrains Mono','Fira Code',Consolas,'DejaVu Sans Mono',monospace"
BG, LIME = "#0a0a0a", "#a3e635"
TEXT, DIM = "#d4d4d8", "#71717a"
W = 760


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


def traffic_strip(stats):
    w, h = 440, 40
    v = lambda t: f'<tspan fill="{LIME}" font-weight="700">{t}</tspan>'
    text = (
        f"{v(fmt(stats['requests']))} requests &#183; {v(fmt(stats['pageViews']))} views"
        f" &#183; {v(fmt(stats['visitors']))} visitors"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{MONO}">
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" fill="{BG}" stroke="{LIME}" stroke-opacity="0.55"/>
  <rect x="16" y="16" width="8" height="8" fill="{LIME}"/>
  <text x="34" y="24" font-size="11.5" fill="{DIM}">{text}</text>
  <text x="{w - 16}" y="24" text-anchor="end" font-size="10.5" fill="{DIM}">30d</text>
</svg>
"""


def banner():
    w, h = 1280, 300
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{MONO}">
  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" fill="{BG}" stroke="{LIME}" stroke-width="2"/>
  <text x="48" y="64" font-size="16" fill="{DIM}">~/abdnoman.com</text>
  <text x="48" y="156" font-size="64" font-weight="700" fill="{LIME}">Abdullah Al Noman</text>
  <rect x="48" y="180" width="64" height="3" fill="{LIME}"/>
  <text x="48" y="232" font-size="22" fill="{TEXT}">Backend &#183; AI &#183; Linux &#183; DevOps</text>
  <rect x="{w - 64}" y="{h - 72}" width="16" height="30" fill="{LIME}">
    <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" repeatCount="indefinite"/>
  </rect>
</svg>
"""


def write(path, svg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{path} updated")


def build_static():
    write("assets/banner.svg", banner())


if __name__ == "__main__":
    if "--static" in sys.argv:
        build_static()
    else:
        stats = fetch(os.environ["CF_API_TOKEN"], os.environ["CF_ZONE_ID"])
        write("assets/traffic.svg", traffic_strip(stats))
