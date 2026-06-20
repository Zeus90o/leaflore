#!/usr/bin/env python3
"""LeafLore static site generator.

Reads data/site.json and data/plants.json and renders a complete static
website into ./public. Pure standard library so it can run unattended.

Usage:
    python build.py
"""
import json
import re
import shutil
import html
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus, urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "public"
ASSETS_SRC = ROOT / "assets"


def load_json(name):
    with open(DATA / name, "r", encoding="utf-8") as f:
        return json.load(f)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def esc(text):
    return html.escape(str(text), quote=True)


def amazon_link(query, site):
    tag = site.get("amazon_associate_tag", "")
    domain = site.get("amazon_domain", "www.amazon.com")
    q = quote_plus(query)
    return f"https://{domain}/s?k={q}&tag={tag}"


def ad_slot(site, label="Advertisement"):
    """Render an ad container. If an AdSense client id is configured, emit the
    AdSense unit; otherwise emit a labelled placeholder so layout is stable."""
    client = site.get("adsense_client", "")
    if client:
        return (
            f'<div class="ad"><span class="ad-label">{label}</span>'
            f'<ins class="adsbygoogle" style="display:block" '
            f'data-ad-client="{esc(client)}" data-ad-format="auto" '
            f'data-full-width-responsive="true"></ins>'
            f'<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script></div>'
        )
    return f'<div class="ad ad--placeholder"><span class="ad-label">{label}</span></div>'


def analytics(site):
    aid = site.get("analytics_id", "")
    if not aid:
        return ""
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={esc(aid)}"></script>'
        f'<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}'
        f'gtag("js",new Date());gtag("config","{esc(aid)}");</script>'
    )


def adsense_head(site):
    client = site.get("adsense_client", "")
    if not client:
        return ""
    return (
        f'<script async src="https://pagead2.googlesyndication.com/pagead/js/'
        f'adsbygoogle.js?client={esc(client)}" crossorigin="anonymous"></script>'
    )


def base_page(site, *, title, description, canonical_path, body, jsonld=None, breadcrumbs=None):
    url = site["url"].rstrip("/")
    canonical = f"{url}{canonical_path}"
    name = esc(site["name"])
    crumbs_html = ""
    if breadcrumbs:
        items = []
        for i, (label, href) in enumerate(breadcrumbs):
            if href:
                items.append(f'<a href="{esc(href)}">{esc(label)}</a>')
            else:
                items.append(f"<span>{esc(label)}</span>")
        crumbs_html = '<nav class="crumbs" aria-label="Breadcrumb">' + " / ".join(items) + "</nav>"

    jsonld_html = ""
    if jsonld:
        jsonld_html = f'<script type="application/ld+json">{json.dumps(jsonld)}</script>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:site_name" content="{name}">
<meta name="twitter:card" content="summary">
<link rel="stylesheet" href="/assets/style.css">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
{adsense_head(site)}
{analytics(site)}
{jsonld_html}
</head>
<body>
<a class="skip-link" href="#main-content">Skip to content</a>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="/"><span class="leaf">&#127807;</span> {name}</a>
    <nav class="main-nav">
      <a href="/">Plants</a>
      <a href="/toxic-to-pets/">Pet Safety</a>
      <a href="/about/">About</a>
    </nav>
  </div>
</header>
<main class="wrap" id="main-content">
{crumbs_html}
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p>{name} &mdash; {esc(site['tagline'])}</p>
    <p class="disclosure">As an Amazon Associate we earn from qualifying purchases. Care information is general guidance, not a substitute for professional or veterinary advice. Always confirm pet toxicity with the ASPCA or your veterinarian.</p>
    <p class="copyright">&copy; {site['year']} {name}. <a href="/privacy/">Privacy</a> &middot; <a href="/accessibility/">Accessibility</a></p>
  </div>
</footer>

