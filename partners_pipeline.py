import os
import re
import json
import time
import random
import urllib.parse
from datetime import datetime
import argparse
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv
import urllib3
import resend
from rich.console import Console
from rich.panel import Panel
import libsql_client
import sys
import io

# Ensure UTF-8 output on Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
load_dotenv(".env")
load_dotenv("crm/.env")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
console = Console()

# ---------------------------------------------------------------------------
# Models & Prompts
# ---------------------------------------------------------------------------

class PartnerAIResponse(BaseModel):
    is_compatible: bool
    partner_focus: str
    pitch: str
    subject: str

CA_PITCH_PROMPT = '''You are a B2B partnerships director for "Svantham Software" (custom software development agency).
We build custom ERP, billing automation, POS, and inventory software for Indian SMEs (starting from ₹10,000, zero recurring subscription).
Given this Accounting/CA firm: "{name}"
And their website content: "{context}"

1. Decide if this is a genuine Chartered Accountant, Tax Consultant, Auditor, or Financial Advisory firm.
2. Identify their primary client focus or service area in 2-4 words for the remarks column (e.g. "GST & Tax Advisory", "Corporate Audit Practice", "SME Accounting Services").
3. Write a SHORT, professional, punchy B2B cold email proposal (max 3 sentences) to the CA/Managing Partner:
   - Sentence 1: Acknowledge their role managing financial health and audits for growing businesses.
   - Sentence 2: Propose a mutually beneficial referral partnership where they introduce SME clients struggling with billing/inventory/Excel bottlenecks to Svantham Software for custom software.
   - Sentence 3: Mention our attractive referral fee/commission for every referred project.
4. Provide a catchy, professional email subject line (e.g. "Partnership proposal for {name} | Client Software Referrals").
'''

AGENCY_PITCH_PROMPT = '''You are a B2B partnerships director for "Svantham Software" (backend engineering & custom software agency).
We act as a silent / white-label backend development team (APIs, Database design, complex web portals, SaaS, CRM/ERP backend, cloud infrastructure).
Given this Design / Marketing Agency: "{name}"
And their website content: "{context}"

1. Decide if this is a boutique design, UI/UX, branding, advertising, or digital marketing agency.
2. Identify their primary creative focus in 2-4 words for the remarks column (e.g. "UI/UX & Branding Studio", "Performance Marketing Agency", "Creative Digital Agency").
3. Write a SHORT, punchy B2B cold email proposal (max 3 sentences) to the agency founder/director:
   - Sentence 1: Compliment their focus on branding/marketing/creative work.
   - Sentence 2: Position Svantham Software as their reliable, white-label backend tech engineering partner for complex web applications, client portals, or API integrations.
   - Sentence 3: Highlight that they can deliver full-stack, high-ticket tech projects to clients without hiring full-time backend developers.
4. Provide an intriguing, professional email subject line (e.g. "White-label backend tech partner for {name}").
'''

CA_STATIC_WP_PITCH = '''*{name}*,

Do any of your audit or accounting clients struggle with _billing bottlenecks_, _inventory tracking_, or _outgrowing Excel_?

We build *custom business software* (ERP, Custom POS, Inventory & Billing Automation) starting from just *₹10,000* with *zero monthly subscription*.

> *Referral Partnership:* Introduce clients who need custom software, and we offer an attractive *Referral Commission / Incentive* on every successful project!

Check our portfolio & experience: https://svantham.in/tailored

Regards,
Svantham Software
Urapakkam'''

