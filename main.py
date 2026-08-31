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


load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
console = Console()

# ---------------------------------------------------------------------------
# Models & Configuration
# ---------------------------------------------------------------------------

class PitchResponse(BaseModel):
    is_compatible: bool
    software_needs: str
    pitch: str
    subject: str

AI_PITCH_PROMPT = '''You are an expert tech sales consultant for "K2M Services".
We build custom software (Mobile Apps, Web Apps, CRM, ERP, client portals, internal tools).
Given this business: "{name}"
And their website content: "{context}"

1. Decide if they are a B2B business or industrial/service business that might need custom software.
(Exclude B2C retail, restaurants, hotels, gyms, marriage halls, sports turf, schools, hospitals, places of worship)
2. Identify 1-2 core software needs (e.g. "CRM", "Inventory System", "Client Portal").
3. Write a SHORT, punchy, cold email pitch (max 3 sentences).
   - Sentence 1: A personalized observation about their business ops.
   - Sentence 2: Introduce a specific custom software solution (Mobile App, Website, CRM, ERP, AI, etc.) that would streamline their workflows.
4. Provide a catchy email subject line.
'''

STATIC_WP_PITCH = '''*{name}*,

_Innum Excel use panitu irukingala?  Unga business work ah automate pananuma??_

Unga business work ah simplify pana: *Mobile App, Website, CRM, ERP, AI Integration, etc* venuma??
Naanga _customized_ ah pani tharuvom, along with *domain & hosting setup, with annual maintenance plans.*

> Starting from just ₹10,000. Fully yours, no subscription.

Check our experience at https://k2ms.in

Thank you for taking your time to read this!

Regards,
K2M Services
Urapakkam'''

EXCLUDED_PLACE_TYPES = {
    'restaurant', 'cafe', 'fast_food_restaurant', 'bar', 'bakery', 'meal_delivery',
    'meal_takeaway', 'liquor_store', 'supermarket', 'grocery_store', 'convenience_store',
    'shopping_mall', 'clothing_store', 'shoe_store', 'jewelry_store', 'department_store',
    'electronics_store', 'furniture_store', 'hardware_store', 'home_goods_store',
    'gym', 'fitness_center', 'spa', 'beauty_salon', 'hair_salon',
    'hospital', 'doctor', 'dentist', 'pharmacy', 'veterinary_care',
    'school', 'university', 'library', 'church', 'hindu_temple', 'mosque', 'synagogue',
    'lodging', 'hotel', 'motel', 'stadium', 'movie_theater', 'amusement_park',
    'park', 'campground', 'rv_park', 'casino', 'bowling_alley'
}