<button id="a11y-fab" class="a11y-fab" aria-expanded="false" aria-controls="a11y-panel" aria-label="Accessibility options" title="Accessibility options">&#9855;</button>
<div id="a11y-panel" class="a11y-panel" role="dialog" aria-label="Accessibility options" hidden>
  <h2>Accessibility</h2>
  <div class="a11y-row">
    <button class="a11y-opt" data-a11y="font-down" aria-label="Decrease text size">A&minus;</button>
    <button class="a11y-opt" data-a11y="font-up" aria-label="Increase text size">A+</button>
  </div>
  <div class="a11y-row">
    <button id="a11y-contrast-btn" class="a11y-opt" data-a11y="contrast" aria-pressed="false">High contrast</button>
  </div>
  <div class="a11y-row">
    <button id="a11y-links-btn" class="a11y-opt" data-a11y="links" aria-pressed="false">Highlight links</button>
  </div>
  <div class="a11y-row">
    <button id="a11y-readable-btn" class="a11y-opt" data-a11y="readable" aria-pressed="false">Readable font</button>
  </div>
  <button class="a11y-opt a11y-reset" data-a11y="reset">Reset</button>
  <a class="a11y-statement" href="/accessibility/">Accessibility statement</a>
</div>
<script src="/assets/a11y.js" defer></script>
</body>
</html>
"""


def difficulty_class(d):
    return "diff-" + slugify(d)


def render_plant_card(p):
    pets = "Pet-safe" if not p["toxic_to_pets"] else "Toxic to pets"
    pet_class = "ok" if not p["toxic_to_pets"] else "warn"
    return f"""<a class="card" href="/plants/{esc(p['slug'])}/">
  <h3>{esc(p['common_name'])}</h3>
  <p class="sci">{esc(p['scientific_name'])}</p>
  <p class="card-summary">{esc(p['summary'][:120])}&hellip;</p>
  <div class="badges">
    <span class="badge {difficulty_class(p['difficulty'])}">{esc(p['difficulty'])}</span>
    <span class="badge pet-{pet_class}">{pets}</span>
  </div>
</a>"""


def render_index(site, plants):
    cards = "\n".join(render_plant_card(p) for p in sorted(plants, key=lambda x: x["common_name"]))
    body = f"""
<section class="hero">
  <h1>Houseplant care, without the guesswork</h1>
  <p class="lede">{esc(site['description'])}</p>
  <input type="search" id="plant-search" class="search" placeholder="Search plants (e.g. monstera, snake plant)&hellip;" aria-label="Search plants">
</section>
{ad_slot(site)}
<section>
  <h2>All plants</h2>
  <div class="grid" id="plant-grid">
{cards}
  </div>
</section>
<script>
const q=document.getElementById('plant-search');
if(q){{q.addEventListener('input',()=>{{const v=q.value.toLowerCase();
document.querySelectorAll('#plant-grid .card').forEach(c=>{{
c.style.display=c.textContent.toLowerCase().includes(v)?'':'none';}});}});}}
</script>
"""
    jsonld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site["name"],
        "url": site["url"],
        "description": site["description"],
    }
    return base_page(
        site,
        title=f"{site['name']} — {site['tagline']}",
        description=site["description"],
        canonical_path="/",
        body=body,
        jsonld=jsonld,
    )


def render_plant(site, p):
    pets_line = (
        "Non-toxic and considered safe for cats and dogs."
        if not p["toxic_to_pets"]
        else "Toxic to cats and dogs."
    )
    pet_class = "ok" if not p["toxic_to_pets"] else "warn"

    care_rows = [
        ("Difficulty", p["difficulty"]),
        ("Light", p["light"]),
        ("Water", p["water"]),
        ("Humidity", p["humidity"]),
        ("Temperature", p["temperature"]),
        ("Soil", p["soil"]),
        ("Fertilizer", p["fertilizer"]),
        ("Growth", p["growth"]),
    ]
    rows_html = "\n".join(
        f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in care_rows
    )

    products_html = "\n".join(
        f'<li><a href="{esc(amazon_link(prod["name"], site))}" rel="nofollow sponsored" '
        f'target="_blank">{esc(prod["category"])}: {esc(prod["name"])}</a></li>'
        for prod in p.get("products", [])
    )

    problems_html = ""
    faq_entities = []
    for prob in p.get("common_problems", []):
        pslug = slugify(prob["problem"])
        question = f"Why is my {p['common_name']} {prob['problem']}?"
        answer = f"{prob['cause']} {prob['fix']}"
        problems_html += f"""
