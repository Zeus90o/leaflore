#!/usr/bin/env python3
"""Plantwick static site generator (multilingual).

Reads data/site.json, data/plants.json and data/i18n/* and renders a complete
static website into ./public, one subtree per language. Pure standard library.

UI strings come from data/i18n/ui.json. Per-language plant content comes from
data/i18n/plants.<lang>.json; anything missing falls back to English, so pages
never break while translations are filled in.

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
I18N = DATA / "i18n"
OUT = ROOT / "public"
ASSETS_SRC = ROOT / "assets"

# Globals populated in main()
SITE = {}
UI = {}
TRANS = {}        # {lang: {slug: {fields...}}}
LANGS = []        # list of {code,name,dir}
DEFAULT = "en"
EN = {}           # English UI dict (fallback)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def esc(text):
    return html.escape(str(text), quote=True)


def t(lang, key, **kw):
    """Translate a UI key with English fallback. Formats only if kwargs given."""
    val = UI.get(lang, {}).get(key)
    if val is None:
        val = EN.get(key, key)
    if kw:
        try:
            val = val.format(**kw)
        except (KeyError, IndexError):
            pass
    return val


def lang_dir(lang):
    for L in LANGS:
        if L["code"] == lang:
            return L.get("dir", "ltr")
    return "ltr"


def localize(path, lang):
    """Map a language-agnostic path to its localized URL."""
    if lang == DEFAULT:
        return path
    if path == "/":
        return f"/{lang}/"
    return f"/{lang}{path}"


def amazon_link(query):
    tag = SITE.get("amazon_associate_tag", "")
    domain = SITE.get("amazon_domain", "www.amazon.com")
    return f"https://{domain}/s?k={quote_plus(query)}&tag={tag}"


def get_plant(plant, lang):
    """Return a plant dict with localized display values (English fallback)."""
    if lang == DEFAULT:
        base = dict(plant)
        base["_problems"] = [
            {"problem": p["problem"], "cause": p["cause"], "fix": p["fix"], "en": p["problem"]}
            for p in plant.get("common_problems", [])
        ]
        return base

    tr = TRANS.get(lang, {}).get(plant["slug"], {})
    base = dict(plant)
    for f in ("common_name", "summary", "light", "water", "humidity",
              "temperature", "soil", "fertilizer", "growth", "toxicity_notes"):
        base[f] = tr.get(f, plant[f])
    base["aka"] = tr.get("aka", plant.get("aka", []))
    ptr = tr.get("problems", {})
    base["_problems"] = []
    for p in plant.get("common_problems", []):
        x = ptr.get(p["problem"], {})
        base["_problems"].append({
            "problem": x.get("problem", p["problem"]),
            "cause": x.get("cause", p["cause"]),
            "fix": x.get("fix", p["fix"]),
            "en": p["problem"],
        })
    return base


# ---------------------------------------------------------------- ad / head bits

def ad_slot(label="Advertisement"):
    client = SITE.get("adsense_client", "")
    if client:
        return (
            f'<div class="ad"><span class="ad-label">{esc(label)}</span>'
            f'<ins class="adsbygoogle" style="display:block" '
            f'data-ad-client="{esc(client)}" data-ad-format="auto" '
            f'data-full-width-responsive="true"></ins>'
            f'<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script></div>'
        )
    return f'<div class="ad ad--placeholder"><span class="ad-label">{esc(label)}</span></div>'


def analytics():
    aid = SITE.get("analytics_id", "")
    if not aid:
        return ""
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={esc(aid)}"></script>'
        f'<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}'
        f'gtag("js",new Date());gtag("config","{esc(aid)}");</script>'
    )


def adsense_head():
    client = SITE.get("adsense_client", "")
    if not client:
        return ""
    return (
        f'<script async src="https://pagead2.googlesyndication.com/pagead/js/'
        f'adsbygoogle.js?client={esc(client)}" crossorigin="anonymous"></script>'
    )


def hreflang_links(logical_path):
    url = SITE["url"].rstrip("/")
    out = []
    for L in LANGS:
        href = url + localize(logical_path, L["code"])
        out.append(f'<link rel="alternate" hreflang="{esc(L["code"])}" href="{esc(href)}">')
    out.append(f'<link rel="alternate" hreflang="x-default" href="{esc(url + localize(logical_path, DEFAULT))}">')
    return "\n".join(out)


def lang_switcher(lang, logical_path):
    items = []
    for L in LANGS:
        href = localize(logical_path, L["code"])
        cur = ' aria-current="true"' if L["code"] == lang else ""
        items.append(f'<a href="{esc(href)}"{cur} lang="{esc(L["code"])}">{esc(L["name"])}</a>')
    return (f'<div class="lang-switch" aria-label="{esc(t(lang, "lang_label"))}">'
            + "".join(items) + "</div>")


def base_page(lang, *, title, description, logical_path, body, jsonld=None,
              breadcrumbs=None, extra_head=""):
    url = SITE["url"].rstrip("/")
    canonical = url + localize(logical_path, lang)
    name = esc(SITE["name"])
    direction = lang_dir(lang)

    crumbs_html = ""
    if breadcrumbs:
        items = []
        for label, href in breadcrumbs:
            if href:
                items.append(f'<a href="{esc(localize(href, lang))}">{esc(label)}</a>')
            else:
                items.append(f"<span>{esc(label)}</span>")
        crumbs_html = '<nav class="crumbs" aria-label="Breadcrumb">' + " / ".join(items) + "</nav>"

    jsonld_html = ""
    if jsonld:
        jsonld_html = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>'

    return f"""<!DOCTYPE html>
