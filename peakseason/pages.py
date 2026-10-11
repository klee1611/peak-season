"""Static pages for search engines and link previews, written after every export.

The app (site/index.html) renders in the browser from the visitor's location, so a crawler
sees almost nothing. These pages give every famous spot a stable URL per language with its
current status as plain HTML:

    /                 /ja/  /ko/  /zh-tw/        app homes (head tags rewritten in place)
    /spots/           /ja/spots/ ...             spot index per language
    /spots/<id>/      /ja/spots/<id>/ ...        one page per famous spot
    /sitemap.xml                                 every page above, with hreflang

Pages are generated from the exported JSON (site/data), never from model calls, so they always
match what the app shows. Nothing here knows about any particular plant: names and stage labels
come from targets.json.

    uv run python -m peakseason.pages        # regenerate from the current site/data
"""

import html
import json
import logging
import re
from pathlib import Path
from urllib.parse import quote

from peakseason import geo
from peakseason.config import Settings, get_settings
from peakseason.spots import Spot, load_spots

log = logging.getLogger("peakseason.pages")

LANGS = ("en", "ja", "ko", "zh-TW")
NEARBY_SPOTS = 4
NEARBY_MAX_KM = 1500  # "nearby" across an ocean is not useful

# Page text. The app's own strings live in site/app.js; these are only what static pages need.
# {window} is WINDOW_DAYS.
TEXT = {
    "en": {
        "home_title": "Peak Season: {plants} at their peak near you, right now",
        "home_desc": "See where {plants} are at their best near you this week, from recent photos "
        "checked by Gemma, an open-source AI model. Free, no sign-up, worldwide.",
        "spots_title": "Famous spots for {plants}: status now | Peak Season",
        "spots_h1": "Famous spots",
        "spots_intro": "Current status at well-known viewing spots, from photos taken in the "
        "last {window} days. Updated {date}.",
        "spot_title": "{spot}: {plants} now | Peak Season",
        "status": "{spot}: {plant} {stage} as of {date}, based on {count} photo reports from "
        "the last {window} days.",
        "thin": "{spot}: {plant} has been seen in the last {window} days, but there are not "
        "enough reports to judge the stage yet ({date}).",
        "none": "{spot}: no recent reports of {plant} as of {date}.",
        "reports": "{count} reports",
        "photo_by": "Photo",
        "originals": "Original posts",
        "directions": "Directions",
        "open_app": "Open the live map of places near here",
        "nearby": "Other famous spots nearby",
        "all_spots": "All famous spots",
        "updated": "Updated {date}",
        "about": "How it works",
        "home": "Peak Season",
        "km": "{km} km",
        "list_and": " and ",
    },
    "ja": {
        "home_title": "Peak Season｜近くの{plants}の見頃が今わかる",
        "home_desc": "直近の写真をオープンソースAIモデル Gemma が確認し、近くで今{plants}が"
        "見頃の場所を表示します。無料・登録不要・世界対応。",
        "spots_title": "{plants}の名所 見頃情報｜Peak Season",
        "spots_h1": "名所",
        "spots_intro": "有名な名所の現在の状況です。直近{window}日間の写真に基づきます。{date}更新。",
        "spot_title": "{spot}の{plants} 見頃情報｜Peak Season",
        "status": "{spot}の{plant}：{date}時点で「{stage}」（直近{window}日間のレポート{count}件より）。",
        "thin": "{spot}の{plant}：直近{window}日間に観察がありますが、段階を判断するには"
        "レポートが足りません（{date}時点）。",
        "none": "{spot}の{plant}：{date}時点で最近のレポートはありません。",
        "reports": "レポート{count}件",
        "photo_by": "写真",
        "originals": "元の投稿",
        "directions": "経路",
        "open_app": "この近くの最新情報をアプリで見る",
        "nearby": "近くの名所",
        "all_spots": "すべての名所",
        "updated": "{date}更新",
        "about": "仕組み",
        "home": "Peak Season",
        "km": "{km} km",
        "list_and": "・",
    },
    "ko": {
        "home_title": "Peak Season | 지금 내 주변 {plants} 절정 정보",
        "home_desc": "오픈소스 AI 모델 Gemma가 최근 사진을 확인해, 지금 내 주변에서 {plants}이(가) "
        "가장 아름다운 곳을 알려 줍니다. 무료, 가입 없음, 전 세계.",
        "spots_title": "{plants} 명소 현재 상황 | Peak Season",
        "spots_h1": "명소",
        "spots_intro": "유명 명소의 현재 상황입니다. 최근 {window}일간의 사진 기준. {date} 업데이트.",
        "spot_title": "{spot} {plants} 현재 상황 | Peak Season",
        "status": "{spot} {plant}: {date} 기준 '{stage}' (최근 {window}일 제보 {count}건 기준).",
        "thin": "{spot} {plant}: 최근 {window}일간 관찰은 있지만 단계를 판단하기에는 제보가 "
        "부족합니다({date} 기준).",
        "none": "{spot} {plant}: {date} 기준 최근 제보가 없습니다.",
        "reports": "제보 {count}건",
        "photo_by": "사진",
        "originals": "원본 게시물",
        "directions": "길찾기",
        "open_app": "이 근처의 최신 정보를 앱에서 보기",
        "nearby": "근처의 다른 명소",
        "all_spots": "모든 명소",
        "updated": "{date} 업데이트",
        "about": "작동 방식",
        "home": "Peak Season",
        "km": "{km} km",
        "list_and": "·",
    },
    "zh-TW": {
        "home_title": "Peak Season｜即時查看附近{plants}的最佳觀賞期",
        "home_desc": "由開源 AI 模型 Gemma 檢查最近的照片，告訴你附近哪裡的{plants}正值最美。"
        "免費、免註冊、全球適用。",
        "spots_title": "{plants}知名景點現況｜Peak Season",
        "spots_h1": "知名景點",
        "spots_intro": "知名賞景地點的目前狀況，根據最近{window}天的照片。{date}更新。",
        "spot_title": "{spot}{plants}現況｜Peak Season",
        "status": "{spot}的{plant}：截至{date}為「{stage}」（根據最近{window}天的{count}則回報）。",
        "thin": "{spot}的{plant}：最近{window}天有觀察紀錄，但回報不足，尚無法判斷階段"
        "（截至{date}）。",
        "none": "{spot}的{plant}：截至{date}沒有最近的回報。",
        "reports": "{count} 則回報",
        "photo_by": "照片",
        "originals": "原始貼文",
        "directions": "路線",
        "open_app": "在應用程式中查看附近的最新狀況",
        "nearby": "附近的其他知名景點",
        "all_spots": "所有知名景點",
        "updated": "{date}更新",
        "about": "運作方式",
        "home": "Peak Season",
        "km": "{km} 公里",
        "list_and": "與",
    },
}

