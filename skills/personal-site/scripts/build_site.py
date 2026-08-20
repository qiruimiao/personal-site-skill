#!/usr/bin/env python3
"""Build a one-page personal site from a JSON config.

    pip install segno pillow
    python3 scripts/build_site.py config.json --out ./site

Produces a complete, self-contained `index.html` plus a home-screen icon set.
Every QR code is encoded at build time and baked in as a static SVG path, so the
published page never calls an external QR service and works offline.

The build fails loudly rather than shipping something subtly broken: each QR is
decoded back from its own path data and compared against the source string.
"""
import argparse, base64, io, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from channel_icons import icon  # noqa: E402

try:
    import segno
except ImportError:
    sys.exit("segno is required:  pip install segno")

ASSETS = os.path.join(os.path.dirname(HERE), "assets")

THEME_DEFAULTS = {
    "accent_light": "#0B6B5B", "accent_light_hover": "#085548", "accent_soft_light": "#DCEBE6",
    "accent_dark": "#54D3B6", "accent_dark_hover": "#82E5CD", "accent_soft_dark": "#11322C",
    "font_display": "Bricolage Grotesque", "font_mono": "IBM Plex Mono",
}


# --------------------------------------------------------------------------- QR

def qr_path(text, border=3):
    """Encode `text`; return (module count, SVG path data) as run-length rects."""
    qr = segno.make(text, error="m")
    rows = list(qr.matrix_iter(border=border))
    n = len(rows)
    parts = []
    for y, row in enumerate(rows):
        x = 0
        while x < n:
            if row[x]:
                run = 0
                while x + run < n and row[x + run]:
                    run += 1
                parts.append("M%d %dh%dv1h-%dz" % (x, y, run, run))
                x += run
            else:
                x += 1
    return n, "".join(parts)


def verify_qr(n, d, expected, border=3):
    """Expand the path back to a matrix and compare with segno's own output."""
    grid = [[0] * n for _ in range(n)]
    consumed = 0
    for m in re.finditer(r"M(\d+) (\d+)h(\d+)v1h-(\d+)z", d):
        x, y, run, back = map(int, m.groups())
        if run != back:
            return False
        consumed += m.end() - m.start()
        for i in range(run):
            grid[y][x + i] = 1
    if consumed != len(d):
        return False
    ref = [list(r) for r in segno.make(expected, error="m").matrix_iter(border=border)]
    return grid == ref


def vcard(cfg):
    """Build a vCard 3.0 string from the config's `vcard` block."""
    v = cfg.get("vcard") or {}
    name = v.get("name") or cfg["name"]
    parts = name.split()
    last, first = (parts[-1], " ".join(parts[:-1])) if len(parts) > 1 else (name, "")
    lines = ["BEGIN:VCARD", "VERSION:3.0",
             "N:%s;%s;;;" % (last, first), "FN:%s" % name]
    if v.get("email"):
        lines.append("EMAIL;TYPE=INTERNET:%s" % v["email"])
    if v.get("phone"):
        lines.append("TEL;TYPE=CELL:%s" % v["phone"])
    if v.get("url"):
        lines.append("URL:%s" % v["url"])
    if v.get("city") or v.get("country"):
        lines.append("ADR;TYPE=HOME:;;;%s;;;%s" % (v.get("city", ""), v.get("country", "")))
    if v.get("title"):
        lines.append("TITLE:%s" % v["title"])
    lines += ["END:VCARD", ""]
    return "\r\n".join(lines)


# ----------------------------------------------------------------------- markup

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def entify(s):
    """Escape non-ASCII to numeric entities so the page is charset-proof."""
    return "".join(c if ord(c) < 128 else "&#%d;" % ord(c) for c in s)


_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def inline_md(s):
    """Markup allowed in prose fields: **bold** and [text](https://url).

    Everything is HTML-escaped first, so the only markup that survives is what
    this function puts back. Only http(s) links are recognised - no javascript:
    or data: URLs can be smuggled in through a config.
    """
    out = esc(s)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = _LINK_RE.sub(
        lambda m: '<a href="%s" target="_blank" rel="noopener">%s</a>' % (m.group(2), m.group(1)),
        out)
    return out