<html lang="{esc(lang)}" dir="{esc(direction)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
{hreflang_links(logical_path)}
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:site_name" content="{name}">
<meta property="og:locale" content="{esc(lang)}">
<meta name="twitter:card" content="summary">
<link rel="stylesheet" href="/assets/style.css">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
{adsense_head()}
{analytics()}
{extra_head}
{jsonld_html}
</head>
<body>
<a class="skip-link" href="#main-content">{esc(t(lang, 'skip'))}</a>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="{esc(localize('/', lang))}"><span class="leaf">&#127807;</span> {name}</a>
    <nav class="main-nav">
      <a href="{esc(localize('/', lang))}">{esc(t(lang, 'nav_plants'))}</a>
      <a href="{esc(localize('/toxic-to-pets/', lang))}">{esc(t(lang, 'nav_pet_safety'))}</a>
      <a href="{esc(localize('/about/', lang))}">{esc(t(lang, 'nav_about'))}</a>
      {lang_switcher(lang, logical_path)}
    </nav>
  </div>
</header>
<main class="wrap" id="main-content">
{crumbs_html}
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p>{name} &mdash; {esc(t(lang, 'tagline'))}</p>
    <p class="disclosure">{esc(t(lang, 'footer_disclosure'))}</p>
    <p class="copyright">&copy; {SITE['year']} {name}. <a href="{esc(localize('/privacy/', lang))}">{esc(t(lang, 'footer_privacy'))}</a> &middot; <a href="{esc(localize('/accessibility/', lang))}">{esc(t(lang, 'footer_accessibility'))}</a></p>
  </div>
</footer>

<button id="a11y-fab" class="a11y-fab" aria-expanded="false" aria-controls="a11y-panel" aria-label="{esc(t(lang, 'a11y_btn'))}" title="{esc(t(lang, 'a11y_btn'))}">&#9855;</button>
<div id="a11y-panel" class="a11y-panel" role="dialog" aria-label="{esc(t(lang, 'a11y_btn'))}" hidden>
  <h2>{esc(t(lang, 'a11y_heading'))}</h2>
  <div class="a11y-row">
    <button class="a11y-opt" data-a11y="font-down" aria-label="{esc(t(lang, 'a11y_decrease'))}">A&minus;</button>
    <button class="a11y-opt" data-a11y="font-up" aria-label="{esc(t(lang, 'a11y_increase'))}">A+</button>
  </div>
  <div class="a11y-row"><button id="a11y-contrast-btn" class="a11y-opt" data-a11y="contrast" aria-pressed="false">{esc(t(lang, 'a11y_contrast'))}</button></div>
  <div class="a11y-row"><button id="a11y-links-btn" class="a11y-opt" data-a11y="links" aria-pressed="false">{esc(t(lang, 'a11y_links'))}</button></div>
  <div class="a11y-row"><button id="a11y-readable-btn" class="a11y-opt" data-a11y="readable" aria-pressed="false">{esc(t(lang, 'a11y_readable'))}</button></div>
  <button class="a11y-opt a11y-reset" data-a11y="reset">{esc(t(lang, 'a11y_reset'))}</button>
  <a class="a11y-statement" href="{esc(localize('/accessibility/', lang))}">{esc(t(lang, 'a11y_statement'))}</a>