LANG_NAMES = {"en": "English", "ja": "日本語", "ko": "한국어", "zh-TW": "繁體中文"}

HOME_BLOCK = re.compile(r"<!-- seo:start -->.*?<!-- seo:end -->", re.DOTALL)


def folder(lang: str) -> str:
    """URL prefix of a language: "" for English, "ja/" etc. otherwise."""
    return "" if lang == "en" else lang.lower() + "/"


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def json_ld(data: dict) -> str:
    # "</" would end the script element early; JSON allows the escaped form.
    text = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{text}</script>'


def plain_name(name: str) -> str:
    """ "Autumn leaves (maples)" -> "Autumn leaves" for titles."""
    return re.sub(r"\s*\([^)]*\)", "", name).strip()


def plant_name(target: dict, lang: str) -> str:
    local = (target.get("local_names") or {}).get(lang)
    return local or plain_name(target["display_name"]).lower()


def stage_label(target: dict, stage_id: str, lang: str) -> str | None:
    for s in target["stages"]:
        if s["id"] == stage_id:
            return (s.get("local_labels") or {}).get(lang) or s["label"]
    return None


def spot_name(spot: Spot, lang: str) -> str:
    """A spot's local name on pages in its own language, its English name elsewhere."""
    if spot.local_name and spot.lang.split("-")[0] == lang.split("-")[0]:
        return spot.local_name
    return spot.name


