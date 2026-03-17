"""
Auto-updates the RSVP list in index.html from Formspree submissions.
Run by GitHub Actions on a schedule.
Requires env var: FORMSPREE_API_KEY
"""

import os
import json
import re
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError

FORM_ID   = "xqeygbbr"
API_KEY   = os.environ.get("FORMSPREE_API_KEY", "")
HTML_FILE = "index.html"

# Seed entries from pre-existing RSVPs (SignupGenius / manual)
SEED = [
    ("Sahana Bhat",    5),
    ("Pallavi Kiran",  4),
    ("Archana Dongre", 4),
]

def fetch_submissions():
    url = f"https://api.formspree.io/api/0/forms/{FORM_ID}/submissions"
    req = Request(url, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    })
    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read())
        return data.get("submissions", [])
    except URLError as e:
        print(f"Error fetching submissions: {e}", file=sys.stderr)
        sys.exit(1)

def parse_submissions(submissions):
    yes_list   = list(SEED)   # start with seeded entries
    maybe_count = 0
    seen_names  = {n.lower() for n, _ in SEED}

    for s in submissions:
        body     = s.get("body", {})
        name     = body.get("name", "").strip()
        attending = body.get("attending", "").strip()
        try:
            guests = max(1, int(body.get("guests", 1)))
        except (ValueError, TypeError):
            guests = 1

        if not name or name.lower() in seen_names:
            continue

        if attending == "Yes":
            yes_list.append((name, guests))
            seen_names.add(name.lower())
        elif attending == "Maybe":
            maybe_count += 1

    total_guests = sum(g for _, g in yes_list)
    return yes_list, maybe_count, total_guests

def build_stats_html(families, total_guests, maybe):
    return (
        f'        <div class="stat"><div class="num">{families}</div><div class="lbl">Families</div></div>\n'
        f'        <div class="stat"><div class="num">{total_guests}</div><div class="lbl">Total Guests</div></div>\n'
        f'        <div class="stat"><div class="num">{maybe}</div><div class="lbl">Maybe</div></div>\n'
    )

def build_list_html(yes_list):
    lines = ""
    for name, guests in yes_list:
        plus = guests - 1
        lines += f'        <li><span>{name}</span><span class="count">+{plus} guests</span></li>\n'
    return lines

def update_html(stats_html, list_html):
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(
        r'<!-- RSVP_STATS_START -->.*?<!-- RSVP_STATS_END -->',
        f'<!-- RSVP_STATS_START -->\n{stats_html}        <!-- RSVP_STATS_END -->',
        content, flags=re.DOTALL
    )
    content = re.sub(
        r'<!-- RSVP_LIST_START -->.*?<!-- RSVP_LIST_END -->',
        f'<!-- RSVP_LIST_START -->\n{list_html}        <!-- RSVP_LIST_END -->',
        content, flags=re.DOTALL
    )

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    subs = fetch_submissions()
    yes_list, maybe_count, total_guests = parse_submissions(subs)
    stats_html = build_stats_html(len(yes_list), total_guests, maybe_count)
    list_html  = build_list_html(yes_list)
    update_html(stats_html, list_html)
    print(f"Updated: {len(yes_list)} families, {total_guests} total guests, {maybe_count} maybe")