AGENCY_STATIC_WP_PITCH = '''*{name}*,

Does your agency need a reliable tech team to handle *complex web applications*, *backend engineering*, or *custom client portals*?

While you focus on _branding, UI/UX, and marketing_, we handle *Backend APIs, Databases, Custom Dashboards, and Cloud Infrastructure*.

> *White-Label Tech Partner:* Deliver high-ticket web software under your own agency brand with *zero in-house backend hiring overhead*!

Check out our technical experience: https://svantham.in/tailored

Regards,
Svantham Software
Urapakkam'''

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def check_env_vars():
    required = ["GCP_API_KEY", "GEMINI_API_KEY", "RESEND_API_KEY", "DATABASE_URL", "DATABASE_AUTH_TOKEN"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        console.print(f"[bold red]Missing environment variables: {', '.join(missing)}[/bold red]")
        sys.exit(1)


def generate_expanding_grid(start_lat, start_lng, max_radius_km, step_km=5.0):
    '''Yields lat, lng nodes in concentric rings from 0 up to max_radius_km.'''
    yield start_lat, start_lng
    
    import math
    km_per_lat = 111.0
    km_per_lng = 111.0 * math.cos(math.radians(start_lat))

    current_r = step_km
    while current_r <= max_radius_km:
        lat_step = current_r / km_per_lat
        lng_step = current_r / km_per_lng

        yield start_lat + lat_step, start_lng
        yield start_lat - lat_step, start_lng
        yield start_lat, start_lng + lng_step
        yield start_lat, start_lng - lng_step
        yield start_lat + lat_step, start_lng + lng_step
        yield start_lat - lat_step, start_lng - lng_step
        yield start_lat + lat_step, start_lng - lng_step
        yield start_lat - lat_step, start_lng + lng_step
        
        current_r += step_km


def fetch_places_by_query(api_key, query_text, lat, lng, radius_meters=15000):
    """Uses Google Places API (New) TextSearch with location bias to find targeted partners."""
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "X-Goog-Api-Key": api_key,
        "Content-Type": "application/json",
        "X-Goog-FieldMask": (
            "places.displayName,places.nationalPhoneNumber,"
            "places.websiteUri,places.googleMapsUri,"
            "places.primaryType,places.types,places.formattedAddress"
        ),
    }
    payload = {
        "textQuery": query_text,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": min(radius_meters, 50000.0),
            }
        },
        "maxResultCount": 20
    }
    response = requests.post(url, headers=headers, json=payload, timeout=12)
    response.raise_for_status()
    return response.json().get("places", [])


def sanitize_email(raw_email):
    if not raw_email:
        return None
    cleaned = raw_email.strip().lower().strip(""";:,'"!#* \t\n\r""").replace('.@', '@')
    return cleaned if re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', cleaned) else None


def extract_phone_from_text(text):
    patterns = [
        r'(?:(?:\+91|91|0)[\s\-]?)?(?:[6-9]\d{9})',
        r'(?:(?:\+91|91|0)[\s\-]?)?(?:\d{2,5}[\s\-]?\d{6,8})',
    ]
    found = []
    for pat in patterns:
        for m in re.finditer(pat, text):
            digits = re.sub(r'\D', '', m.group())
            if len(digits) >= 10:
                found.append(digits)
    for d in found:
        if len(d) == 10 and d[0] in '6789':
            return '+91' + d
        if len(d) == 12 and d.startswith('91') and d[2] in '6789':
            return '+' + d
    if found:
        d = found[0]
        if len(d) == 10:
            return '+91' + d
        if len(d) == 12 and d.startswith('91'):
            return '+' + d
    return None