EXCLUDED_NAME_PATTERNS = [
    r'\b(supermarket|hypermarket|grocery|provisions|store|mart|bazaar)\b',
    r'\b(restaurant|cafe|hotel|motel|resort|inn|lodge|eatery|diner|mess)\b',
    r'\b(gym|fitness|crossfit|sports|turf|arena|stadium)\b',
    r'\b(school|college|university|academy|tuition|institute)\b',
    r'\b(hospital|clinic|dental|pharmacy|medical)\b',
    r'\b(temple|church|mosque|shrine)\b',
    r'\b(mahal|marriage|banquet|hall)\b',
    r'\b(salon|spa|parlour|beauty)\b'
]

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def check_env_vars():
    required = ["GCP_API_KEY", "GEMINI_API_KEY", "RESEND_API_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        console.print(f"[bold red]Missing environment variables: {', '.join(missing)}[/bold red]")
        sys.exit(1)


def generate_expanding_grid(start_lat, start_lng, max_radius_km, step_km=5.0):
    '''Yields lat, lng nodes in concentric rings from 0 up to max_radius_km.'''
    yield start_lat, start_lng
    
    km_per_lat = 111.0
    km_per_lng = 111.0 * (1.0 if start_lat == 0 else abs(round(os.environ.get('dummy', 0)))) # rough approx
    import math
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


def fetch_places(api_key, lat, lng, radius_meters=10000):
    response = requests.post(
        "https://places.googleapis.com/v1/places:searchNearby",
        headers={
            "X-Goog-Api-Key": api_key,
            "Content-Type": "application/json",
            "X-Goog-FieldMask": (
                "places.displayName,places.nationalPhoneNumber,"
                "places.websiteUri,places.googleMapsUri,"
                "places.primaryType,places.types"
            ),
        },
        json={
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": min(radius_meters, 50000.0),
                }
            }
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("places", [])


def sanitize_email(raw_email):
    if not raw_email:
        return None
    cleaned = raw_email.strip().lower().strip(""";:,'"!#* \t\n\r""").replace('.@', '@')
    return cleaned if re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', cleaned) else None


def extract_phone_from_text(text):
    """Extract Indian phone numbers from arbitrary text using regex."""
    patterns = [
        r'(?:(?:\+91|91|0)[\s\-]?)?(?:[6-9]\d{9})',  # Mobile: +91 / 91 / 0 prefix or plain 10-digit starting 6-9
        r'(?:(?:\+91|91|0)[\s\-]?)?(?:\d{2,5}[\s\-]?\d{6,8})',  # Landlines with STD code
    ]
    found = []
    for pat in patterns:
        for m in re.finditer(pat, text):
            digits = re.sub(r'\D', '', m.group())
            if len(digits) >= 10:
                found.append(digits)
    # Prefer 10-digit mobiles starting 6-9
    for d in found:
        if len(d) == 10 and d[0] in '6789':
            return '+91' + d
        if len(d) == 12 and d.startswith('91') and d[2] in '6789':
            return '+' + d
    # Fallback: return first found if any
    if found:
        d = found[0]
        if len(d) == 10:
            return '+91' + d
        if len(d) == 12 and d.startswith('91'):
            return '+' + d
    return None


def scrape_website(url, genai_client=None):
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        resp = requests.get(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'},
            timeout=15,
            verify=False,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        full_text = soup.get_text(separator=' ', strip=True)

        # --- Email extraction ---
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

        # --- Phone extraction: target contact/footer sections first ---
        phone = None

        # 1. Check tel: / callto: links (most reliable)
        for a in soup.find_all('a', href=True):
            href_lower = a['href'].lower()
            if href_lower.startswith('tel:') or href_lower.startswith('callto:'):
                prefix_len = 7 if href_lower.startswith('callto:') else 4
                digits = re.sub(r'\D', '', a['href'][prefix_len:])
                if len(digits) >= 10:
                    candidate = '+91' + digits[-10:] if not digits.startswith('91') else '+' + digits
                    # Prefer mobile (last 10 digits starting 6-9) over landline
                    if not phone or digits[-10] in '6789':
                        phone = candidate

        # 2. Scrape contact/footer sections with targeted regex
        if not phone:
            contact_text = ''
            for selector in ['footer', '[id*="contact"]', '[class*="contact"]',
                             '[id*="footer"]', '[class*="footer"]']:
                sections = soup.select(selector)
                for sec in sections:
                    contact_text += ' ' + sec.get_text(separator=' ', strip=True)

            if contact_text.strip():
                phone = extract_phone_from_text(contact_text)

        # 3. Fall back to scanning full page text
        if not phone:
            phone = extract_phone_from_text(full_text)

        # 4. If still nothing and genai_client is available, ask Gemini
        if not phone and genai_client:
            snippet = full_text[:3000]
            try:
                gem_resp = genai_client.models.generate_content(
                    model='gemini-2.0-flash-lite',
                    contents=(
                        f"Extract only the primary Indian phone number from this text. "
                        f"Return ONLY the 10-digit number or empty string if none found.\n\n{snippet}"
                    ),
                )
                raw = re.sub(r'\D', '', gem_resp.text.strip())
                if len(raw) == 10 and raw[0] in '6789':
                    phone = '+91' + raw
                    console.print(f"  [dim]Phone found via Gemini: {phone}[/dim]")
            except Exception:
                pass

        if phone:
            console.print(f"  [dim]Phone extracted: {phone}[/dim]")

        return email, full_text, phone
    except Exception as e:
        console.print(f"  [dim]Scraping failed for {url}: {e}[/dim]")
        return None, "", None


def is_excluded_place(place, business_name):
    all_types = set([place.get('primaryType', '')] + place.get('types', []))
    if any(t in EXCLUDED_PLACE_TYPES for t in all_types):
        return True
    if any(re.search(pat, business_name, re.IGNORECASE) for pat in EXCLUDED_NAME_PATTERNS):
        return True
    return False


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


def process_stale_leads(client):
    """
    Shifts leads from 'main' to 'call' if their status is 'Contacted'
    and they are older than 7 days, updating status to 'Pending'.
    Leads with no phone (email-only contacted) are intentionally excluded —
    they can't be called/WhatsApp'd so there's no point moving them to follow-up.
    """
    try:
        res = client.execute('''
            UPDATE leads
            SET stage = 'call', status = 'Pending'
            WHERE stage = 'main'
              AND LOWER(status) = 'contacted'
              AND phone IS NOT NULL
              AND TRIM(phone) != ''
              AND date(date) <= date('now', '-7 days')
        ''')
        shifted = res.rows_affected
        if shifted > 0:
            console.print(f"[bold green]Moved {shifted} stale 'Contacted' leads to the Follow-up stage.[/bold green]")
    except Exception as e:
        console.print(f"[red]Error processing stale leads: {e}[/red]")


def send_email(to_address, subject, pitch_text, business_name):
    html_body = pitch_text.replace('\n', '<br>')
    html_body = re.sub(r'\*(.*?)\*', r'<strong>\1</strong>', html_body)
    html_body = re.sub(r'\_(.*?)\_', r'<em>\1</em>', html_body)

    full_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; background: #f9f9f9; margin: 0; padding: 40px 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 30px;">
        <div style="font-size: 16px;">
            <img src="https://r2.k2ms.in/logos/email_logo.png" alt="K2M Services" style="max-height: 45px; display: block; margin: 0 auto 25px auto;">
            Hi <u>{business_name}</u> Team,<br><br>
            {html_body}<br><br>
            Would you like to schedule a quick call to discuss this further?<br><br>
            Regards,<br>K2M Services
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; padding: 12px 16px; border-radius: 6px; margin-top: 20px; font-size: 15px; text-align: center;">
                <strong>Custom software starting from just ₹10,000.</strong> Fully yours, zero recurring fees.
            </div>
            <p style="margin-top: 25px; font-size: 14px;">
                <a href="https://k2ms.in" style="color: #2563eb; text-decoration: none; font-weight: 600;">View our work &rarr;</a>
            </p>
        </div>
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #888; text-align: center;">
            <p>You are receiving this email because we identified your business as a great fit for our solutions. Reply with "Unsubscribe" to opt out.</p>
        </div>
    </div>
</body>
</html>'''

    resend.Emails.send({
        "from": "K2M Services <hello@k2ms.in>",
        "reply_to": "kaushikkalesh@gmail.com",
        "to": [to_address],
        "subject": subject,
        "html": full_html,
    })


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="K2MS AI Lead Generation Pipeline")
    parser.add_argument("--lat",    type=float, default=12.8647896, help="Central Latitude")
    parser.add_argument("--lng",    type=float, default=80.061107,  help="Central Longitude")
    parser.add_argument("--radius", type=float, default=10,         help="Search Radius in km")
    parser.add_argument("--cap",    type=int,   default=20,         help="Max leads to collect")
    parser.add_argument("--test",   type=str,   metavar="EMAIL",
                        help="Test mode: 1 lead, email to this address, skip sheet save")
    args = parser.parse_args()

    if args.test:
        args.cap = 1

    check_env_vars()

    gcp_api_key  = os.environ["GCP_API_KEY"]
    gemini_key   = os.environ["GEMINI_API_KEY"]
    resend.api_key = os.environ["RESEND_API_KEY"]

    genai_client = genai.Client(api_key=gemini_key)

    console.print(Panel.fit("K2MS Leads Pipeline Started", style="bold cyan"))

    # --- Turso Database setup ---
    console.print("[bold blue]Connecting to Turso Database...[/bold blue]")
    try:
        # Load from .env if possible
        from dotenv import load_dotenv
        load_dotenv("crm/.env")

        db_url = os.environ.get("DATABASE_URL")
        db_token = os.environ.get("DATABASE_AUTH_TOKEN")
        if not db_url or not db_token:
            console.print("[bold red]Missing Turso credentials in crm/.env[/bold red]")
            sys.exit(1)

        client = libsql_client.create_client_sync(db_url, auth_token=db_token)
        
        process_stale_leads(client)
        
        existing_res = client.execute("SELECT phone, LOWER(business) FROM leads")
        existing_phones = {str(r[0]).strip() for r in existing_res.rows if r[0]}
        existing_names = {str(r[1]).strip() for r in existing_res.rows if r[1]}
        
        console.print(f"[green][OK] Loaded {len(existing_names)} existing leads from Turso.[/green]\n")
    except Exception as e:
        console.print(f"[bold red]Database connection failed: {e}[/bold red]")
        sys.exit(1)

    # --- Grid search cache ---
    searched_grids = set()
    if os.path.exists("searched_grids.txt"):
        with open("searched_grids.txt") as f:
            searched_grids = {line.strip() for line in f if line.strip()}

    collected = []
    processed = 0
    seen_names = set()

    for lat, lng in generate_expanding_grid(args.lat, args.lng, args.radius):
        if processed >= args.cap:
            console.print(f"\n[bold yellow]DONE: {args.cap} leads collected.[/bold yellow]")
            break

        grid_key = f"{lat:.4f},{lng:.4f}"
        if grid_key in searched_grids:
            continue

        console.print(f"\n[cyan]Searching near {lat:.6f}, {lng:.6f}...[/cyan]")
        try:
            places = fetch_places(gcp_api_key, lat, lng)
            console.print(f"Fetched {len(places)} places")
            searched_grids.add(grid_key)
            with open("searched_grids.txt", "a") as f:
                f.write(grid_key + "\n")
        except Exception as e:
            console.print(f"[red]Places API error: {e}[/red]")
            continue

        for place in places:
            if processed >= args.cap:
                break

            name    = place.get('displayName', {}).get('text', 'Unknown')
            phone   = place.get('nationalPhoneNumber', '')
            website = place.get('websiteUri', '')
            gmaps   = place.get('googleMapsUri', '')

            if name in seen_names:
                continue
            seen_names.add(name)

            console.print(f"\n[bold]Evaluating:[/bold] {name}")

            if is_excluded_place(place, name):
                console.print(f"  [yellow]Dropped: Excluded category/name.[/yellow]")
                continue

            if not phone and not website:
                console.print(f"  [yellow]Dropped: No phone or website.[/yellow]")
                continue

            if phone in existing_phones:
                console.print(f"  [yellow]Dropped: Phone already in DB.[/yellow]")
                continue
            if name.lower() in existing_names:
                console.print(f"  [yellow]Dropped: Name already in DB.[/yellow]")
                continue

            email, page_text, scraped_phone = ("", "", None)
            if website:
                console.print(f"  [dim]Scraping {website}...[/dim]")
                email, page_text, scraped_phone = scrape_website(website, genai_client)
                if not email:
                    console.print("  [dim]No email found.[/dim]")
                # Use scraped phone only if Places API didn't provide one
                if not phone and scraped_phone:
                    phone = scraped_phone
                    console.print(f"  [dim]Using phone from website scrape: {phone}[/dim]")
            else:
                console.print("  [dim]No website.[/dim]")

            ai_context = page_text[:10000] if page_text else f"Business Name: {name}. No website."
            prompt = AI_PITCH_PROMPT.format(name=name, context=ai_context)

            console.print("  [blue]Calling Gemini...[/blue]")
            try:
                ai_response = genai_client.models.generate_content(
                    model='gemini-3.5-flash-lite',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=PitchResponse,
                        temperature=0.7,
                    ),
                )
                ai_data = json.loads(ai_response.text)
            except Exception as e:
                if "429" in str(e):
                    console.print("[bold red]Rate limit hit. Stopping.[/bold red]")
                    break
                console.print(f"  [red]AI error: {e}[/red]")
                continue

            if not ai_data.get('is_compatible', True):
                console.print("  [yellow]Dropped: AI marked incompatible.[/yellow]")
                continue

            pitch   = ai_data.get('pitch', '').strip()
            needs   = ai_data.get('software_needs', 'General')
            subject = ai_data.get('subject', f"Quick question for {name}")

            if not pitch:
                console.print("  [red]Dropped: No pitch generated.[/red]")
                continue

            pitch = pitch.replace(name, f"*{name}*")
            status = "Contacted" if (not phone and email) else "Pending"

            idea_url = ""
            pitch_url = ""
            if phone:
                e164 = format_phone(phone)
                formatted_idea = f"*Thank you for your time! Here's what we have in mind for you:*\n\n{pitch}"
                idea_url = get_wa_url(e164, formatted_idea)
                static_text = STATIC_WP_PITCH.format(name=name)
                pitch_url = get_wa_url(e164, static_text)

            added_date = datetime.now().strftime('%Y-%m-%d')
            
            # stage, business, website, phone, email, status, remarks, idea_url, date, pitch_url
            row = ["main", name, website or gmaps, phone, email or "", status, needs, idea_url, added_date, pitch_url, pitch, subject]
            collected.append(row)

            if phone: existing_phones.add(phone)
            existing_names.add(name.lower())

            processed += 1
            console.print(f"  [green][OK] Lead {processed}/{args.cap}[/green]")

    else:
        console.print("\n[bold yellow]Grid exhausted.[/bold yellow]")

    # --- Save to Turso ---
    if collected and not args.test:
        console.print(f"\n[bold blue]Saving {len(collected)} rows to Turso...[/bold blue]")
        try:
            for r in collected:
                client.execute(
                    '''INSERT INTO leads (stage, business, website, phone, email, status, remarks, idea_url, date, pitch_url)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                    r[:10]
                )
            console.print(f"[green][OK] Saved {len(collected)} rows to Turso.[/green]")
        except Exception as e:
            console.print(f"[bold red]DB save error: {e}[/bold red]")
    elif args.test:
        console.print("\n[yellow]Test mode: skipping DB save.[/yellow]")
    else:
        console.print("\n[yellow]No new leads to save.[/yellow]")
        
    try:
        client.close()
    except:
        pass

    # --- Send emails ---
    if collected:
        console.print(f"\n[bold blue]Sending emails...[/bold blue]")
        for row in collected:
            b_name    = row[1]
            l_email   = row[4]
            l_pitch   = row[10]
            l_subject = row[11]

            target = args.test if args.test else l_email
            if not target:
                console.print(f"  [dim]No email for {b_name}, skipping.[/dim]")
                continue

            console.print(f"  [cyan]Emailing {target} for {b_name}...[/cyan]")
            try:
                send_email(target, l_subject, l_pitch, b_name)
                console.print(f"  [green][OK] Sent.[/green]")
                sleep_time = random.uniform(2, 5)
                console.print(f"  [dim]Sleeping {sleep_time:.1f}s...[/dim]")
                time.sleep(sleep_time)
            except Exception as e:
                console.print(f"  [red]Email failed: {e}[/red]")

    console.print(f"\n[bold green]Done! {processed} new leads processed.[/bold green]")


if __name__ == "__main__":
    main()