</div>
<script src="/assets/a11y.js" defer></script>
</body>
</html>
"""


def difficulty_class(d):
    return "diff-" + slugify(d)


# ---------------------------------------------------------------------- renders

def render_plant_card(lang, p):
    pets = t(lang, "pet_safe") if not p["toxic_to_pets"] else t(lang, "pet_toxic")
    pet_class = "ok" if not p["toxic_to_pets"] else "warn"
    diff_label = t(lang, "diff_" + p["difficulty"])
    return f"""<a class="card" href="{esc(localize('/plants/' + p['slug'] + '/', lang))}">
  <h3>{esc(p['common_name'])}</h3>
  <p class="sci">{esc(p['scientific_name'])}</p>
  <p class="card-summary">{esc(p['summary'][:120])}&hellip;</p>
  <div class="badges">
    <span class="badge {difficulty_class(p['difficulty'])}">{esc(diff_label)}</span>
    <span class="badge pet-{pet_class}">{esc(pets)}</span>
  </div>
</a>"""


def render_index(lang, plants):
    locp = [get_plant(p, lang) for p in plants]
    cards = "\n".join(render_plant_card(lang, p) for p in sorted(locp, key=lambda x: x["common_name"]))
    body = f"""
<section class="hero">
  <h1>{esc(t(lang, 'home_h1'))}</h1>
  <p class="lede">{esc(t(lang, 'home_lede'))}</p>
  <input type="search" id="plant-search" class="search" placeholder="{esc(t(lang, 'search_placeholder'))}" aria-label="{esc(t(lang, 'search_label'))}">
</section>
{ad_slot()}
<section>
  <h2>{esc(t(lang, 'all_plants'))}</h2>
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
        "name": SITE["name"],
        "url": SITE["url"],
        "inLanguage": lang,
    }
    return base_page(
        lang,
        title=f"{SITE['name']} — {t(lang, 'tagline')}",
        description=t(lang, "home_lede"),
        logical_path="/",
        body=body,
        jsonld=jsonld,
    )


def render_plant(lang, p):
    name = p["common_name"]
    pets_line = t(lang, "pets_safe_line") if not p["toxic_to_pets"] else t(lang, "pets_toxic_line")
    pet_class = "ok" if not p["toxic_to_pets"] else "warn"
    diff_label = t(lang, "diff_" + p["difficulty"])

    care_rows = [
        ("row_difficulty", diff_label),
        ("row_light", p["light"]),
        ("row_water", p["water"]),
        ("row_humidity", p["humidity"]),
        ("row_temperature", p["temperature"]),
        ("row_soil", p["soil"]),
        ("row_fertilizer", p["fertilizer"]),
        ("row_growth", p["growth"]),
    ]
    rows_html = "\n".join(
        f"<tr><th>{esc(t(lang, k))}</th><td>{esc(v)}</td></tr>" for k, v in care_rows
    )

    products_html = "\n".join(
        f'<li><a href="{esc(amazon_link(prod["name"]))}" rel="nofollow sponsored" '
        f'target="_blank">{esc(prod["category"])}: {esc(prod["name"])}</a></li>'
        for prod in p.get("products", [])
    )

    problems_html = ""
    faq_entities = []
    for prob in p["_problems"]:
        pslug = slugify(prob["en"])
        question = t(lang, "why_is_my", name=name, problem=prob["problem"])
        answer = f"{prob['cause']} {prob['fix']}"
        problems_html += f"""
<div class="problem">
  <h3 id="{esc(pslug)}"><a href="{esc(localize('/problems/' + p['slug'] + '-' + pslug + '/', lang))}">{esc(question)}</a></h3>
  <p><strong>{esc(t(lang, 'cause_label'))}</strong> {esc(prob['cause'])}</p>
  <p><strong>{esc(t(lang, 'fix_label'))}</strong> {esc(prob['fix'])}</p>
</div>"""
        faq_entities.append({
            "@type": "Question",
            "name": question,
            "acceptedAnswer": {"@type": "Answer", "text": answer},
        })

    aka = ", ".join(p.get("aka", []))
    aka_html = f'<p class="aka">{esc(t(lang, "aka_label"))} {esc(aka)}</p>' if aka else ""

    body = f"""
<article class="plant">
  <h1>{esc(t(lang, 'care_guide_h1', name=name))}</h1>
  <p class="sci">{esc(p['scientific_name'])}</p>
  {aka_html}
  <p class="summary">{esc(p['summary'])}</p>

  <div class="callout pet-{pet_class}">
    <strong>{esc(t(lang, 'pet_safety_label'))}</strong> {esc(pets_line)} {esc(p['toxicity_notes'])}
  </div>

  <h2>{esc(t(lang, 'care_glance'))}</h2>
  <table class="care-table">{rows_html}</table>

  {ad_slot()}

  <h2>{esc(t(lang, 'watering_h2', name=name))}</h2>
  <p>{esc(t(lang, 'watering_para', days=p['watering_days']))} {esc(p['water'])}</p>

  <h2>{esc(t(lang, 'problems_h2'))}</h2>
  {problems_html}

  {ad_slot()}

  <h2>{esc(t(lang, 'supplies_h2'))}</h2>
  <p>{esc(t(lang, 'supplies_intro', name=name))}</p>
  <ul class="products">{products_html}</ul>
</article>
"""
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": t(lang, "care_guide_h1", name=name),
        "description": p["summary"],
        "inLanguage": lang,
        "author": {"@type": "Organization", "name": SITE["name"]},
        "publisher": {"@type": "Organization", "name": SITE["name"]},
    }
    extra = ""
    if faq_entities:
        faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_entities}
        extra = f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script>'

    return base_page(
        lang,
        title=f"{t(lang, 'care_guide_title', name=name)} | {SITE['name']}",
        description=t(lang, "care_guide_desc", name=name),
        logical_path=f"/plants/{p['slug']}/",
        body=body,
        jsonld=jsonld,
        breadcrumbs=[(t(lang, "bc_home"), "/"), (t(lang, "bc_plants"), "/"), (name, None)],
        extra_head=extra,
    )