class Data:
    """The exported JSON, indexed for page rendering."""

    def __init__(self, data_dir: Path, spots: list[Spot], window_days: int):
        targets = json.loads((data_dir / "targets.json").read_text(encoding="utf-8"))
        index = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
        self.targets = {t["id"]: t for t in targets["targets"] if t.get("validated")}
        self.generated_at = index.get("generated_at") or ""
        self.date = self.generated_at[:10]
        self.window_days = window_days
        self.cells: dict[tuple[str, str], dict] = {}
        for p in sorted((data_dir / "shards").glob("*.json")):
            shard = json.loads(p.read_text(encoding="utf-8"))
            for tid, cells in (shard.get("targets") or {}).items():
                for c in cells:
                    self.cells[(tid, c["cell"])] = c
        self.spots = [s for s in spots if self.plants(s)]

    def plants(self, spot: Spot) -> list[dict]:
        return [self.targets[t] for t in spot.known_for if t in self.targets]

    def cell(self, spot: Spot, target_id: str) -> dict | None:
        return self.cells.get((target_id, spot.cell))

    def plant_list(self, spots: list[Spot] | None, lang: str) -> str:
        ids = {t["id"] for s in spots for t in self.plants(s)} if spots else set(self.targets)
        names = [plant_name(self.targets[i], lang) for i in sorted(ids)]
        return TEXT[lang]["list_and"].join(names)


def status_sentence(data: Data, spot: Spot, target: dict, lang: str) -> tuple[str, str | None]:
    """(quotable status sentence, stage id or None) for one plant at one spot."""
    tx = TEXT[lang]
    args = {
        "spot": spot_name(spot, lang),
        "plant": plant_name(target, lang),
        "date": data.date,
        "window": data.window_days,
    }
    c = data.cell(spot, target["id"])
    if c is None:
        return tx["none"].format(**args), None
    label = stage_label(target, c["stage"], lang)
    if label is None:  # not_enough_reports
        return tx["thin"].format(**args), None
    return tx["status"].format(stage=label, count=c["report_count"], **args), c["stage"]


def alternates(path: str, site_url: str) -> list[tuple[str, str]]:
    """(hreflang, absolute URL) for every language version of `path` (relative, no lang)."""
    out = [(lang, f"{site_url}/{folder(lang)}{path}") for lang in LANGS]
    return out + [("x-default", f"{site_url}/{path}")]


def head(title: str, desc: str, url: str, alts: list[tuple[str, str]], site_url: str) -> str:
    links = "\n".join(
        f'  <link rel="alternate" hreflang="{esc(h)}" href="{esc(u)}">' for h, u in alts
    )
    return f"""  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="canonical" href="{esc(url)}">
{links}
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Peak Season">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{esc(url)}">
  <meta property="og:image" content="{esc(site_url)}/og.png">
  <meta name="twitter:card" content="summary_large_image">"""


def page(lang: str, head_html: str, body: str, ld: dict) -> str:
    return f"""<!doctype html>
<html lang="{esc(lang)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
{head_html}
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/styles.css">
  {json_ld(ld)}
</head>
<body>
{body}
</body>
</html>
"""


def footer(data: Data, lang: str, path: str) -> str:
    tx = TEXT[lang]
    langs = " · ".join(
        f'<a href="/{folder(code)}{path}" lang="{code}" hreflang="{code}">{esc(name)}</a>'
        for code, name in LANG_NAMES.items()
    )
    return f"""  <footer class="foot">
    <p>{esc(tx["updated"].format(date=data.date))} ·
      <a href="/{folder(lang)}">{esc(tx["home"])}</a> ·
      <a href="/{folder(lang)}spots/">{esc(tx["all_spots"])}</a> ·
      <a href="/about/">{esc(tx["about"])}</a> ·
      <a href="https://github.com/klee1611/peak-season">GitHub</a></p>
    <p class="langs">{langs}</p>
  </footer>"""


