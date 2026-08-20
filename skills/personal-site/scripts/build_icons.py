#!/usr/bin/env python3
"""Generate the home-screen / favicon set and the web manifest.

Draws a monogram over the dispersed-beam rule, using the same display font as
the page so the icon and the page headline share a letterform.

Backgrounds are opaque on purpose: iOS composites any alpha against black and
applies its own rounded mask, so a transparent icon comes out looking broken.
"""
import io, json, os, sys, urllib.request

FONT_URLS = {
    "Bricolage Grotesque":
        "https://raw.githubusercontent.com/google/fonts/main/ofl/bricolagegrotesque/"
        "BricolageGrotesque%5Bopsz%2Cwdth%2Cwght%5D.ttf",
}
FONT_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "personal-site-skill")

DEFAULT_BG = (16, 23, 26)
DEFAULT_FG = (242, 245, 243)
DEFAULT_BEAM = [[0.00, "#6D4AFF"], [0.34, "#0B9E8A"], [0.56, "#7FBF3A"],
                [0.78, "#F2A73B"], [1.00, "#E1503C"]]


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _stops(cfg):
    raw = ((cfg.get("icon") or {}).get("beam")) or DEFAULT_BEAM
    return [(float(p), _hex(c) if isinstance(c, str) else tuple(c)) for p, c in raw]


def _beam_colour(stops, t):
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if p0 <= t <= p1:
            f = 0 if p1 == p0 else (t - p0) / (p1 - p0)
            return tuple(round(c0[j] + (c1[j] - c0[j]) * f) for j in range(3))
    return stops[-1][1]


def _font_file(family):
    """Return a local TTF path, downloading a known family once if needed."""
    override = os.environ.get("MONOGRAM_TTF")
    if override and os.path.exists(override):
        return override
    url = FONT_URLS.get(family)
    if not url:
        return None
    os.makedirs(FONT_CACHE, exist_ok=True)
    path = os.path.join(FONT_CACHE, family.replace(" ", "_") + ".ttf")
    if not os.path.exists(path):
        print("    fetching %s ..." % family)
        try:
            urllib.request.urlretrieve(url, path)
        except Exception as e:
            print("    could not fetch font (%s); falling back to a system face" % e)
            return None
    return path


def _load_font(ImageFont, path, px):
    if path:
        f = ImageFont.truetype(path, px)
        try:
            # Bricolage's axis order is opsz, wght, wdth -- NOT the order the
            # family name suggests. Getting it wrong silently yields ExtraLight.
            axes = [a["maximum"] for a in f.get_variation_axes()]
            f.set_variation_by_axes(axes)
        except Exception:
            pass
        return f
    for cand in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(cand):
            return ImageFont.truetype(cand, px)
    return ImageFont.load_default()


def _render(cfg, size, font_path, scale=4):
    from PIL import Image, ImageDraw, ImageFont
    ic = cfg.get("icon") or {}
    bg = _hex(ic["bg"]) if ic.get("bg") else DEFAULT_BG
    fg = _hex(ic["fg"]) if ic.get("fg") else DEFAULT_FG
    stops = _stops(cfg)
    text = ic.get("monogram") or "".join(w[0] for w in cfg["name"].split()[:2]).upper()

    S = size * scale
    img = Image.new("RGB", (S, S), bg)
    d = ImageDraw.Draw(img)

    font = _load_font(ImageFont, font_path, int(S * 0.40))
    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    tx = (S - tw) / 2 - box[0]
    ty = (S - th) / 2 - box[1] - S * 0.020
    d.text((tx, ty), text, font=font, fill=fg)

    bw, bh = int(S * 0.42), max(1, int(S * 0.035))
    bx, by = (S - bw) // 2, int(ty + th + S * 0.13)
    for i in range(bw):
        d.rectangle([bx + i, by, bx + i, by + bh], fill=_beam_colour(stops, i / (bw - 1)))
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw - 1, bh - 1], radius=bh / 2, fill=255)
    flat = Image.new("RGB", (bw, bh), bg)
    flat.paste(img.crop((bx, by, bx + bw, by + bh)), (0, 0), mask)
    img.paste(flat, (bx, by))

    return img.resize((size, size), Image.LANCZOS)


def generate(cfg, out_dir):
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("  icons        skipped (pip install pillow to enable)")
        return
    os.makedirs(out_dir, exist_ok=True)
    theme = cfg.get("theme") or {}
    font_path = _font_file(theme.get("font_display", "Bricolage Grotesque"))

    print("  icons")
    for name, size in [("apple-touch-icon.png", 180), ("icon-192.png", 192),
                       ("icon-512.png", 512), ("favicon-32.png", 32)]:
        p = os.path.join(out_dir, name)
        _render(cfg, size, font_path).save(p, "PNG", optimize=True)
        print("    %-22s %3dpx  %5d bytes" % (name, size, os.path.getsize(p)))

    ic = cfg.get("icon") or {}
    bg = ic.get("bg") or "#10171A"
    manifest = {
        "name": cfg["name"],
        "short_name": cfg.get("short_name") or cfg["name"],
        "description": cfg.get("description") or cfg.get("headline", ""),
        "start_url": cfg.get("start_url", "./#card"),
        "display": "standalone",
        "background_color": bg,
        "theme_color": bg,
        "icons": [
            {"src": "./icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "./icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "./icon-512.png", "sizes": "512x512", "type": "image/png",
             "purpose": "maskable"},
        ],
    }
    mp = os.path.join(out_dir, "site.webmanifest")
    io.open(mp, "w", encoding="utf-8").write(json.dumps(manifest, indent=2) + "\n")
    print("    %-22s %5d bytes" % ("site.webmanifest", os.path.getsize(mp)))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: build_icons.py config.json [out_dir]")
    cfg = json.load(io.open(sys.argv[1], encoding="utf-8"))
    generate(cfg, sys.argv[2] if len(sys.argv) > 2 else "./site/assets")