def render_problem(lang, p, prob):
    name = p["common_name"]
    pslug = slugify(prob["en"])
    question = t(lang, "why_is_my", name=name, problem=prob["problem"])
    body = f"""
<article class="problem-page">
  <h1>{esc(question)}</h1>
  <p class="summary">{esc(t(lang, 'problem_summary', name=name, problem=prob['problem']))}</p>

  <h2>{esc(t(lang, 'cause_h2'))}</h2>
  <p>{esc(prob['cause'])}</p>

  <h2>{esc(t(lang, 'fix_h2'))}</h2>
  <p>{esc(prob['fix'])}</p>

  {ad_slot()}

  <h2>{esc(t(lang, 'prevention_h2'))}</h2>
  <p>{esc(t(lang, 'prevention_para', name=name, days=p['watering_days']))} {esc(p['light'])}</p>

  <p><a href="{esc(localize('/plants/' + p['slug'] + '/', lang))}">{esc(t(lang, 'see_full', name=name))}</a></p>
</article>
"""
    jsonld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": lang,
        "mainEntity": [{
            "@type": "Question",
            "name": question,
            "acceptedAnswer": {"@type": "Answer", "text": f"{prob['cause']} {prob['fix']}"},
        }],
    }
    return base_page(
        lang,
        title=f"{question} | {SITE['name']}",
        description=f"{question} {prob['cause']} {prob['fix']}"[:155],
        logical_path=f"/problems/{p['slug']}-{pslug}/",
        body=body,
        jsonld=jsonld,
        breadcrumbs=[(t(lang, "bc_home"), "/"), (name, f"/plants/{p['slug']}/"), (prob["problem"], None)],
    )


def render_toxic_index(lang, plants):
    locp = [get_plant(p, lang) for p in plants]
    toxic = [p for p in locp if p["toxic_to_pets"]]
    safe = [p for p in locp if not p["toxic_to_pets"]]

    def li(p):
        return (f'<li><a href="{esc(localize("/plants/" + p["slug"] + "/", lang))}">{esc(p["common_name"])}</a>'
                f' &mdash; {esc(p["toxicity_notes"])}</li>')

    intro = (t(lang, "petsafety_intro_before")
             + f'<a href="https://www.aspca.org/pet-care/animal-poison-control/toxic-and-non-toxic-plants" rel="nofollow" target="_blank">{esc(t(lang, "petsafety_aspca"))}</a>'
             + t(lang, "petsafety_intro_after"))

    body = f"""
<article>
  <h1>{esc(t(lang, 'petsafety_h1'))}</h1>
  <p class="summary">{intro}</p>

  {ad_slot()}

  <h2>{esc(t(lang, 'petsafety_safe_h2'))}</h2>
  <ul class="safety-list ok">{''.join(li(p) for p in sorted(safe, key=lambda x: x['common_name']))}</ul>

  <h2>{esc(t(lang, 'petsafety_toxic_h2'))}</h2>
  <ul class="safety-list warn">{''.join(li(p) for p in sorted(toxic, key=lambda x: x['common_name']))}</ul>
</article>
"""
    return base_page(
        lang,
        title=f"{t(lang, 'petsafety_title')} | {SITE['name']}",
        description=t(lang, "petsafety_title"),
        logical_path="/toxic-to-pets/",
        body=body,
        breadcrumbs=[(t(lang, "bc_home"), "/"), (t(lang, "bc_pet_safety"), None)],
    )


