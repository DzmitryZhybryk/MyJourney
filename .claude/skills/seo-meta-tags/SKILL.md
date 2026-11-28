---
name: seo-meta-tags
description: Audits the <head> of any HTML file in this project and adds missing SEO meta tags — title, meta description, the full Open Graph set, and Twitter Card — with semantically meaningful values, never just placeholders. Use this proactively whenever creating a new .html file, editing the <head> of an existing one, or reading an HTML file whose head is missing production-grade SEO defaults.
---

Project-local skill. Triggers proactively — the user does not want to think about SEO; the skill must generate real on-brand values, not TODO placeholders.

## When to apply

Trigger on any of:

1. A new `.html` file is created (e.g. `frontend/index.html`, future landing/marketing).
2. The `<head>` of an existing `.html` is edited — even unrelated to SEO. Audit the head as a side action.
3. An HTML file is read and one of the 7 tags below is missing — fix it in the same reply, even if the user didn't ask.

Skip:

- `.tsx`/`.jsx` — per-route SEO is handled at runtime there (React Helmet, etc.), not in static head.
- `dist/`, `build/`, `node_modules/`, `.next/` — build artifacts.
- Templates/fragments (`_partial.html`, `head-fragment.html`, `partials/*`, `includes/*`).

## Required tags (7)

Add only the missing ones. Do not duplicate or rewrite existing tags without an explicit request.

| Tag | Purpose |
|---|---|
| `<title>` | Browser tab + primary search title |
| `<meta name="description">` | Search snippet, ≤ 160 chars |
| `<meta property="og:type">` | `website` for landing/auth/home, `article` for blog posts |
| `<meta property="og:title">` | Share title |
| `<meta property="og:description">` | Share description |
| `<meta property="og:image">` | Preview image, 1200×630 |
| `<meta name="twitter:card">` | Twitter card style |

**Do NOT add:**
- `<meta name="keywords">` — Google has ignored it since 2009.
- `<link rel="canonical">` — requires a production URL; guessing is worse than omitting.
- `<meta name="robots">` — the default "index, follow" is already correct.

## Brand context

- **User-facing brand:** `MyJourney`.
- **Product:** travel tracking + self-reflection, unified by a globe-with-aura on the home page.
- **Tone:** quiet, atmospheric, observational. Avoid hype: "revolutionary", "best-in-class", "unleash", "supercharge". Verbs: *track*, *log*, *reflect*, *mark*, *watch*. Address the user as "you/your".
- **Audience:** travelers who keep records of their trips and reflect on them.

## Per-tag rules

**`<title>`** — pattern `{Page-specific phrase} — MyJourney`. ≤ 60 chars (longer titles get truncated by Google).
- Landing/SPA shell: product-level, e.g. `MyJourney — track your travels, reflect on your trips`.
- Auth: `Sign in — MyJourney`, `Create your account — MyJourney`.

**`<meta name="description">`** — 120–160 chars. Describe what the user *does* on the page. No keyword stuffing or puffery.
- Landing: `MyJourney is a quiet companion for travelers — mark countries you've visited, log trips, and reflect on how each journey felt, all in one place.` (152 chars)

**`<meta property="og:title">`** — usually the same as `<title>` but **without** the trailing ` — MyJourney` (OG renders the site name separately). If the title is already a short product-level string, leave it as is.

**`<meta property="og:description">`** — may match meta description verbatim, or be a tighter version.

**`<meta property="og:type">`** — default `website`. Use `article` only for blog posts/essays (`posts/*.html`, `<article>` as main, or an explicit request).

**`<meta property="og:image">`** — path `/og-image.png`. Before writing, check `frontend/public/og-image.{png,jpg}`. If it's missing, still write `/og-image.png` and **at the end of the reply** say: *"Drop a 1200×630 image at `frontend/public/og-image.png` so social shares render with a preview."*

**`<meta name="twitter:card">`** — always `summary_large_image`.

## Order in `<head>`

After `<meta charset>` and `<meta viewport>`, before `<link>`/`<script>`:

```html
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <title>...</title>
  <meta name="description" content="..." />

  <meta property="og:type" content="website" />
  <meta property="og:title" content="..." />
  <meta property="og:description" content="..." />
  <meta property="og:image" content="/og-image.png" />

  <meta name="twitter:card" content="summary_large_image" />

  <!-- existing link/script tags -->
</head>
```

If the file structure differs, insert the new tags next to related ones — don't restructure.

## Edge cases

- **Don't touch existing tags.** The skill *adds* missing ones, it doesn't refactor copy.
- **All 7 already present:** do nothing. In the reply: "head already has full SEO defaults — no changes."
- **SPA shell** (`frontend/index.html`): meta is a fallback for crawlers and FCP. Set product-level defaults; don't try to be page-specific (per-route overrides happen via runtime libraries).

## Reporting

After the edit, a 3–4 line reply:
1. Which file was edited.
2. Which tags were added (just the names).
3. A TODO line if og:image points to a missing file.
