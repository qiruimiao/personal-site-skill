# personal-site

Turn a CV and a few links into a one-page personal site — with QR codes people can scan off your screen, a business-card view for networking, and an icon you can add to your phone's home screen.

Works as a skill in [Claude Code](https://claude.com/claude-code) and [Codex](https://developers.openai.com/codex), or standalone from the command line.

**Live example:** [qiruimiao.github.io](https://qiruimiao.github.io) · [card view](https://qiruimiao.github.io/#card)

## What you get

One self-contained HTML file with two views:

| View | URL | For |
|---|---|---|
| **Full profile** | `/` | Education, experience, capabilities, availability, CV download. What a recruiter sees. |
| **Card** | `/#card` | Name, subtitle, one big QR code. Fits a phone screen — hold it up and someone scans it. |

Plus a home-screen icon set, a web manifest, and Open Graph tags so the link previews properly when you send it.

**The QR codes are encoded at build time and baked into the page as static SVG paths.** No QR service, no runtime dependency, no expiring links. Save the page to your phone and it still scans with the wifi off.

## Quick start

The skill works the same in either agent: point it at your CV, say what you want, and it reads the CV, writes the config, builds and deploys. It asks before publishing anything sensitive.

```
Build me a personal site from my CV at ~/Documents/CV.docx.
LinkedIn: <url>, GitHub: <url>. Deploy it to GitHub Pages.
```

### Claude Code

Install as a plugin marketplace — recommended, since it stays updatable:

```
/plugin marketplace add qiruimiao/personal-site-skill
/plugin install personal-site@personal-site-skill
```

Or copy it in:

```bash
git clone https://github.com/qiruimiao/personal-site-skill
cp -r personal-site-skill/skills/personal-site ~/.claude/skills/
```

### Codex

Codex reads the same `SKILL.md`, so the skill needs no changes — just put it somewhere Codex looks:

```bash
git clone https://github.com/qiruimiao/personal-site-skill
mkdir -p ~/.agents/skills
cp -r personal-site-skill/skills/personal-site ~/.agents/skills/
```

Then type `$` in Codex and pick `personal-site`, or `/skills` to list what it found. Codex picks up new skills automatically; restart it if one does not show up.

To scope it to a single project instead of installing it for your whole user, drop it at `.agents/skills/personal-site` inside that repo — Codex scans from your working directory up to the repository root.

### Standalone

No agent required; the scripts do the building, the agent only writes the config.

```bash
pip install segno pillow
cp skills/personal-site/config.example.json config.json
# edit config.json
python3 skills/personal-site/scripts/build_site.py config.json --out ./site
python3 -m http.server -d ./site 8000
```

## Configuration

One JSON file drives everything. See [`config.example.json`](skills/personal-site/config.example.json) for a template and [`examples/qirui.json`](examples/qirui.json) for the config behind the live example.

```json
{
  "name": "Ada Lovelace",
  "location": "London, United Kingdom",
  "card_subtitle": "Mathematician · Analytical Engine",
  "headline": "One line on what you do.",
  "sections": [
    { "label": "Education", "rows": [
      { "meta": "MSc · 2026", "title": "University", "sub": "Subject",
        "note": "Dissertation: ..." }
    ]},
    { "label": "Capabilities", "list": ["Thing one", "Thing two"] }
  ],
  "availability": { "label": "Availability", "text": "Available from **January 1844**." },
  "cv": { "href": "assets/CV.pdf", "source": "./CV.pdf", "meta": "PDF · 2 pages" },
  "channels": [
    { "key": "linkedin", "url": "https://www.linkedin.com/in/example/", "handle": "in/example" }
  ]
}
```

Write **plain text** — real `·` `—` `–` characters, not HTML entities. The builder escapes and encodes for you.

Two bits of markup are interpreted in `sub`, `note`, `list` and `availability.text`: `**bold**` and `[text](https://url)`. A row can also take a `link` field, which turns its title into a link. Only `http(s)` URLs are accepted — everything else is escaped, so a config cannot inject markup or a `javascript:` URL.

### Channels

Each channel becomes a tab with its own QR code. Icons ship for `whatsapp`, `linkedin`, `instagram`, `github`, `x`, `telegram`, `email`, `website`, `phone`, `calendar` and `vcard`; any other key still works with a generic link icon.

`key: "vcard"` encodes a contact card built from the top-level `vcard` block, so scanning saves you straight into someone's contacts.

### Theme

```json
"theme": { "accent_light": "#0B6B5B", "accent_dark": "#54D3B6",
           "font_display": "Bricolage Grotesque", "font_mono": "IBM Plex Mono" },
"icon":  { "monogram": "AL", "bg": "#10171A", "fg": "#F2F5F3" }
```

Fonts come from Google Fonts, the one host a strict CSP allows. The icon monogram defaults to your initials.

## A note on what goes public

A personal site gets crawled. The skill will raise these, but they are worth knowing up front:

- **Your CV PDF is as public as the page.** Crawlers read PDFs. If your CV carries a phone number, publishing it publishes the number. Keep a phone-free public copy and send the real one when you apply.
- **Photos are a regional convention.** UK, US, Irish and Australian CVs omit them; German, French and Chinese ones expect them.
- **A WhatsApp `wa.me/qr/…` invite link** keeps your number out of the page source, unlike `wa.me/<number>`. It can be reset from inside WhatsApp, which invalidates any QR you already printed.

## How it's verified

Two failure modes drove the checks here, both found the hard way:

- **A QR that scans to nothing.** Every code is decoded back from its own generated path data and compared against the source string. A mismatch aborts the build.
- **A page that renders at 980px on a phone.** Without a viewport meta tag, mobile browsers lay out at desktop width and shrink. Testing in an iframe cannot catch this — an iframe gets its width directly and never exercises the tag. The skill tells the agent to use real device emulation and check the reported CSS viewport width.

## Requirements

- Python 3.8+
- [`segno`](https://pypi.org/project/segno/) for QR encoding
- [`pillow`](https://pypi.org/project/pillow/) for icons — optional; the build skips icons without it
- [`gh`](https://cli.github.com) to deploy to GitHub Pages

## Licence

MIT