bold_md = inline_md  # kept for readability at call sites


def build_channels(cfg):
    tabs, panels, report = [], [], []
    channels = cfg.get("channels") or []
    if not channels:
        sys.exit("config error: at least one entry in `channels` is required")

    for i, ch in enumerate(channels):
        key = ch.get("key") or "link"
        if not re.fullmatch(r"[a-z0-9_-]+", key):
            sys.exit("config error: channel key %r must be lowercase a-z0-9_-" % key)
        label = ch.get("label") or key.title()

        payload = vcard(cfg) if key == "vcard" else ch.get("url")
        if not payload:
            sys.exit("config error: channel %r needs a `url` (or use key 'vcard')" % key)

        n, d = qr_path(payload)
        if not verify_qr(n, d, payload):
            sys.exit("internal error: QR for %r did not round-trip" % key)
        report.append((key, n, payload))

        on = " is-on" if i == 0 else ""
        tabs.append(
            '<button class="tab%s" type="button" role="tab" id="tab-%s" '
            'aria-controls="panel-qr" aria-selected="%s" data-key="%s" onclick="pick(\'%s\')">'
            "%s<span>%s</span></button>"
            % (on, key, "true" if i == 0 else "false", key, key, icon(key), esc(label)))

        href = ch.get("link") or ("mailto:" + cfg["vcard"]["email"]
                                  if key == "vcard" and cfg.get("vcard", {}).get("email")
                                  else payload)
        external = "" if href.startswith("mailto:") else ' target="_blank" rel="noopener"'
        cta = ch.get("cta") or ("Open " + label)
        caption = ch.get("caption") or ("Scan to open my " + label)
        handle = ch.get("handle") or re.sub(r"^https?://(www\.)?", "", payload).rstrip("/")
        if key == "vcard":
            handle = ch.get("handle") or cfg.get("vcard", {}).get("email", "")

        panels.append(
            '<div class="qrpanel%s" data-key="%s"%s>'
            '<div class="plate"><svg viewBox="0 0 %d %d" shape-rendering="crispEdges" '
            'role="img" aria-label="QR code &mdash; %s"><path d="%s" fill="#0D1214"/></svg></div>'
            '<div class="qrmeta"><p class="cap">%s</p><p class="sub mono">%s</p></div>'
            '<a class="cta" href="%s"%s>%s <span aria-hidden="true">&rarr;</span></a></div>'
            % (on, key, "" if i == 0 else " hidden", n, n, esc(label), d,
               esc(caption), esc(handle), esc(href), external, esc(cta)))

    return "\n        ".join(tabs), "\n        ".join(panels), report


def build_sections(cfg):
    out = []
    for sec in cfg.get("sections") or []:
        label = esc(sec.get("label", ""))
        if sec.get("list"):
            items = "".join("<li>%s</li>" % bold_md(x) for x in sec["list"])
            body = '<ul class="caps">%s</ul>' % items
        else:
            rows = []
            for r in sec.get("rows") or []:
                bits = ['<p class="meta mono">%s</p>' % esc(r["meta"])] if r.get("meta") else []
                title = esc(r.get("title", ""))
                if r.get("link"):
                    if not r["link"].startswith(("http://", "https://")):
                        sys.exit("config error: row link must be http(s): %r" % r["link"])
                    title = ('<a href="%s" target="_blank" rel="noopener">%s'
                             '<span class="ext" aria-hidden="true">&#8599;</span></a>'
                             % (esc(r["link"]), title))
                bits.append("<h3>%s</h3>" % title)
                if r.get("sub"):
                    bits.append('<p class="sub">%s</p>' % bold_md(r["sub"]))
                if r.get("note"):
                    bits.append('<p class="diss">%s</p>' % bold_md(r["note"]))
                rows.append('<article class="row">%s</article>' % "".join(bits))
            body = '<div class="rows">%s</div>' % "".join(rows)
        out.append('<section class="block"><h2 class="mono">%s</h2>%s</section>' % (label, body))
    return "\n      ".join(out)