def scrape_website(url):
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        resp = requests.get(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'},
            timeout=12,
            verify=False,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        full_text = soup.get_text(separator=' ', strip=True)

        email = None
        for a in soup.find_all('a', href=True):
            if a['href'].lower().startswith('mailto:'):
                email = sanitize_email(a['href'][7:].split('?')[0].strip())
                if email:
                    break

        if not email:
            match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', full_text)
            if match:
                found = match.group(0)
                image_exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
                if not any(found.lower().endswith(ext) for ext in image_exts):
                    email = sanitize_email(found)

        phone = None
        for a in soup.find_all('a', href=True):
            href_lower = a['href'].lower()
            if href_lower.startswith('tel:') or href_lower.startswith('callto:'):
                prefix_len = 7 if href_lower.startswith('callto:') else 4
                digits = re.sub(r'\D', '', a['href'][prefix_len:])
                if len(digits) >= 10:
                    candidate = '+91' + digits[-10:] if not digits.startswith('91') else '+' + digits
                    if not phone or digits[-10] in '6789':
                        phone = candidate

        if not phone:
            contact_text = ''
            for selector in ['footer', '[id*="contact"]', '[class*="contact"]', '[id*="footer"]', '[class*="footer"]']:
                for sec in soup.select(selector):
                    contact_text += ' ' + sec.get_text(separator=' ', strip=True)
            if contact_text.strip():
                phone = extract_phone_from_text(contact_text)

        if not phone:
            phone = extract_phone_from_text(full_text)

        return email, full_text, phone
    except Exception as e:
        console.print(f"  [dim]Scraping note for {url}: {e}[/dim]")
        return None, "", None


def format_phone(raw_phone):
    clean = re.sub(r'\D', '', raw_phone)
    if clean.startswith('0'):
        clean = '91' + clean[1:]
    elif len(clean) == 10:
        clean = '91' + clean
    return clean


def get_wa_url(phone_e164, text):
    encoded = urllib.parse.quote(text)
    return f'https://wa.me/{phone_e164[-12:]}?text={encoded}'


def send_partner_email(to_address, subject, pitch_text, business_name, target_type):
    html_body = pitch_text.replace('\n', '<br>')
    html_body = re.sub(r'\*(.*?)\*', r'<strong>\1</strong>', html_body)
    html_body = re.sub(r'\_(.*?)\_', r'<em>\1</em>', html_body)

    badge_text = (
        "<strong>Partnership & Referral Incentives on all projects.</strong>"
        if target_type == "ca"
        else "<strong>White-label Backend Engineering & Cloud Hosting Partner.</strong>"
    )

    full_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; background: #f9f9f9; margin: 0; padding: 40px 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 30px;">
        <div style="font-size: 16px;">
            <img src="https://r2.svantham.in/tailored/logos/email_logo.png" alt="Svantham Software" style="max-height: 45px; display: block; margin: 0 auto 25px auto;">
            Hi <u>{business_name}</u> Team,<br><br>
            {html_body}<br><br>
            Regards,<br><strong>Svantham Software</strong>
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; padding: 12px 16px; border-radius: 6px; margin-top: 20px; font-size: 14px; text-align: center;">
                {badge_text}
            </div>
            <p style="margin-top: 25px; font-size: 14px; text-align: center;">
                <a href="https://svantham.in/tailored" style="color: #2563eb; text-decoration: none; font-weight: 600;">Explore Svantham Software &rarr;</a>
            </p>
        </div>
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #888; text-align: center;">
            <p>You received this email because we identified mutual partnership opportunities with your firm. Reply with "Unsubscribe" to opt out.</p>
        </div>
    </div>
</body>
</html>'''

    resend.Emails.send({
        "from": "Svantham Software <hello@svantham.in/tailored>",
        "reply_to": "kaushikkalesh@gmail.com",
        "to": [to_address],
        "subject": subject,
        "html": full_html,
    })

# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Svantham B2B Partner Lead Generation Pipeline")
    parser.add_argument("--lat",    type=float, default=12.8647896, help="Central Latitude")
    parser.add_argument("--lng",    type=float, default=80.061107,  help="Central Longitude")
    parser.add_argument("--radius", type=float, default=10,         help="Search Radius in km")
    parser.add_argument("--cap",    type=int,   default=10,         help="Max leads to collect")
    parser.add_argument("--test",   type=str,   metavar="EMAIL",    help="Test mode: 1 lead, email to this address, skip DB save")
    args = parser.parse_args()

    if args.test:
        args.cap = 1

    check_env_vars()

    gcp_api_key  = os.environ["GCP_API_KEY"]
    gemini_key   = os.environ["GEMINI_API_KEY"]
    resend.api_key = os.environ["RESEND_API_KEY"]
    db_url       = os.environ["DATABASE_URL"].replace("libsql://", "https://")
    db_token     = os.environ["DATABASE_AUTH_TOKEN"]

    genai_client = genai.Client(api_key=gemini_key)

    console.print(Panel.fit("Svantham Partner Leads Pipeline Started | Target: ALL", style="bold cyan"))

    # Connect to Turso DB & load existing leads for deduplication
    try:
        client = libsql_client.create_client_sync(db_url, auth_token=db_token)
        existing_res = client.execute("SELECT phone, LOWER(business) FROM leads")
        existing_phones = {str(r[0]).strip() for r in existing_res.rows if r[0]}
        existing_names = {str(r[1]).strip() for r in existing_res.rows if r[1]}
        console.print(f"[green][OK] Loaded {len(existing_names)} existing leads from Turso for deduplication.[/green]\n")
    except Exception as e:
        console.print(f"[bold red]Database connection failed: {e}[/bold red]")
        sys.exit(1)

    # Search queries map
    ca_queries = [
        "Chartered Accountant",
        "Auditor",
        "Tax Consultant",
        "Financial Advisor",
        "Accounting Firm"
    ]
    agency_queries = [
        "Digital Marketing Agency",
        "Design Agency",
        "Web Design Company",
        "Branding Studio",
        "Creative Agency"
    ]

    segments_to_run = [
        ("ca", "referrer", CA_PITCH_PROMPT, CA_STATIC_WP_PITCH, ca_queries),
        ("agency", "partner", AGENCY_PITCH_PROMPT, AGENCY_STATIC_WP_PITCH, agency_queries)
    ]

    # Grid search cache
    cache_file = "searched_partner_grids.txt"
    searched_grids = set()
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            searched_grids = {line.strip() for line in f if line.strip()}

    collected = []
    processed = {s[1]: 0 for s in segments_to_run}
    seen_names = set()

    for lat, lng in generate_expanding_grid(args.lat, args.lng, args.radius, step_km=4.0):
        if all(v >= args.cap for v in processed.values()):
            console.print(f"\n[bold yellow]DONE: {args.cap} leads collected per segment.[/bold yellow]")
            break

        grid_key = f"{lat:.4f},{lng:.4f}"
        if grid_key in searched_grids:
            continue

        console.print(f"\n[cyan]Searching near {lat:.6f}, {lng:.6f}...[/cyan]")
        searched_grids.add(grid_key)
        with open(cache_file, "a") as f:
            f.write(grid_key + "\n")

        for target_key, segment_name, prompt_tmpl, static_wp_tmpl, query_list in segments_to_run:
            if processed[segment_name] >= args.cap:
                continue

            for query_text in query_list:
                if processed[segment_name] >= args.cap:
                    break

                try:
                    places = fetch_places_by_query(gcp_api_key, query_text, lat, lng)
                except Exception as e:
                    console.print(f"  [red]Places query error ({query_text}): {e}[/red]")
                    continue

                for place in places:
                    if processed[segment_name] >= args.cap:
                        break

                    name    = place.get('displayName', {}).get('text', 'Unknown')
                    phone   = place.get('nationalPhoneNumber', '')
                    website = place.get('websiteUri', '')
                    gmaps   = place.get('googleMapsUri', '')

                    if name in seen_names:
                        continue
                    seen_names.add(name)

                    if not phone and not website:
                        continue
                    if phone in existing_phones:
                        continue
                    if name.lower() in existing_names:
                        continue

                    console.print(f"\n[bold]Evaluating [{segment_name.upper()}]:[/bold] {name}")

                    email, page_text, scraped_phone = ("", "", None)
                    if website:
                        console.print(f"  [dim]Scraping {website}...[/dim]")
                        email, page_text, scraped_phone = scrape_website(website)
                        if not phone and scraped_phone:
                            phone = scraped_phone
                            console.print(f"  [dim]Using scraped phone: {phone}[/dim]")

                    ai_context = page_text[:10000] if page_text else f"Business Name: {name}. No website."
                    prompt = prompt_tmpl.format(name=name, context=ai_context)

                    console.print(f"  [blue]Calling Gemini 3.5 Flash-Lite ({segment_name})...[/blue]")
                    try:
                        chat = genai_client.chats.create(
                            model='gemini-3.5-flash-lite',
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=PartnerAIResponse,
                                temperature=0.7,
                            )
                        )
                        ai_response = chat.send_message(prompt)
                        ai_data = json.loads(ai_response.text)
                    except Exception as e:
                        if "429" in str(e):
                            console.print("[bold red]Rate limit reached. Pausing.[/bold red]")
                            time.sleep(5)
                            continue
                        console.print(f"  [red]AI error: {e}[/red]")
                        continue

                    if not ai_data.get('is_compatible', True):
                        console.print("  [yellow]Dropped: AI flagged incompatible.[/yellow]")
                        continue

                    pitch   = ai_data.get('pitch', '').strip()
                    remarks = ai_data.get('partner_focus', 'B2B Partner')
                    subject = ai_data.get('subject', f"Partnership opportunity for {name}")

                    if not pitch:
                        console.print("  [yellow]Dropped: No pitch generated.[/yellow]")
                        continue

                    pitch = pitch.replace(name, f"*{name}*")
                    status = "Contacted" if (not phone and email) else "Pending"

                    # Static WhatsApp pitch for this partner segment
                    pitch_url = ""
                    if phone:
                        e164 = format_phone(phone)
                        static_wp_text = static_wp_tmpl.format(name=name)
                        pitch_url = get_wa_url(e164, static_wp_text)

                    idea_url = "" # Dynamic idea is not needed for partner leads
                    added_date = datetime.now().strftime('%Y-%m-%d')

                    # row columns:
                    # stage, business, website, phone, email, status, remarks, idea_url, date, pitch_url, segment, pitch, subject, target_key
                    row = [
                        "main", name, website or gmaps, phone, email or "",
                        status, remarks, idea_url, added_date, pitch_url,
                        segment_name, pitch, subject, target_key
                    ]
                    collected.append(row)

                    if phone:
                        existing_phones.add(phone)
                    existing_names.add(name.lower())

                    processed[segment_name] += 1
                    console.print(f"  [green][OK] Collected Partner Lead {processed[segment_name]}/{args.cap}: {name} ({segment_name})[/green]")

    # --- Save to Turso ---
    if collected and not args.test:
        console.print(f"\n[bold blue]Saving {len(collected)} partner rows to Turso...[/bold blue]")
        try:
            for r in collected:
                client.execute(
                    '''INSERT INTO leads (stage, business, website, phone, email, status, remarks, idea_url, date, pitch_url, segment)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    r[:11]
                )
            console.print(f"[green][OK] Saved {len(collected)} partner rows to Turso.[/green]")
        except Exception as e:
            console.print(f"[bold red]DB save error: {e}[/bold red]")
    elif args.test:
        console.print("\n[yellow]Test mode enabled: skipping database insert.[/yellow]")
    else:
        console.print("\n[yellow]No new partner leads collected.[/yellow]")

    try:
        client.close()
    except Exception:
        pass

    # --- Send partner emails ---
    if collected:
        console.print(f"\n[bold blue]Sending partner outreach emails...[/bold blue]")
        for row in collected:
            b_name     = row[1]
            l_email    = row[4]
            l_pitch    = row[11]
            l_subject  = row[12]
            target_key = row[13]

            target = args.test if args.test else l_email
            if not target:
                console.print(f"  [dim]No email for {b_name}, skipping email outreach.[/dim]")
                continue

            console.print(f"  [cyan]Emailing {target} for {b_name}...[/cyan]")
            try:
                send_partner_email(target, l_subject, l_pitch, b_name, target_key)
                console.print(f"  [green][OK] Sent partner email.[/green]")
                sleep_time = random.uniform(2, 4)
                time.sleep(sleep_time)
            except Exception as e:
                console.print(f"  [red]Email delivery error: {e}[/red]")

    total_processed = sum(processed.values())
    console.print(f"\n[bold green]Pipeline completed! {total_processed} partner leads processed ({processed}).[/bold green]")


if __name__ == "__main__":
    main()