<div class="problem">
  <h3 id="{esc(pslug)}"><a href="/problems/{esc(p['slug'])}-{esc(pslug)}/">{esc(question)}</a></h3>
  <p><strong>Cause:</strong> {esc(prob['cause'])}</p>
  <p><strong>Fix:</strong> {esc(prob['fix'])}</p>
</div>"""
        faq_entities.append({
            "@type": "Question",
            "name": question,
            "acceptedAnswer": {"@type": "Answer", "text": answer},
        })

    aka = ", ".join(p.get("aka", []))
    aka_html = f'<p class="aka">Also known as: {esc(aka)}</p>' if aka else ""

    body = f"""
<article class="plant">
  <h1>{esc(p['common_name'])} Care Guide</h1>
  <p class="sci">{esc(p['scientific_name'])}</p>
  {aka_html}
  <p class="summary">{esc(p['summary'])}</p>

  <div class="callout pet-{pet_class}">
    <strong>Pet safety:</strong> {esc(pets_line)} {esc(p['toxicity_notes'])}
  </div>

  <h2>Care at a glance</h2>
  <table class="care-table">{rows_html}</table>

  {ad_slot(site)}

  <h2>How often to water a {esc(p['common_name'])}</h2>
  <p>In typical indoor conditions, water roughly every <strong>{esc(p['watering_days'])} days</strong>, but always check the soil first rather than watering on a fixed calendar. {esc(p['water'])}</p>

  <h2>Common problems &amp; fixes</h2>
  {problems_html}

  {ad_slot(site)}

  <h2>Recommended supplies</h2>
  <p>These are the tools that make {esc(p['common_name'])} care easier:</p>
  <ul class="products">{products_html}</ul>
</article>
"""
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"{p['common_name']} Care Guide",
        "description": p["summary"],
        "author": {"@type": "Organization", "name": site["name"]},
        "publisher": {"@type": "Organization", "name": site["name"]},
    }
    faq_jsonld = ""
    if faq_entities:
        faq_jsonld = json.dumps({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faq_entities,
        })

    page = base_page(
        site,
        title=f"{p['common_name']} Care Guide: Light, Water & Problems | {site['name']}",
        description=f"Complete {p['common_name']} ({p['scientific_name']}) care guide: watering schedule, light, humidity, pet safety, and fixes for common problems.",
        canonical_path=f"/plants/{p['slug']}/",
        body=body,
        jsonld=jsonld,
        breadcrumbs=[("Home", "/"), ("Plants", "/"), (p["common_name"], None)],
    )
    if faq_jsonld:
        page = page.replace("</head>", f'<script type="application/ld+json">{faq_jsonld}</script>\n</head>')
    return page


def render_problem(site, p, prob):
    pslug = slugify(prob["problem"])
    question = f"Why is my {p['common_name']} {prob['problem']}?"
    body = f"""
<article class="problem-page">
  <h1>{esc(question)}</h1>
  <p class="summary">If your {esc(p['common_name'])} has {esc(prob['problem'])}, here's what's likely going on and how to fix it.</p>

  <h2>The most likely cause</h2>
  <p>{esc(prob['cause'])}</p>

  <h2>How to fix it</h2>
  <p>{esc(prob['fix'])}</p>

  {ad_slot(site)}

  <h2>Prevention</h2>
  <p>Most {esc(p['common_name'])} problems come down to watering and light. Water roughly every {esc(p['watering_days'])} days but always check the soil first. Light needs: {esc(p['light'])}</p>

  <p><a href="/plants/{esc(p['slug'])}/">&rarr; See the full {esc(p['common_name'])} care guide</a></p>
