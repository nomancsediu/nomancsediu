"""Generate assets/traffic.svg from the Cloudflare GraphQL Analytics API.

Env vars: CF_API_TOKEN (Zone > Analytics > Read), CF_ZONE_ID
Optional: CARD_TITLE (default "Admission Informer")
"""
import datetime as dt
import json
import os
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


def render(title, cols, footer):
    width, height = 495, 130
    step = (width - 48) / len(cols)
    items = ""
    for i, (value, label) in enumerate(cols):
        x = 24 + i * step
        items += (
            f'<text x="{x:.0f}" y="86" font-size="30" font-weight="700" fill="#ffffff">{value}</text>'
            f'<text x="{x:.0f}" y="108" font-size="12" fill="#a9a5d9">{label}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0f0c29"/>
      <stop offset="0.5" stop-color="#302b63"/>
      <stop offset="1" stop-color="#24243e"/>
    </linearGradient>
  </defs>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="url(#bg)" stroke="#ffffff" stroke-opacity="0.12"/>
  <text x="24" y="36" font-size="14" font-weight="600" fill="#d9d6ff">{title} &#183; last 30 days</text>
  <circle cx="{width - 24}" cy="31" r="4" fill="#22c55e"/>
  <text x="{width - 34}" y="35" font-size="11" text-anchor="end" fill="#a9a5d9">{footer}</text>
  {items}
</svg>
"""


if __name__ == "__main__":
    stats = fetch(os.environ["CF_API_TOKEN"], os.environ["CF_ZONE_ID"])
    svg = render(
        os.environ.get("CARD_TITLE", "Admission Informer"),
        [
            (fmt(stats["requests"]), "Requests"),
            (fmt(stats["pageViews"]), "Page views"),
            (fmt(stats["visitors"]), "Visitors (daily total)"),
        ],
        f"Cloudflare Analytics &#183; {dt.date.today()}",
    )
    os.makedirs("assets", exist_ok=True)
    with open("assets/traffic.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("assets/traffic.svg updated")
