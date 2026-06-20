# Plantwick — an automated houseplant care website

A self-growing, SEO-optimized content site that earns through Amazon affiliate
links and display ads. It is built to run with **near-zero ongoing effort**:
a scheduled job publishes new pages on its own and redeploys the site for free.

- **Cost to run:** ~$10/year (a domain). Hosting, HTTPS, and automation are free.
- **What it does on its own:** every few days it publishes new plant guides from
  a backlog, rebuilds the whole site, and redeploys — no computer required.
- **Your job:** a one-time ~30-minute setup, then occasionally top up the backlog
  and collect affiliate/ad earnings.

---

## How it works (the moving parts)

```
data/plants.json    -> the live plants shown on the site
data/backlog.json   -> pre-written plants waiting to be published (the "inventory")
build.py            -> turns the data into a full static website in ./public
grow.py             -> moves plants from backlog -> live, then rebuilds
.github/workflows/  -> runs grow.py on a schedule and deploys to GitHub Pages
```

Each scheduled run promotes 2 plants from the backlog to the live site and
redeploys. That steady trickle of fresh content is what search engines reward.

Current inventory: run `python grow.py --status` to see how many plant guides
are live and how many are queued.

---

## One-time setup (do this once, ~30 min)

### 1. Put the code on GitHub (free)
1. Create a free account at https://github.com if you don't have one.
2. Create a new **public** repository (public repos get free GitHub Pages).
3. From this folder, push the code:
   ```bash
   git init
   git add .
   git commit -m "Initial Plantwick site"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<repo>.git
   git push -u origin main
   ```

### 2. Turn on free hosting (GitHub Pages)
1. In your repo on GitHub: **Settings -> Pages**.
2. Under **Build and deployment -> Source**, choose **GitHub Actions**.
3. That's it. The included workflow (`.github/workflows/deploy.yml`) builds and
   deploys automatically on every push and on the schedule. Your site goes live
   at `https://<your-username>.github.io/<repo>/` within a couple of minutes.

> If the first Actions run fails to push the auto-commit, go to
> **Settings -> Actions -> General -> Workflow permissions** and select
> **Read and write permissions**.

### 3. Point a domain at it (optional but recommended, ~$10/yr)
A custom domain (e.g. `leaflore.com`) looks more trustworthy and is required by
most ad networks.
1. Buy a domain (Namecheap, Cloudflare Registrar, Porkbun are cheap).
2. In your repo: **Settings -> Pages -> Custom domain**, enter your domain.
3. At your registrar, add the DNS records GitHub shows you (A records / CNAME).
4. Update `data/site.json` -> `"url"` to your real domain, commit, and push.

### 4. Monetize — Amazon Associates (affiliate links)
1. Apply at https://affiliate-program.amazon.com (free).
2. Once approved, copy your tracking ID (looks like `yourname-20`).
3. Put it in `data/site.json` -> `"amazon_associate_tag"`, commit, and push.
   Every product link on the site instantly carries your tag.

> Amazon requires **3 qualifying sales within 180 days** to stay approved, so
> apply once you have a little traffic. All product links already work — they
> just need your tag swapped in.

### 5. Monetize — display ads (when you have traffic)
- **Easiest early option:** Google AdSense (https://adsense.com). Once approved,
  put your client id in `data/site.json` -> `"adsense_client"` (e.g.
  `ca-pub-XXXXXXXXXXXX`). Ad slots are already placed throughout the site.
- **Better rates later:** apply to **Ezoic** or **Mediavine** once you have
  steady traffic (Mediavine needs ~50k sessions/mo). They pay far more than
  AdSense.

### 6. (Optional) Analytics
Add a Google Analytics 4 measurement id to `data/site.json` -> `"analytics_id"`
to track visitors.

---

## Keeping it growing (the only recurring task)

The site auto-publishes until the backlog runs dry. To extend the runway, add
more plant entries to `data/backlog.json` (copy the format of an existing entry),
commit, and push. That's the single lever that keeps content flowing.

There are thousands of houseplants, so this can run for years. When you want a
fresh batch written, just ask.

### Manual commands (optional)
```bash
python build.py            # rebuild the site locally into ./public
python grow.py --status    # see live vs. backlog counts
python grow.py --count 2   # publish 2 plants now and rebuild
```

### Preview locally
```bash
python -m http.server 8099 --directory public
# then open http://localhost:8099
```

---

## Realistic expectations

SEO is a slow burn. Expect months 1-3 to be near-zero traffic while Google
indexes and trusts the site, then a gradual climb as long-tail pages start
ranking. The content compounds: every page keeps earning for years. This is a
consistency play, not a get-rich-quick scheme.

To speed it up: keep the backlog topped up (more pages = more search surface),
get a custom domain early, and once approved, make sure your Amazon tag and ad
codes are in `site.json`.