def cv_button(cfg, extra_class=""):
    cv = cfg.get("cv")
    if not cv:
        return ""
    return (
        '<a class="cv%s" href="%s" target="_blank" rel="noopener">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M13 2.5H7a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8.5z"/>'
        '<path d="M13 2.5V8.5h6"/><path d="M12 12v5.2m0 0 2.1-2.1M12 17.2 9.9 15.1"/></svg>'
        '<span class="cvtext"><b>%s</b><span class="mono">%s</span></span></a>'
        % (extra_class, esc(cv["href"]), esc(cv.get("label", "Download CV")),
           esc(cv.get("meta", "PDF"))))


def portrait_tag(cfg, out_dir):
    src = cfg.get("portrait")
    if not src:
        return ""
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp"}.get(src.rsplit(".", 1)[-1].lower())
    if not mime:
        sys.exit("config error: portrait must be .jpg, .png or .webp")
    b64 = base64.b64encode(open(src, "rb").read()).decode("ascii")
    return ('<img class="portrait" src="data:%s;base64,%s" alt="%s" width="92" height="92">'
            % (mime, b64, esc(cfg["name"])))


# ------------------------------------------------------------------------ build

def validate(cfg, config_path):
    """Check everything the build depends on before writing any output.

    Failing here beats failing halfway through with a traceback and a
    half-written site directory.
    """
    where = os.path.dirname(os.path.abspath(config_path)) or "."

    for required in ("name", "channels"):
        if not cfg.get(required):
            sys.exit("config error: %r is required" % required)

    def resolve(path):
        return path if os.path.isabs(path) else os.path.join(where, path)

    cv = cfg.get("cv")
    if cv:
        if not cv.get("href"):
            sys.exit("config error: `cv.href` is required when `cv` is present "
                     "(the public path, e.g. \"assets/CV.pdf\")")
        src = cv.get("source")
        if src:
            full = resolve(src)
            if not os.path.exists(full):
                sys.exit(
                    "config error: CV file not found: %s\n"
                    "  `cv.source` must point at a real file, relative to the config.\n"
                    "  Point it at your own CV, or delete the whole \"cv\" block to\n"
                    "  build without a download button." % full)
            cv["source"] = full

    portrait = cfg.get("portrait")
    if portrait:
        full = resolve(portrait)
        if not os.path.exists(full):
            sys.exit("config error: portrait not found: %s\n"
                     "  Point `portrait` at a real image, or remove the field." % full)
        cfg["portrait"] = full


