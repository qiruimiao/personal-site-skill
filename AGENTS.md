# personal-site-skill

A skill that turns a CV and a set of links into a deployable one-page personal site. The skill itself lives in `skills/personal-site/`; this file is for working **on** the repo.

## Layout

| Path | What it is |
|---|---|
| `skills/personal-site/SKILL.md` | The instructions an agent reads. Read by both Claude Code and Codex. |
| `skills/personal-site/scripts/build_site.py` | Config → complete `index.html`. The entry point. |
| `skills/personal-site/scripts/build_icons.py` | Home-screen icons and web manifest. |
| `skills/personal-site/scripts/channel_icons.py` | Inline SVG per channel, with a generic fallback. |
| `skills/personal-site/assets/style.css` | Stylesheet with `{{TOKEN}}` placeholders substituted at build time. |
| `examples/qirui.json` | A real config, used as the regression fixture. |

## Build and check

```bash
pip install segno pillow
python3 skills/personal-site/scripts/build_site.py examples/qirui.json --out /tmp/site
```

The build fails loudly on bad input rather than emitting something subtly broken. Keep it that way:

- every QR is decoded back from its own generated path data and compared against the source string
- config paths are resolved relative to the config file and checked before any output is written
- unresolved `{{TOKEN}}` placeholders in the stylesheet abort the build

## Invariants worth not breaking

- **Config content is data, not markup.** Everything is HTML-escaped; only `**bold**` and `[text](https://url)` survive, and only `http(s)` URLs are accepted. Do not add a raw-HTML passthrough.
- **The output is one self-contained file.** No runtime fetches except Google Fonts. QR codes and portraits are embedded, never linked to a service.
- **`index.html` is a complete document.** The `viewport` meta is load-bearing: without it mobile browsers lay out at ~980px and shrink the page.
- **Do not hand-edit generated output.** Change `style.css`, the scripts, or the config, then rebuild.

## Testing a change

An iframe is not a mobile test — it gets its width directly and never exercises the viewport meta. Use real device emulation and check the reported CSS viewport width.

The strongest regression check is that `examples/qirui.json` still reproduces <https://qiruimiao.github.io> exactly: compare QR path data, the stylesheet, and the visible text against the live page.