</article>
"""
    jsonld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{
            "@type": "Question",
            "name": question,
            "acceptedAnswer": {"@type": "Answer", "text": f"{prob['cause']} {prob['fix']}"},
        }],
    }
    return base_page(
        site,
        title=f"{question} (Causes & Fixes) | {site['name']}",
        description=f"{question} {prob['cause']} {prob['fix']}"[:155],
        canonical_path=f"/problems/{p['slug']}-{pslug}/",
        body=body,
        jsonld=jsonld,
        breadcrumbs=[("Home", "/"), (p["common_name"], f"/plants/{p['slug']}/"), (prob["problem"].title(), None)],
    )


def render_toxic_index(site, plants):
    toxic = [p for p in plants if p["toxic_to_pets"]]
    safe = [p for p in plants if not p["toxic_to_pets"]]

    def li(p):
        return f'<li><a href="/plants/{esc(p["slug"])}/">{esc(p["common_name"])}</a> &mdash; {esc(p["toxicity_notes"])}</li>'

    body = f"""
<article>
  <h1>Houseplants and Pet Safety</h1>
  <p class="summary">Whether a plant is safe around cats and dogs is one of the most important things to check before buying. Below are the plants in our database grouped by pet safety. Always confirm with the <a href="https://www.aspca.org/pet-care/animal-poison-control/toxic-and-non-toxic-plants" rel="nofollow" target="_blank">ASPCA database</a> or your vet.</p>

  {ad_slot(site)}

  <h2>Pet-safe plants</h2>
  <ul class="safety-list ok">{''.join(li(p) for p in sorted(safe, key=lambda x: x['common_name']))}</ul>

  <h2>Plants toxic to cats &amp; dogs</h2>
  <ul class="safety-list warn">{''.join(li(p) for p in sorted(toxic, key=lambda x: x['common_name']))}</ul>
</article>
"""
    return base_page(
        site,
        title=f"Which Houseplants Are Toxic to Cats & Dogs? | {site['name']}",
        description="A clear list of common houseplants that are toxic or safe for cats and dogs, with symptoms to watch for.",
        canonical_path="/toxic-to-pets/",
        body=body,
        breadcrumbs=[("Home", "/"), ("Pet Safety", None)],
    )


def render_about(site):
    body = f"""
<article class="prose">
  <h1>About {esc(site['name'])}</h1>
  <p>{esc(site['name'])} is a free, no-nonsense houseplant care database. Every guide is written to answer the real questions plant owners search for: how often to water, how much light a plant needs, whether it's safe for pets, and how to fix the problems that actually come up.</p>
  <p>We keep guides practical and skimmable. No life stories before the watering schedule.</p>
  <h2>How we make money</h2>
  <p>{esc(site['name'])} is free to read. We earn a small commission when you buy recommended supplies through our links, at no extra cost to you. This keeps the lights on and the guides free.</p>
  <h2>A note on accuracy</h2>
  <p>Care advice is general guidance and conditions vary by home. Pet-toxicity notes are summarized for convenience &mdash; always confirm with the ASPCA or your veterinarian before bringing a plant into a home with animals.</p>
</article>
"""
    return base_page(
        site,
        title=f"About {site['name']}",
        description=f"About {site['name']}, a free houseplant care database.",
        canonical_path="/about/",
        body=body,
    )


def render_privacy(site):
    body = f"""
<article class="prose">
  <h1>Privacy Policy</h1>
  <p>{esc(site['name'])} respects your privacy. We may use cookies for analytics and advertising to understand traffic and keep the site free.</p>
  <h2>Advertising</h2>
  <p>Third-party vendors, including Google, may use cookies to serve ads based on your prior visits. You can opt out of personalized advertising via Google Ads Settings.</p>
  <h2>Affiliate links</h2>
  <p>As an Amazon Associate we earn from qualifying purchases. Outbound product links may be affiliate links.</p>
  <h2>Contact</h2>
  <p>Questions? Reach us through the site.</p>
</article>
"""
    return base_page(
        site,
        title=f"Privacy Policy | {site['name']}",
        description=f"Privacy policy for {site['name']}.",
        canonical_path="/privacy/",
        body=body,
    )


def render_accessibility(site):
    body = f"""
