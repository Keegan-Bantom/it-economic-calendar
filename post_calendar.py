#!/usr/bin/env python3
"""
Institutional Traders Community - daily high-impact news poster.

Pulls the public Forex Factory weekly calendar feed, keeps today's
high-impact events (and bank holidays) for the major currencies, and
posts a formatted embed to a Discord channel webhook.

Env vars:
  DISCORD_WEBHOOK_URL  (required unless --dry-run)
  TZ_NAME              display timezone, default Africa/Johannesburg
Flags:
  --dry-run            print the Discord payload instead of posting
  --fixture PATH       read events from a local JSON file (for testing)
  --date YYYY-MM-DD    pretend "today" is this date (for testing)
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

FEEDS = [
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.json",  # optional; covers week rollover
]
MAJORS = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "CNY"]
FLAGS = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "JPY": "🇯🇵", "AUD": "🇦🇺",
    "NZD": "🇳🇿", "CAD": "🇨🇦", "CHF": "🇨🇭", "CNY": "🇨🇳",
}
BRAND_ORANGE = 0xF75038
CALM_GREEN = 0x2ECC71
MAX_FIELDS = 25  # Discord limit per embed
USER_AGENT = "InstitutionalTradersCalendarBot/1.0 (+discord community)"


def fetch_events(fixture=None):
    if fixture:
        with open(fixture, encoding="utf-8") as f:
            return json.load(f)
    events, seen = [], set()
    for i, url in enumerate(FEEDS):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
            if i == 0:
                raise SystemExit(f"Could not load main calendar feed: {e}")
            print(f"Note: optional feed skipped ({url}): {e}", file=sys.stderr)
            continue
        for ev in data:
            key = (ev.get("title"), ev.get("country"), ev.get("date"))
            if key not in seen:
                seen.add(key)
                events.append(ev)
    return events


def todays_events(events, today, tz):
    high, holidays = [], []
    for ev in events:
        if ev.get("country") not in MAJORS:
            continue
        try:
            when = dt.datetime.fromisoformat(ev["date"]).astimezone(tz)
        except (KeyError, ValueError):
            continue
        if when.date() != today:
            continue
        impact = (ev.get("impact") or "").lower()
        if impact == "high":
            high.append((when, ev))
        elif impact == "holiday":
            holidays.append(ev)
    high.sort(key=lambda x: (x[0], MAJORS.index(x[1]["country"])))
    return high, holidays


def fmt_value(v):
    v = (v or "").strip()
    return v if v else "—"


def build_payload(high, holidays, today, tz_label):
    date_str = today.strftime("%A, %d %B %Y")
    footer = {"text": f"Times in {tz_label} · Source: Forex Factory · Times can change · Not financial advice"}

    holiday_lines = [
        f"{FLAGS.get(h['country'], '')} **{h['country']}** · {h.get('title', 'Bank Holiday')}"
        for h in holidays
    ]

    if not high:
        desc = "✅ **No high-impact news scheduled for the major currencies today.**\nTrade your plan and manage your risk."
        embed = {
            "title": f"🗓️ Economic Calendar · {date_str}",
            "description": desc,
            "color": CALM_GREEN,
            "footer": footer,
        }
        if holiday_lines:
            embed["fields"] = [{
                "name": "🏦 Bank holidays (expect thinner liquidity)",
                "value": "\n".join(holiday_lines)[:1024],
                "inline": False,
            }]
        return {"embeds": [embed], "allowed_mentions": {"parse": []}}

    currencies = sorted({ev["country"] for _, ev in high}, key=MAJORS.index)
    desc = (
        f"🔴 **{len(high)} high-impact event{'s' if len(high) != 1 else ''}** today for "
        + " ".join(f"{FLAGS[c]} {c}" for c in currencies)
        + "\n⚠️ Expect volatility and wider spreads around these times. Consider staying flat or tightening risk."
    )

    fields = []
    for when, ev in high:
        fields.append({
            "name": f"🔴 {when.strftime('%H:%M')} · {FLAGS.get(ev['country'], '')} {ev['country']}",
            "value": (
                f"**{ev.get('title', 'Event')}**\n"
                f"Forecast: `{fmt_value(ev.get('forecast'))}` · Previous: `{fmt_value(ev.get('previous'))}`"
            ),
            "inline": False,
        })

    holiday_field = None
    if holiday_lines:
        holiday_field = {
            "name": "🏦 Bank holidays (expect thinner liquidity)",
            "value": "\n".join(holiday_lines)[:1024],
            "inline": False,
        }

    embeds = []
    chunks = [fields[i:i + MAX_FIELDS] for i in range(0, len(fields), MAX_FIELDS)]
    for idx, chunk in enumerate(chunks):
        e = {"color": BRAND_ORANGE, "fields": chunk}
        if idx == 0:
            e["title"] = f"🗓️ High-Impact News · {date_str}"
            e["description"] = desc
        embeds.append(e)
    if holiday_field:
        if len(embeds[-1]["fields"]) < MAX_FIELDS:
            embeds[-1]["fields"].append(holiday_field)
        else:
            embeds.append({"color": BRAND_ORANGE, "fields": [holiday_field]})
    embeds[-1]["footer"] = footer
    return {"embeds": embeds[:10], "allowed_mentions": {"parse": []}}


def post(webhook, payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status not in (200, 204):
            raise SystemExit(f"Discord returned HTTP {r.status}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fixture")
    ap.add_argument("--date")
    args = ap.parse_args()

    tz_name = os.environ.get("TZ_NAME", "Africa/Johannesburg")
    tz = ZoneInfo(tz_name)
    today = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(tz).date()
    offset = dt.datetime.now(tz).strftime("%z")
    tz_label = "SAST (GMT+2)" if tz_name == "Africa/Johannesburg" else f"{tz_name} (UTC{offset[:3]}:{offset[3:]})"

    events = fetch_events(args.fixture)
    high, holidays = todays_events(events, today, tz)
    payload = build_payload(high, holidays, today, tz_label)

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        raise SystemExit("DISCORD_WEBHOOK_URL is not set")
    post(webhook, payload)
    print(f"Posted {len(high)} high-impact event(s) and {len(holidays)} holiday(s) for {today}.")


if __name__ == "__main__":
    main()