def directions(spot: Spot, lang: str) -> str:
    dest = quote(f"{spot.local_name or spot.name}, {spot.country}")
    return f"""      <div class="directions" aria-label="{esc(TEXT[lang]["directions"])}">
        <a class="dir" rel="noopener" href="https://www.google.com/maps/dir/?api=1&amp;destination={dest}">Google Maps</a>
        <a class="dir" rel="noopener" href="https://maps.apple.com/?daddr={dest}">Apple Maps</a>
        <a class="dir" rel="noopener" href="https://www.openstreetmap.org/directions?to={dest}">OpenStreetMap</a>
      </div>"""


def evidence(c: dict | None, lang: str) -> str:
    """One thumbnail with attribution plus links to the originals. Never rehosted."""
    if not c or not c.get("evidence"):
        return ""
    tx = TEXT[lang]
    parts = []
    photo = next((e for e in c["evidence"] if e.get("thumb")), None)
    if photo:
        parts.append(
            f"""      <figure class="evidence">
        <a href="{esc(photo["link"])}" rel="noopener"><img src="{esc(photo["thumb"])}" alt="{esc(tx["photo_by"])}" loading="lazy" decoding="async" referrerpolicy="no-referrer"></a>
        <figcaption>{esc(photo.get("attribution") or "")}</figcaption>
      </figure>"""
        )
    links = " ".join(
        f'<a href="{esc(e["link"])}" rel="noopener">{i}</a>' for i, e in enumerate(c["evidence"], 1)
    )
    parts.append(f'      <p class="sources">{esc(tx["originals"])}: {links}</p>')
    return "\n".join(parts)


def nearest(data: Data, spot: Spot) -> list[tuple[Spot, float]]:
    others = [
        (s, geo.haversine_km(spot.lat, spot.lng, s.lat, s.lng)) for s in data.spots if s != spot
    ]
    close = [(s, d) for s, d in others if d <= NEARBY_MAX_KM]
    return sorted(close, key=lambda x: x[1])[:NEARBY_SPOTS]


def spot_page(data: Data, spot: Spot, lang: str, site_url: str) -> str:
    tx = TEXT[lang]
    name = spot_name(spot, lang)
    path = f"spots/{spot.id}/"
    url = f"{site_url}/{folder(lang)}{path}"
    sections, sentences = [], []
    for target in data.plants(spot):
        sentence, stage = status_sentence(data, spot, target, lang)
        sentences.append(sentence)
        c = data.cell(spot, target["id"])
        badge = stage_label(target, stage, lang) if stage else ""
        go = any(s["id"] == stage and s.get("go_now") for s in target["stages"])
        meta = ""
        if c and c.get("report_count"):
            meta = f'<p class="meta">{esc(tx["reports"].format(count=c["report_count"]))}</p>'
        sections.append(
            f"""    <section class="card">
      <div class="card-head">
        <h2 class="place">{esc(plant_name(target, lang))}</h2>
        {f'<span class="badge" data-stage="{"go" if go else "s"}">{esc(badge)}</span>' if badge else ""}
      </div>
      <p>{esc(sentence)}</p>
      {meta}
{evidence(c, lang)}
    </section>"""
        )
    near = "\n".join(
        f'      <li><a href="/{folder(lang)}spots/{s.id}/">{esc(spot_name(s, lang))}</a> '
        f"· {esc(tx['km'].format(km=round(d)))}</li>"
        for s, d in nearest(data, spot)
    )
    nearby_html = (
        f'    <h2>{esc(tx["nearby"])}</h2>\n    <ul class="spot-list">\n{near}\n    </ul>'
        if near
        else ""
    )
    plants = data.plant_list([spot], lang)
    title = tx["spot_title"].format(spot=name, plants=plants)
    desc = ("" if lang in ("ja", "zh-TW") else " ").join(sentences)
    app = f"/{folder(lang)}?lat={spot.lat}&amp;lng={spot.lng}"
    body = f"""  <header class="top">
    <p class="crumbs"><a href="/{folder(lang)}">Peak Season</a> › <a href="/{folder(lang)}spots/">{esc(tx["all_spots"])}</a></p>
    <h1>{esc(name)}</h1>
    <p class="tagline">{esc(spot.name if name != spot.name else (spot.local_name or ""))}</p>
  </header>
  <main>
{chr(10).join(sections)}
    <section class="card">
{directions(spot, lang)}
      <p><a href="{app}">{esc(tx["open_app"])}</a></p>
    </section>
{nearby_html}
  </main>
{footer(data, lang, path)}"""
    ld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "url": url,
        "inLanguage": lang,
        "dateModified": data.generated_at,
        "about": {
            "@type": "TouristAttraction",
            "name": spot.name,
            **({"alternateName": spot.local_name} if spot.local_name else {}),
            "geo": {"@type": "GeoCoordinates", "latitude": spot.lat, "longitude": spot.lng},
            "address": {"@type": "PostalAddress", "addressCountry": spot.country},
        },
    }
    return page(lang, head(title, desc, url, alternates(path, site_url), site_url), body, ld)