def build(cfg, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    theme = dict(THEME_DEFAULTS, **(cfg.get("theme") or {}))

    css = io.open(os.path.join(ASSETS, "style.css"), encoding="utf-8").read()
    for k, v in theme.items():
        css = css.replace("{{%s}}" % k.upper(), v)
    left = re.findall(r"\{\{[A-Z_]+\}\}", css)
    if left:
        sys.exit("internal error: unresolved style placeholders %s" % sorted(set(left)))

    tabs, panels, report = build_channels(cfg)

    fonts = "&".join("family=" + t["font"].replace(" ", "+") + t["axes"] for t in [
        {"font": theme["font_display"], "axes": ":opsz,wght@12..96,400;12..96,500;12..96,700"},
        {"font": theme["font_mono"], "axes": ":wght@400;500"}])

    body = """<div class="wrap">
<div class="modebar" role="group" aria-label="View mode">
  <button type="button" class="mode" id="btn-card" onclick="setMode('card')">Card</button>
  <button type="button" class="mode" id="btn-profile" onclick="setMode('profile')">Full profile</button>
</div>

<div class="card">
  <header class="id">
      {portrait}
      <p class="place mono">{location}</p>
      <h1>{name}</h1>
      <div class="beam" aria-hidden="true"></div>
      <p class="cardline">{card_subtitle}</p>
      <p class="headline">{headline}</p>
  </header>

  <div class="main">
      {sections}
      {availability}
  </div>

  <div class="side">
    <div class="tabs" role="tablist" aria-label="Choose what to scan or open">
        {tabs}
    </div>
    <div id="panel-qr" role="tabpanel">
        {panels}
    </div>
    {cv_card}
  </div>
</div>
</div>""".format(
        portrait=portrait_tag(cfg, out_dir),
        location=esc(cfg.get("location", "")),
        name=esc(cfg["name"]).replace(" ", "&nbsp;", 1) if cfg.get("nbsp_name", True) else esc(cfg["name"]),
        card_subtitle=esc(cfg.get("card_subtitle", "")),
        headline=esc(cfg.get("headline", "")),
        sections=build_sections(cfg),
        availability=('<section class="block"><h2 class="mono">%s</h2>'
                      '<p class="availline">%s</p>%s</section>'
                      % (esc(cfg["availability"].get("label", "Availability")),
                         bold_md(cfg["availability"]["text"]), cv_button(cfg))
                      ) if cfg.get("availability") else cv_button(cfg),
        tabs=tabs, panels=panels, cv_card=cv_button(cfg, " cv-card"))

    script = io.open(os.path.join(ASSETS, "page.js"), encoding="utf-8").read()

    head = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}</title>
<meta name="description" content="{description}">
<meta name="theme-color" content="#EFF2F0" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0B0F11" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="profile">
<meta property="og:title" content="{name}">
<meta property="og:description" content="{description}">
{og_url}
<meta name="twitter:card" content="summary">
<link rel="icon" type="image/png" sizes="32x32" href="assets/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon.png">
<link rel="manifest" href="assets/site.webmanifest">
<meta name="apple-mobile-web-app-title" content="{short_name}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{fonts}&display=swap">
<style>
{css}
</style>
</head>
<body>
""".format(lang=cfg.get("lang", "en"), name=esc(cfg["name"]),
           description=esc(cfg.get("description") or cfg.get("headline", "")),
           og_url=('<meta property="og:url" content="%s">' % esc(cfg["site_url"])
                   if cfg.get("site_url") else ""),
           short_name=esc(cfg.get("short_name") or cfg["name"]), fonts=fonts, css=css)

    html = entify(head + body + "\n\n<script>\n" + script + "\n</script>\n</body>\n</html>\n")
    path = os.path.join(out_dir, "index.html")
    io.open(path, "w", encoding="utf-8").write(html)

    print("  QR codes")
    for key, n, payload in report:
        preview = payload.split("\r\n")[0] if "\r\n" in payload else payload
        print("    %-12s %3d modules  verified  %s" % (key, n, preview[:52]))
    print("  index.html   %d bytes" % len(html))
    return path


def copy_cv(cfg, out_dir):
    cv = cfg.get("cv")
    if not cv or not cv.get("source"):
        return
    dest_dir = os.path.join(out_dir, "assets")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(cv["href"]))
    if os.path.abspath(cv["source"]) != os.path.abspath(dest):
        shutil.copyfile(cv["source"], dest)
        print("  CV           copied to %s" % os.path.relpath(dest, out_dir))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config")
    ap.add_argument("--out", default="./site", help="output directory (default: ./site)")
    ap.add_argument("--skip-icons", action="store_true")
    args = ap.parse_args()

    try:
        cfg = json.load(io.open(args.config, encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit("config error: %s is not valid JSON - %s" % (args.config, e))
    validate(cfg, args.config)

    print("Building %s" % cfg["name"])
    build(cfg, args.out)
    copy_cv(cfg, args.out)

    if not args.skip_icons:
        import build_icons
        build_icons.generate(cfg, os.path.join(args.out, "assets"))

    print("\nDone. Serve it with:  python3 -m http.server -d %s 8000" % args.out)


if __name__ == "__main__":
    main()