def render_prose(lang, key_html, key_title, path):
    body = f'<article class="prose">{t(lang, key_html, site=SITE["name"])}</article>'
    return base_page(
        lang,
        title=f"{t(lang, key_title)} | {SITE['name']}",
        description=f"{t(lang, key_title)} — {SITE['name']}",
        logical_path=path,
        body=body,
    )


# ----------------------------------------------------------------------- output

def write_page(lang, path_parts, html_str):
    parts = [] if lang == DEFAULT else [lang]
    parts += path_parts
    d = OUT.joinpath(*parts) if parts else OUT
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html_str, encoding="utf-8")


def build_sitemap(urls):
    today = date.today().isoformat()
    base = SITE["url"].rstrip("/")
    items = "\n".join(
        f"  <url><loc>{esc(base)}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{items}
</urlset>
"""
    (OUT / "sitemap.xml").write_text(xml, encoding="utf-8")


def build_robots():
    txt = f"""User-agent: *
Allow: /

Sitemap: {SITE['url'].rstrip('/')}/sitemap.xml
"""
    (OUT / "robots.txt").write_text(txt, encoding="utf-8")


def build_cname():
    host = urlparse(SITE["url"]).netloc
    if host and "example" not in host:
        (OUT / "CNAME").write_text(host + "\n", encoding="utf-8")


def main():
    global SITE, UI, TRANS, LANGS, DEFAULT, EN
    SITE = load_json(DATA / "site.json")
    plants = load_json(DATA / "plants.json")
    UI = load_json(I18N / "ui.json")
    LANGS = SITE["languages"]
    DEFAULT = SITE.get("default_lang", "en")
    EN = UI.get(DEFAULT, {})

    TRANS = {}
    for L in LANGS:
        code = L["code"]
        if code == DEFAULT:
            continue
        f = I18N / f"plants.{code}.json"
        TRANS[code] = load_json(f) if f.exists() else {}

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    if ASSETS_SRC.exists():
        shutil.copytree(ASSETS_SRC, OUT / "assets")

    urls = []
    for L in LANGS:
        lang = L["code"]
        write_page(lang, [], render_index(lang, plants))
        write_page(lang, ["toxic-to-pets"], render_toxic_index(lang, plants))
        write_page(lang, ["about"], render_prose(lang, "about_html", "about_title", "/about/"))
        write_page(lang, ["privacy"], render_prose(lang, "privacy_html", "privacy_title", "/privacy/"))
        write_page(lang, ["accessibility"], render_prose(lang, "accessibility_html", "accessibility_title", "/accessibility/"))
        for base in ("/", "/toxic-to-pets/", "/about/", "/privacy/", "/accessibility/"):
            urls.append(localize(base, lang))

        for p in plants:
            lp = get_plant(p, lang)
            write_page(lang, ["plants", p["slug"]], render_plant(lang, lp))
            urls.append(localize(f"/plants/{p['slug']}/", lang))
            for prob in lp["_problems"]:
                pslug = slugify(prob["en"])
                write_page(lang, ["problems", f"{p['slug']}-{pslug}"], render_problem(lang, lp, prob))
                urls.append(localize(f"/problems/{p['slug']}-{pslug}/", lang))

    build_sitemap(urls)
    build_robots()
    build_cname()

    print(f"Built {len(urls)} pages across {len(LANGS)} languages from {len(plants)} plants -> {OUT}")
    for L in LANGS:
        translated = len(TRANS.get(L["code"], {})) if L["code"] != DEFAULT else len(plants)
        print(f"  {L['code']}: {translated}/{len(plants)} plants translated")


if __name__ == "__main__":
    main()
