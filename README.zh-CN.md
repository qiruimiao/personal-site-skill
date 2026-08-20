# personal-site

[English](README.md) · **简体中文**

把一份 CV 和几个链接，变成一个单页个人网站——带别人可以直接扫的二维码、用于线下社交的名片模式，以及能添加到手机桌面的图标。

可作为 [Claude Code](https://claude.com/claude-code) 和 [Codex](https://developers.openai.com/codex) 的 skill 使用，也可以脱离 agent 直接跑命令行。

**线上示例：** [qiruimiao.github.io](https://qiruimiao.github.io) · [名片模式](https://qiruimiao.github.io/#card)

## 你会得到什么

一个自包含的 HTML 文件，两种视图：

| 视图 | 网址 | 用途 |
|---|---|---|
| **完整履历** | `/` | 教育、经历、能力、可入职时间、CV 下载。招聘方看到的版本。 |
| **名片** | `/#card` | 姓名、一行副标题、一个大二维码。正好一屏，举起手机就能让人扫。 |

外加一套桌面图标、web manifest，以及 Open Graph 标签——把链接发到微信、WhatsApp、LinkedIn 时会正常显示标题和简介，而不是一条光秃秃的网址。

**二维码在构建时编码，以静态 SVG 路径的形式烧进页面。** 不调用任何二维码服务、没有运行时依赖、不会过期。把页面存到手机上，飞行模式下照样能扫。

## 快速开始

两种 agent 用法一致：把 CV 丢给它，说清楚要什么，它会读 CV、写配置、构建、部署。涉及隐私的内容发布前会先问你。

```
Build me a personal site from my CV at ~/Documents/CV.docx.
LinkedIn: <url>, GitHub: <url>. Deploy it to GitHub Pages.
```

### Claude Code

推荐用插件市场安装，方便以后更新：

```
/plugin marketplace add qiruimiao/personal-site-skill
/plugin install personal-site@personal-site-skill
```

或者直接复制：

```bash
git clone https://github.com/qiruimiao/personal-site-skill
cp -r personal-site-skill/skills/personal-site ~/.claude/skills/
```

### Codex

Codex 读取同一份 `SKILL.md`，skill 本身不需要任何改动，放到 Codex 会扫描的位置即可：

```bash
git clone https://github.com/qiruimiao/personal-site-skill
mkdir -p ~/.agents/skills
cp -r personal-site-skill/skills/personal-site ~/.agents/skills/
```

然后**在 Codex 界面里**（不是在终端 shell 里）输入 `$` 选择 `personal-site`，或输入 `/skills` 查看已识别的技能。Codex 会自动发现新技能，没出现就重启一下。

只想在某个项目里用、而不是装到整个用户环境，把它放进那个仓库的 `.agents/skills/personal-site` —— Codex 会从当前工作目录一路向上扫到仓库根目录。

### 不用 agent

构建全部由脚本完成，agent 只负责写配置。所以你完全可以自己写：

```bash
pip install segno pillow
cp skills/personal-site/config.example.json config.json
# 编辑 config.json
python3 skills/personal-site/scripts/build_site.py config.json --out ./site
python3 -m http.server -d ./site 8000
```

## 配置

一个 JSON 文件驱动全部内容。模板见 [`config.example.json`](skills/personal-site/config.example.json)，线上示例背后的真实配置见 [`examples/qirui.json`](examples/qirui.json)。

```json
{
  "name": "Ada Lovelace",
  "location": "London, United Kingdom",
  "card_subtitle": "Mathematician · Analytical Engine",
  "headline": "一句话说明你是做什么的。",
  "sections": [
    { "label": "Education", "rows": [
      { "meta": "MSc · 2026", "title": "University", "sub": "Subject",
        "note": "Dissertation: ..." }
    ]},
    { "label": "Capabilities", "list": ["能力一", "能力二"] }
  ],
  "availability": { "label": "Availability", "text": "Available from **January 1844**." },
  "cv": { "href": "assets/CV.pdf", "source": "./CV.pdf", "meta": "PDF · 2 pages" },
  "channels": [
    { "key": "linkedin", "url": "https://www.linkedin.com/in/example/", "handle": "in/example" }
  ]
}
```

**配置里写普通文本**——直接用真实字符 `·` `—` `–`，不要写 HTML 实体。转义和字符编码由构建器负责；写 `&middot;` 页面上会显示字面的 `&middot;`。

`sub`、`note`、`list` 和 `availability.text` 里支持两种标记：`**加粗**` 和 `[文字](https://网址)`。行还可以带 `link` 字段，让标题变成带外链箭头的链接。**只接受 `http(s)` 链接**，其余一律转义——所以配置无法注入标记或 `javascript:` 链接。

### 渠道（channels）

每个渠道对应一个标签页和一个二维码。内置图标覆盖 `whatsapp`、`linkedin`、`instagram`、`github`、`x`、`telegram`、`email`、`website`、`phone`、`calendar`、`vcard`；用其他 key 也能正常工作，只是显示通用链接图标。

`key: "vcard"` 比较特殊——它不读 `url`，而是用顶层 `vcard` 配置块生成一张联系人名片，别人扫码可以直接存进通讯录。

### 主题

```json
"theme": { "accent_light": "#0B6B5B", "accent_dark": "#54D3B6",
           "font_display": "Bricolage Grotesque", "font_mono": "IBM Plex Mono" },
"icon":  { "monogram": "AL", "bg": "#10171A", "fg": "#F2F5F3" }
```

字体来自 Google Fonts（严格 CSP 下唯一允许的字体源）。图标上的字母组合默认取你姓名的首字母。

## 关于什么该公开

个人网站会被爬虫抓取。这几点 skill 会主动提醒你，但值得提前知道：

- **CV 的 PDF 和网页一样公开。** 爬虫会读 PDF。CV 上如果有手机号，挂上去就等于公开了号码。建议单独准备一份不含号码的公开版，正式投递时再发原版。
- **照片是地区惯例问题。** 英国、美国、爱尔兰、澳洲的 CV 不放照片（不少雇主做匿名化筛选）；德国、法国、中国则通常要放。
- **WhatsApp 用 `wa.me/qr/…` 邀请链接**，而不是 `wa.me/<手机号>`——后者会把号码写进页面源码。注意邀请链接可以在 WhatsApp 里重置，一旦重置，已经印出去的二维码就失效了。

## 验证方式

这里的两道检查都来自真实踩过的坑：

- **扫不出内容的二维码。** 每个码都会从自己生成的路径数据反解回来，与源字符串比对，不一致就中止构建。一个"看起来没问题、扫出来是空"的二维码，是最该大声失败的场景。
- **手机上按 980px 渲染再缩小的页面。** 没有 viewport meta 标签时，移动浏览器会按桌面宽度排版然后整体缩放。**用 iframe 测不出这个问题**——iframe 直接拿到指定宽度，根本不经过 viewport meta。所以 skill 明确要求 agent 用真实设备模拟，并检查页面报告的 CSS 视口宽度。

## 环境要求

- Python 3.8+
- [`segno`](https://pypi.org/project/segno/) —— 二维码编码
- [`pillow`](https://pypi.org/project/pillow/) —— 生成图标；可选，缺失时会跳过图标继续构建
- [`gh`](https://cli.github.com) —— 部署到 GitHub Pages

## 许可

MIT