<article class="prose">
  <h1>Accessibility Statement</h1>
  <p>{esc(site['name'])} is committed to making its website accessible to people
  with disabilities, in the spirit of the Web Content Accessibility Guidelines
  (WCAG) 2.1 level AA and Israeli Standard IS 5568.</p>

  <h2>What we have done</h2>
  <ul>
    <li>Semantic HTML structure with proper headings and landmarks.</li>
    <li>A "skip to content" link for keyboard and screen-reader users.</li>
    <li>Keyboard-operable navigation and visible focus indicators.</li>
    <li>An on-site accessibility toolbar (the &#9855; button) offering larger
    text, high-contrast mode, link highlighting, and a more readable font.</li>
    <li>Descriptive link text and sufficient colour contrast.</li>
  </ul>

  <h2>Using the accessibility toolbar</h2>
  <p>Select the accessibility button (&#9855;) at the corner of any page to adjust
  text size, contrast, link visibility, and font. Your choices are remembered on
  your device.</p>

  <h2>Ongoing effort &amp; feedback</h2>
  <p>Accessibility is an ongoing process and some content may not yet be fully
  optimised. If you encounter any barrier, or need help with any part of the
  site, please contact us and we will do our best to assist and to fix the
  issue. Your feedback helps us improve.</p>

  <p><strong>Contact for accessibility:</strong> {esc(site.get('contact_email', 'use the contact details on this site'))}</p>
  <p class="aka">Last reviewed: {site['year']}.</p>
</article>
"""
    return base_page(
        site,
        title=f"Accessibility Statement | {site['name']}",
        description=f"Accessibility statement for {site['name']}, following WCAG 2.1 AA and Israeli Standard IS 5568.",
        canonical_path="/accessibility/",
        body=body,
    )


def write_page(path_parts, html_str):
    """path_parts e.g. ['plants','monstera'] -> public/plants/monstera/index.html"""
    if path_parts:
        d = OUT.joinpath(*path_parts)
    else:
        d = OUT
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html_str, encoding="utf-8")


def build_sitemap(site, urls):
    today = date.today().isoformat()
    items = "\n".join(
        f"  <url><loc>{esc(site['url'].rstrip('/'))}{u}</loc><lastmod>{today}</lastmod></url>"
        for u in urls
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{items}
</urlset>
"""
    (OUT / "sitemap.xml").write_text(xml, encoding="utf-8")


def build_cname(site):
    """GitHub Pages reads public/CNAME to apply the custom domain on each deploy."""
    host = urlparse(site["url"]).netloc
    if host and "example" not in host:
        (OUT / "CNAME").write_text(host + "\n", encoding="utf-8")


def build_robots(site):
    txt = f"""User-agent: *
Allow: /

Sitemap: {site['url'].rstrip('/')}/sitemap.xml
"""
    (OUT / "robots.txt").write_text(txt, encoding="utf-8")


def main():
    site = load_json("site.json")
    plants = load_json("plants.json")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # copy assets
    if ASSETS_SRC.exists():
        shutil.copytree(ASSETS_SRC, OUT / "assets")

    urls = ["/", "/toxic-to-pets/", "/about/", "/privacy/", "/accessibility/"]

    write_page([], render_index(site, plants))
    write_page(["toxic-to-pets"], render_toxic_index(site, plants))
    write_page(["about"], render_about(site))
    write_page(["privacy"], render_privacy(site))
    write_page(["accessibility"], render_accessibility(site))

    for p in plants:
        write_page(["plants", p["slug"]], render_plant(site, p))
        urls.append(f"/plants/{p['slug']}/")
        for prob in p.get("common_problems", []):
            pslug = slugify(prob["problem"])
            write_page(["problems", f"{p['slug']}-{pslug}"], render_problem(site, p, prob))
            urls.append(f"/problems/{p['slug']}-{pslug}/")

    build_sitemap(site, urls)
    build_robots(site)
    build_cname(site)

    print(f"Built {len(urls)} pages from {len(plants)} plants -> {OUT}")
    print(f"  Plant guides: {len(plants)}")
    print(f"  Problem pages: {sum(len(p.get('common_problems', [])) for p in plants)}")


if __name__ == "__main__":
    main()
