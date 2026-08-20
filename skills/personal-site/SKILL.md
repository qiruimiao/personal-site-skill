---
name: personal-site
description: Turn a CV and a few social links into a one-page personal site with scannable QR codes, a business-card view for networking, and a home-screen icon set — then deploy it free on GitHub Pages. Use when someone wants a personal website, an online business card, a portfolio landing page, a QR contact card, or wants to put their CV online.
---

# Personal site from a CV

Builds a single self-contained HTML page with two views:

- **Full profile** — education, experience, capabilities, availability, CV download. The default; what a recruiter sees.
- **Card** — name, one-line subtitle, one big QR code. Reached at `#card`, sized to fit a phone screen so it can be held up at a networking event.

Every QR code is encoded at build time and baked in as a static SVG path. The page calls no QR service, works offline, and can be added to a phone home screen as an app-like icon.

## Before you start

Ask for whatever you don't have. Do not invent facts about a person — if the CV does not say it, ask rather than guess.

1. **Their CV** — `.docx`, `.pdf`, or plain text. This supplies the profile content.
2. **The links they want scannable** — LinkedIn, WhatsApp, Instagram, GitHub, a website, whatever. See *Channels*.
3. **Where it should live** — a GitHub Pages repo is the default; ask for their GitHub username.

## Privacy: raise this before publishing, not after

A personal site is public and gets crawled. Two things routinely leak and are hard to undo:

- **Phone numbers.** Most CVs carry one. Putting the CV PDF online publishes it just as surely as putting it in the HTML — crawlers read PDFs. Ask whether they want a phone-free public version of the CV. If yes, produce a separate public copy and leave their real CV untouched; never edit the original in place.
- **Home address.** Should never appear. UK/US CV convention is city and country only.

Also check the CV for **notes to self** that leaked into the text — tailoring reminders, bracketed TODOs, placeholder markers. These are common in CVs assembled by tooling and read badly to an employer. Point out anything you find; do not silently keep it.

Two more judgement calls worth naming:

- **Photos.** UK, US, Irish and Australian CV convention is to omit one; several employers anonymise applications. Germany, France and China expect one. Say which convention applies and let the person decide. The `portrait` field supports it either way.
- **WhatsApp.** Prefer the invite link (`wa.me/qr/…`, from WhatsApp → Settings → the QR icon → share). A `wa.me/<number>` link puts the phone number in the page source. Note that an invite link can be reset inside WhatsApp, which invalidates the printed QR.

## Build it

```bash
pip install segno pillow
python3 scripts/build_site.py config.json --out ./site
```

Write `config.json` from the CV. Start from `config.example.json`; `examples/qirui.json` in the repo root is a complete real one.

**Write plain text in the config — real characters like `·` `—` `–`, not HTML entities.** The builder escapes and encodes for you; typing `&middot;` yields a literal `&middot;` on the page.

Two bits of markup are interpreted in `sub`, `note`, `list` and `availability.text`: `**bold**` and `[text](https://url)`. A row may also carry `link`, which makes its title a link with an outbound arrow — good for a project row. Only `http(s)` URLs are accepted; anything else aborts the build rather than emitting it.

Key fields:

| Field | Notes |
|---|---|
| `name` | Required. Also the page title and the monogram source. |
| `location`, `card_subtitle`, `headline` | Eyebrow, card-view subtitle, one-line positioning. |
| `sections[]` | Ordered. Each has a `label` plus either `rows` (meta/title/sub/note) or `list` (bullets). |
| `availability` | `label` and `text`. Omit if not job-hunting. |
| `cv` | `href` is the public path; `source` is the local file to copy in. Omit for no download button. |
| `channels[]` | Required, at least one. First is the default tab. |
| `portrait` | Optional local image path, embedded as a data URI. |
| `theme`, `icon` | Optional accent colours, fonts, monogram, icon colours. |
| `site_url` | Enables the `og:url` tag for link previews. |

### Channels

Each entry needs a `key` (selects the icon), a `label`, and a `url` to encode. Icons ship for `whatsapp`, `linkedin`, `instagram`, `github`, `x`, `telegram`, `email`, `website`, `phone`, `calendar`, `vcard`; anything else gets a generic link glyph and still works.

`key: "vcard"` is special — instead of a `url` it encodes a contact card from the top-level `vcard` block (`name`, `email`, `phone`, `url`, `city`, `country`, `title`), so scanning saves the person straight to a phone's contacts.

Optional per channel: `caption` (text under the QR), `handle` (the small line under that), `cta` (button label), `link` (if the button should go somewhere other than the encoded URL).

### What the build checks

Each QR is decoded back from its own path data and compared against the source string. A mismatch aborts the build — a QR that looks fine and scans to nothing is the failure mode worth being loud about.

## Deploy to GitHub Pages

For the clean `https://<username>.github.io` root URL, the repo **must** be named exactly `<username>.github.io`. Confirm the username with `gh api user --jq .login` rather than assuming.

```bash
gh auth login --web --git-protocol https     # the person runs this themselves
cp -r site/* <repo>/ && cd <repo>
git init -b main && git add -A && git commit -m "Personal site"
gh repo create <username>.github.io --public --source=. --remote=origin --push
```

Pages auto-enables for a `<username>.github.io` repo. Poll `gh api repos/<owner>/<repo>/pages/builds/latest --jq .status` until it reads `built`, then actually fetch the live URL and confirm it serves — do not report success from a successful push alone.

Free GitHub Pages requires a **public** repo. Say so before creating it.

## Verify before declaring done

- `curl -sS -I <url>` returns 200, and the assets (`assets/site.webmanifest`, the icons, the CV) do too.
- **Test mobile with real device emulation, not an iframe.** An iframe gets its width directly and never exercises the viewport meta tag, so it cannot catch the single most common failure here: a page laid out at ~980px and shrunk on a phone. Check that the CSS viewport reports the device width.
- Re-decode a QR from the *live* page, not just the local build.

## Home screen

Adding `<site>/#card` to a phone home screen gives an app-like launcher: tap the icon, the QR is on screen. iOS uses `apple-touch-icon.png`; Android uses `site.webmanifest`, whose `start_url` defaults to `./#card`.

The icon draws a monogram over a spectral rule using the page's own display font, downloaded once and cached in `~/.cache/personal-site-skill`. Set `icon.monogram`, `icon.bg`, `icon.fg` and `icon.beam` to change it. If the font cannot be fetched the build falls back to a system face rather than failing.

## Updating later

Edit `config.json` and re-run the build; never hand-edit the generated `index.html`. When a WhatsApp invite link is reset or a CV is revised, that is a config change plus a rebuild.