def spots_index(data: Data, lang: str, site_url: str) -> str:
    tx = TEXT[lang]
    path = "spots/"
    url = f"{site_url}/{folder(lang)}{path}"
    by_country: dict[str, list[Spot]] = {}
    for s in data.spots:
        by_country.setdefault(s.country, []).append(s)
    groups = []
    for country in sorted(by_country):
        items = []
        for s in by_country[country]:
            badges = []
            for target in data.plants(s):
                c = data.cell(s, target["id"])
                label = stage_label(target, c["stage"], lang) if c else None
                if label:
                    badges.append(f"{plant_name(target, lang)}: {label}")
            extra = f" · {esc(', '.join(badges))}" if badges else ""
            items.append(
                f'      <li><a href="/{folder(lang)}spots/{s.id}/">{esc(spot_name(s, lang))}</a>{extra}</li>'
            )
        groups.append(
            f"""    <h2>{esc(country_name(country, lang))}</h2>
    <ul class="spot-list">
{chr(10).join(items)}
    </ul>"""
        )
    plants = data.plant_list(None, lang)
    title = tx["spots_title"].format(plants=plants)
    intro = tx["spots_intro"].format(window=data.window_days, date=data.date)
    body = f"""  <header class="top">
    <p class="crumbs"><a href="/{folder(lang)}">Peak Season</a></p>
    <h1>{esc(tx["spots_h1"])}</h1>
    <p class="tagline">{esc(intro)}</p>
  </header>
  <main>
{chr(10).join(groups)}
  </main>
{footer(data, lang, path)}"""
    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "url": url,
        "inLanguage": lang,
        "dateModified": data.generated_at,
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i,
                    "url": f"{site_url}/{folder(lang)}spots/{s.id}/",
                    "name": spot_name(s, lang),
                }
                for i, s in enumerate(data.spots, 1)
            ],
        },
    }
    return page(lang, head(title, intro, url, alternates(path, site_url), site_url), body, ld)


def country_name(code: str, lang: str) -> str:
    """Localized country name; an unknown code is shown as the code itself."""
    return COUNTRIES.get(code, {}).get(lang) or COUNTRIES.get(code, {}).get("en") or code


# Countries that appear in data/spots.yaml. Add a row when a spot in a new country is added;
# an unknown code falls back to the code itself, so nothing breaks.
COUNTRIES = {
    "AU": {"en": "Australia", "ja": "オーストラリア", "ko": "호주", "zh-TW": "澳洲"},
    "CA": {"en": "Canada", "ja": "カナダ", "ko": "캐나다", "zh-TW": "加拿大"},
    "DE": {"en": "Germany", "ja": "ドイツ", "ko": "독일", "zh-TW": "德國"},
    "GB": {"en": "United Kingdom", "ja": "イギリス", "ko": "영국", "zh-TW": "英國"},
    "JP": {"en": "Japan", "ja": "日本", "ko": "일본", "zh-TW": "日本"},
    "KR": {"en": "South Korea", "ja": "韓国", "ko": "대한민국", "zh-TW": "韓國"},
    "TW": {"en": "Taiwan", "ja": "台湾", "ko": "대만", "zh-TW": "臺灣"},
    "US": {"en": "United States", "ja": "アメリカ", "ko": "미국", "zh-TW": "美國"},
}


