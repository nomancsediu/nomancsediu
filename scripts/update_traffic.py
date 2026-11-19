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
    w, h = 1280, 360
    per = 2 * ((w - 2) + (h - 2))
    ease = 'calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{MONO}">
  <defs>
    <pattern id="dots" width="32" height="32" patternUnits="userSpaceOnUse">
      <rect x="15" y="15" width="2" height="2" fill="{LIME}" fill-opacity="0.10"/>
    </pattern>
    <linearGradient id="scan" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0" stop-color="{LIME}" stop-opacity="0"/>
      <stop offset="1" stop-color="{LIME}" stop-opacity="0.14"/>
    </linearGradient>
    <clipPath id="reveal"><rect x="40" y="96" width="0" height="100">
      <animate attributeName="width" from="0" to="760" dur="1.5s" begin="0.7s" fill="freeze" {ease}/>
    </rect></clipPath>
    <clipPath id="frame"><rect x="1" y="1" width="{w - 2}" height="{h - 2}"/></clipPath>
  </defs>

  <rect width="{w}" height="{h}" fill="#000000"/>
  <rect width="{w}" height="{h}" fill="url(#dots)"/>

  <g clip-path="url(#frame)">
    <rect x="-200" y="0" width="200" height="{h}" fill="url(#scan)">
      <animate attributeName="x" from="-200" to="{w}" dur="7s" begin="2.2s" repeatCount="indefinite"/>
    </rect>
  </g>

  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" fill="none" stroke="{LIME}" stroke-width="2" stroke-dasharray="{per}" stroke-dashoffset="{per}">
    <animate attributeName="stroke-dashoffset" from="{per}" to="0" dur="1.6s" begin="0s" fill="freeze" {ease}/>
  </rect>

  <g stroke="{LIME}" stroke-width="4" fill="none" opacity="0">
    <path d="M1 28 V1 H28"/><path d="M{w - 28} 1 H{w - 1} V28"/>
    <path d="M1 {h - 28} V{h - 1} H28"/><path d="M{w - 28} {h - 1} H{w - 1} V{h - 28}"/>
    <animate attributeName="opacity" from="0" to="1" dur="0.4s" begin="1.4s" fill="freeze"/>
  </g>

  <g opacity="0">
    <text x="48" y="68" font-size="15" letter-spacing="2" fill="{LIME}" fill-opacity="0.6">~/abdnoman.com</text>
    <rect x="{w - 214}" y="55" width="10" height="10" fill="{LIME}">
      <animate attributeName="opacity" values="1;0.2;1" dur="1.8s" repeatCount="indefinite"/>
    </rect>
    <text x="{w - 48}" y="68" text-anchor="end" font-size="15" letter-spacing="2" fill="{LIME}" fill-opacity="0.6">OPEN TO WORK</text>
    <animate attributeName="opacity" from="0" to="1" dur="0.6s" begin="0.4s" fill="freeze"/>
  </g>

  <g clip-path="url(#reveal)">
    <text x="48" y="172" font-size="72" font-weight="700" fill="{LIME}">Abdullah Al Noman</text>
  </g>
  <rect x="48" y="96" width="14" height="82" fill="{LIME}">
    <animate attributeName="x" from="40" to="792" dur="1.5s" begin="0.7s" fill="freeze" {ease}/>
    <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" begin="2.2s" repeatCount="indefinite"/>
  </rect>

  <rect x="48" y="206" width="0" height="3" fill="{LIME}">
    <animate attributeName="width" from="0" to="96" dur="0.7s" begin="1.8s" fill="freeze" {ease}/>
  </rect>

  <g opacity="0">
    <text x="48" y="256" font-size="26" fill="{LIME}">Backend  &#183;  AI  &#183;  Linux  &#183;  DevOps</text>
    <animate attributeName="opacity" from="0" to="1" dur="0.8s" begin="2.0s" fill="freeze"/>
    <animateTransform attributeName="transform" type="translate" from="0 10" to="0 0" dur="0.8s" begin="2.0s" fill="freeze" {ease}/>
  </g>

  <g opacity="0">
    <text x="48" y="312" font-size="15" letter-spacing="1" fill="{LIME}" fill-opacity="0.6">2x Hackathon Winner  /  Daffodil International University  /  Dhaka</text>
    <animate attributeName="opacity" from="0" to="1" dur="0.8s" begin="2.5s" fill="freeze"/>
  </g>
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