def home_head(data: Data, lang: str, site_url: str) -> str:
    tx = TEXT[lang]
    plants = data.plant_list(None, lang)
    title = tx["home_title"].format(plants=plants)
    desc = tx["home_desc"].format(plants=plants)
    url = f"{site_url}/{folder(lang)}"
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "name": "Peak Season", "url": f"{site_url}/", "inLanguage": lang},
            {
                "@type": "WebApplication",
                "name": "Peak Season",
                "url": url,
                "inLanguage": lang,
                "applicationCategory": "TravelApplication",
                "operatingSystem": "Any",
                "isAccessibleForFree": True,
                "offers": {"@type": "Offer", "price": 0, "priceCurrency": "USD"},
                "description": desc,
            },
        ],
    }
    return (
        "<!-- seo:start -->\n"
        + head(title, desc, url, alternates("", site_url), site_url)
        + f"\n  {json_ld(ld)}\n  <!-- seo:end -->"
    )


def home_page(template: str, data: Data, lang: str, site_url: str) -> str:
    """The app's index.html with this language's head tags. Language homes carry data-lang so
    the app starts in that language; the root keeps following the visitor's own preference."""
    out = HOME_BLOCK.sub(lambda _: home_head(data, lang, site_url), template)
    tag = '<html lang="en">' if lang == "en" else f'<html lang="{lang}" data-lang="{lang}">'
    return re.sub(r'<html lang="[^"]*"( data-lang="[^"]*")?>', tag, out, count=1)


def sitemap(data: Data, site_url: str) -> str:
    paths = ["", "spots/"] + [f"spots/{s.id}/" for s in data.spots]
    urls = []
    for path in paths:
        alts = alternates(path, site_url)
        links = "".join(
            f'\n    <xhtml:link rel="alternate" hreflang="{h}" href="{esc(u)}"/>' for h, u in alts
        )
        for lang in LANGS:
            urls.append(
                f"  <url>\n    <loc>{esc(f'{site_url}/{folder(lang)}{path}')}</loc>"
                f"\n    <lastmod>{data.date}</lastmod>{links}\n  </url>"
            )
    urls.append(f"  <url>\n    <loc>{site_url}/about/</loc>\n  </url>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(urls) + "\n</urlset>\n"
    )


def write_text_if_changed(path: Path, text: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def write_pages(settings: Settings) -> list[str]:
    """Regenerate every static page from site/data. Returns the paths that changed."""
    site = settings.site_data_dir.parent
    site_url = settings.site_url.rstrip("/")
    data = Data(settings.site_data_dir, load_spots(settings.spots_path), settings.window_days)
    home = site / "index.html"
    template = home.read_text(encoding="utf-8") if home.is_file() else None
    files: dict[str, str] = {}
    for lang in LANGS:
        if template is not None:
            files[f"{folder(lang)}index.html"] = home_page(template, data, lang, site_url)
        files[f"{folder(lang)}spots/index.html"] = spots_index(data, lang, site_url)
        for spot in data.spots:
            files[f"{folder(lang)}spots/{spot.id}/index.html"] = spot_page(
                data, spot, lang, site_url
            )
    files["sitemap.xml"] = sitemap(data, site_url)
    changed = [rel for rel, text in files.items() if write_text_if_changed(site / rel, text)]
    log.info("pages: %d files, %d changed", len(files), len(changed))
    return changed


def record_history(settings: Settings) -> bool:
    """Keep one status per famous spot, plant and day in data/history/<year>.json.

    Shards are overwritten every run, so without this a season's peak dates are lost. The file
    is small (spots x plants x days) and feeds yearly recaps and "usually peaks in ..." text.
    """
    data = Data(settings.site_data_dir, load_spots(settings.spots_path), settings.window_days)
    if not data.date:
        return False
    day: dict[str, dict] = {}
    for spot in data.spots:
        for target in data.plants(spot):
            c = data.cell(spot, target["id"])
            if c:
                day.setdefault(spot.id, {})[target["id"]] = {
                    "stage": c["stage"],
                    "reports": c["report_count"],
                }
    path = settings.history_dir / f"{data.date[:4]}.json"
    history = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if history.get(data.date) == day:
        return False
    history[data.date] = day
    text = json.dumps(history, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    return write_text_if_changed(path, text)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    write_pages(get_settings())
    record_history(get_settings())
