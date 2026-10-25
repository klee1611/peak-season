// Peak Season site: static, no framework, no third-party scripts.
// Loads only the user's regional shard (plus neighbours) and renders place cards.
"use strict";

// ---------------------------------------------------------------------------
// Strings. Every user-visible string lives here. Plant and stage names come from targets.json
// (local_names / local_labels), so adding a plant never touches this file.
// ---------------------------------------------------------------------------
const I18N = {
  en: {
    tagline: "Where nature is at its peak near you, right now.",
    locating: "Finding your location… You can also pick a place below.",
    loading: "Loading reports…",
    pick_place: "Pick a city or famous spot:",
    cities: "Cities",
    spots_in: "Famous spots · {country}",
    use_my_location: "Use my location",
    cancel: "Cancel",
    location_declined:
      "Location is off for this site. Pick a place below, or allow location in your browser's site settings and tap “Use my location”.",
    location_failed: "Couldn't get your location. Pick a place below.",
    change_place: "Change place",
    within: "Within",
    units: "Distance units",
    units_km: "km",
    units_mi: "mi",
    plant: "Plant",
    load_failed: "Couldn't load the data. Please try again later.",
    nothing_nearby: "Nothing in season within {radius} of {place} right now.",
    thin_nearby: "Places near {place} have sightings this week, but not enough reports to judge the stage yet.",
    nearest_peak_near: "Closest at its peak: {name} ({plant}), {distance} away.",
    nearest_season_near: "Closest place in season: {name} ({plant}), {distance} away.",
    widen: "Show places within {radius}",
    nearest_region: "{plant} is at its peak in another region, roughly {distance} away.",
    nearest_in_season: "{plant} is in season in another region, roughly {distance} away.",
    nearest_none: "Nothing is in season anywhere we track right now.",
    your_location: "you",
    go_now_line: "{stage} {distance} away at {name}. {reports}. {advice}",
    best_line: "Nothing at its best nearby yet. Closest: {name}, {distance} away ({stage}).",
    go_weekend: "Go this weekend.",
    go_soon: "Go soon.",
    worth_a_look: "Worth a look.",
    reports_count: "{count, plural, one {# report} other {# reports}}",
    reports_recent: "{reports}, newest {ago}",
    not_enough_reports: "Not enough reports",
    in_season_hint: "{count, plural, one {# sighting} other {# sightings}} this week",
    compass: "N,NE,E,SE,S,SW,W,NW",
    dist_dir: "{distance} {dir}",
    photo_alt: "Photo from {place}",
    originals: "Originals:",
    famous_spot: "Famous spot",
    show_more: "{count, plural, one {Show # more place} other {Show # more places}}",
    show_more_thin:
      "{count, plural, one {Show # place with too few reports} other {Show # places with too few reports}}",
    updated: "Last updated {ago}.",
    about:
      "Reports come from iNaturalist and the web, checked by Gemma, an open-weight AI model, running on a free GitHub Actions runner. Photos stay with their owners; we only link to them.",
    language: "Language",
    famous_spots: "Famous spots",
    how_it_works: "How it works",
    sentence_gap: " ",
  },
  ja: {
    tagline: "近くで今いちばん見頃の自然を。",
    locating: "現在地を取得しています…下から場所を選ぶこともできます。",
    loading: "レポートを読み込んでいます…",
    pick_place: "都市または名所を選ぶ：",
    cities: "都市",
    spots_in: "名所・{country}",
    use_my_location: "現在地を使う",
    cancel: "キャンセル",
    location_declined:
      "このサイトの位置情報がオフです。下から場所を選ぶか、ブラウザのサイト設定で位置情報を許可してから「現在地を使う」を押してください。",
    location_failed: "現在地を取得できませんでした。下から場所を選んでください。",
    change_place: "場所を変更",
    within: "半径",
    units: "距離の単位",
    units_km: "km",
    units_mi: "マイル",
    plant: "植物",
    load_failed: "データを読み込めませんでした。しばらくしてからもう一度お試しください。",
    nothing_nearby: "{place}から{radius}以内に、今シーズン中のものはありません。",
    thin_nearby: "{place}の近くに今週の観察はありますが、段階を判断するにはレポートが足りません。",
    nearest_peak_near: "最も近い見頃：{name}（{plant}）、{distance}先。",
    nearest_season_near: "最も近いシーズン中の場所：{name}（{plant}）、{distance}先。",
    widen: "半径{radius}まで表示",
    nearest_region: "{plant}は別の地域で見頃です（約{distance}先）。",
    nearest_in_season: "{plant}は別の地域でシーズン中です（約{distance}先）。",
    nearest_none: "現在、追跡しているどの地域にもシーズン中のものはありません。",
    your_location: "現在地",
    go_now_line: "{distance}先の{name}が{stage}です。{reports}。{advice}",
    best_line: "近くにはまだ見頃の場所はありません。最寄り：{name}（{distance}先、{stage}）。",
    go_weekend: "今週末に行きましょう。",
    go_soon: "早めに行きましょう。",
    worth_a_look: "行ってみる価値があります。",
    reports_count: "レポート{count}件",
    reports_recent: "{reports}、最新は{ago}",
    not_enough_reports: "レポート不足",
    in_season_hint: "今週の観察{count}件",
    compass: "北,北東,東,南東,南,南西,西,北西",
    dist_dir: "{dir}に{distance}",
    photo_alt: "{place}の写真",
    originals: "元の投稿：",
    famous_spot: "名所",
    show_more: "さらに{count}か所を表示",
    show_more_thin: "レポートが少ない{count}か所を表示",
    updated: "最終更新：{ago}。",
    about:
      "レポートは iNaturalist とウェブから集め、無料の GitHub Actions ランナー上で動くオープンウェイトAIモデル Gemma が確認しています。写真は撮影者のもので、ここではリンクのみ表示しています。",
    language: "言語",
    famous_spots: "名所",
    how_it_works: "仕組み",
    sentence_gap: "",
  },
  ko: {
    tagline: "지금 내 주변에서 자연이 가장 아름다운 곳.",
    locating: "위치를 찾는 중… 아래에서 장소를 고를 수도 있어요.",
    loading: "제보를 불러오는 중…",
    pick_place: "도시 또는 명소 선택:",
    cities: "도시",
    spots_in: "명소 · {country}",
    use_my_location: "내 위치 사용",
    cancel: "취소",
    location_declined:
      "이 사이트의 위치 정보가 꺼져 있습니다. 아래에서 장소를 고르거나, 브라우저 사이트 설정에서 위치를 허용한 뒤 '내 위치 사용'을 누르세요.",
    location_failed: "위치를 가져올 수 없습니다. 아래에서 장소를 골라 주세요.",
    change_place: "장소 변경",
    within: "반경",
    units: "거리 단위",
    units_km: "km",
    units_mi: "마일",
    plant: "식물",
    load_failed: "데이터를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.",
    nothing_nearby: "지금 {place} 반경 {radius} 안에는 제철인 것이 없습니다.",
    thin_nearby: "{place} 근처에 이번 주 관찰이 있지만, 단계를 판단하기에는 제보가 부족합니다.",
    nearest_peak_near: "가장 가까운 절정: {name} ({plant}), {distance} 거리.",
    nearest_season_near: "가장 가까운 제철 장소: {name} ({plant}), {distance} 거리.",
    widen: "반경 {radius}까지 보기",
    nearest_region: "{plant}은(는) 다른 지역에서 절정입니다 (약 {distance} 거리).",
    nearest_in_season: "{plant}은(는) 다른 지역에서 제철입니다 (약 {distance} 거리).",
    nearest_none: "지금은 추적 중인 어느 지역에도 제철인 것이 없습니다.",
    your_location: "내 위치",
    go_now_line: "{distance} 거리의 {name}: {stage}. {reports}. {advice}",
    best_line: "근처에는 아직 절정인 곳이 없습니다. 가장 가까운 곳: {name}, {distance} 거리 ({stage}).",
    go_weekend: "이번 주말에 가 보세요.",
    go_soon: "서둘러 가 보세요.",
    worth_a_look: "가 볼 만합니다.",
    reports_count: "제보 {count}건",
    reports_recent: "{reports}, 최신 {ago}",
    not_enough_reports: "제보 부족",
    in_season_hint: "이번 주 관찰 {count}건",
    compass: "북,북동,동,남동,남,남서,서,북서",
    dist_dir: "{dir}쪽 {distance}",
    photo_alt: "{place} 사진",
    originals: "원본:",
    famous_spot: "명소",
    show_more: "{count}곳 더 보기",
    show_more_thin: "제보가 적은 {count}곳 보기",
    updated: "마지막 업데이트: {ago}.",
    about:
      "제보는 iNaturalist와 웹에서 모으며, 무료 GitHub Actions 러너에서 실행되는 오픈 웨이트 AI 모델 Gemma가 확인합니다. 사진은 원작자의 것이며, 여기서는 링크만 제공합니다.",
    language: "언어",
    famous_spots: "명소",
    how_it_works: "작동 방식",
    sentence_gap: " ",
  },
  "zh-TW": {
    tagline: "現在，你附近哪裡的自然景色正值最美。",
    locating: "正在取得你的位置…也可以直接在下方選擇地點。",
    loading: "正在載入回報…",
    pick_place: "選擇城市或知名景點：",
    cities: "城市",
    spots_in: "知名景點・{country}",
    use_my_location: "使用我的位置",
    cancel: "取消",
    location_declined:
      "此網站的位置功能已關閉。請在下方選擇地點，或在瀏覽器的網站設定中允許位置存取後，再按「使用我的位置」。",
    location_failed: "無法取得你的位置，請在下方選擇地點。",
    change_place: "更換地點",
    within: "半徑",
    units: "距離單位",
    units_km: "公里",
    units_mi: "英里",
    plant: "植物",
    load_failed: "無法載入資料，請稍後再試。",
    nothing_nearby: "目前{place}方圓{radius}內沒有正當季的景色。",
    thin_nearby: "{place}附近本週有觀察紀錄，但回報不足，尚無法判斷階段。",
    nearest_peak_near: "最近正值最佳時期的地點：{name}（{plant}），{distance}外。",
    nearest_season_near: "最近正當季的地點：{name}（{plant}），{distance}外。",
    widen: "顯示半徑{radius}內的地點",
    nearest_region: "{plant}在另一個地區正值最佳時期（約{distance}外）。",
    nearest_in_season: "{plant}在另一個地區正當季（約{distance}外）。",
    nearest_none: "目前我們追蹤的地區都沒有正當季的景色。",
    your_location: "你的位置",
    go_now_line: "{distance}外的{name}：{stage}。{reports}。{advice}",
    best_line: "附近還沒有正值最佳時期的地點。最近的是{name}，{distance}外（{stage}）。",
    go_weekend: "這個週末就去吧。",
    go_soon: "盡快去吧。",
    worth_a_look: "值得去看看。",
    reports_count: "{count} 則回報",
    reports_recent: "{reports}，最新一則{ago}",
    not_enough_reports: "回報不足",
    in_season_hint: "本週 {count} 筆觀察",
    compass: "北,東北,東,東南,南,西南,西,西北",
    dist_dir: "{dir}方 {distance}",
    photo_alt: "{place}的照片",
    originals: "原始貼文：",
    famous_spot: "知名景點",
    show_more: "再顯示 {count} 個地點",
    show_more_thin: "顯示回報較少的 {count} 個地點",
    updated: "最後更新：{ago}。",
    about:
      "回報來自 iNaturalist 與網路，由在免費 GitHub Actions 執行器上運行的開放權重 AI 模型 Gemma 檢查。照片屬於原作者，我們只提供連結。",
    language: "語言",
    famous_spots: "知名景點",
    how_it_works: "運作方式",
    sentence_gap: "",
  },
};
// Language names shown in the picker, each in its own language.
const LANG_NAMES = { en: "English", ja: "日本語", ko: "한국어", "zh-TW": "繁體中文" };

// Language homes (/ja/, /ko/, /zh-tw/) preset their language with <html data-lang>.
const PAGE_LANG = document.documentElement.dataset.lang || null;
const langHome = (lang) => (lang === "en" ? "/" : `/${lang.toLowerCase()}/`);

/** ?lang= first, then the language home's own language, then the saved choice, then the browser. */
function pickLang() {
  const wanted = [
    new URLSearchParams(location.search).get("lang"),
    PAGE_LANG,
    safeGet("lang"),
    ...(navigator.languages || []),
  ];
  for (const tag of wanted) {
    if (!tag) continue;
    if (Object.hasOwn(I18N, tag)) return tag;
    const base = tag.toLowerCase().split("-")[0];
    if (base === "zh") return "zh-TW"; // the only Chinese UI so far
    if (Object.hasOwn(I18N, base)) return base;
  }
  return "en";
}

function safeGet(k) {
  try { return localStorage.getItem(k); } catch { return null; }
}

let LANG = pickLang();
let PLURALS = new Intl.PluralRules(LANG);
let RTF = new Intl.RelativeTimeFormat(LANG, { numeric: "auto" });

function setLang(lang) {
  LANG = lang;
  PLURALS = new Intl.PluralRules(LANG);
  RTF = new Intl.RelativeTimeFormat(LANG, { numeric: "auto" });
  document.documentElement.lang = LANG;
}

/** t("key", {var: value}). Supports {var} and a tiny {count, plural, one {...} other {...}}. */
function t(key, vars = {}) {
  let s = (Object.hasOwn(I18N[LANG], key) ? I18N[LANG][key] : I18N.en[key]) ?? key;
  s = s.replace(/\{(\w+), plural, one \{([^}]*)\} other \{([^}]*)\}\}/g, (_, name, one, other) => {
    const n = vars[name];
    return (PLURALS.select(n) === "one" ? one : other).replace("#", fmtNum(n));
  });
  return s.replace(/\{(\w+)\}/g, (_, name) => (name in vars ? String(vars[name]) : `{${name}}`));
}

const fmtNum = (n) => new Intl.NumberFormat(LANG).format(n);

function timeAgo(iso, now = Date.now()) {
  const secs = (new Date(iso).getTime() - now) / 1000;
  const units = [
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of units) {
    if (Math.abs(secs) >= size) return RTF.format(Math.round(secs / size), unit);
  }
  return RTF.format(0, "minute");
}

// ---------------------------------------------------------------------------
// Geo: geohash encode / neighbours / centre, and haversine distance.
// ---------------------------------------------------------------------------
const B32 = "0123456789bcdefghjkmnpqrstuvwxyz";

function geohash(lat, lng, precision) {
  let latR = [-90, 90], lngR = [-180, 180], bits = 0, bit = 0, even = true, out = "";
  while (out.length < precision) {
    const r = even ? lngR : latR, v = even ? lng : lat, mid = (r[0] + r[1]) / 2;
    if (v >= mid) { bits = bits * 2 + 1; r[0] = mid; } else { bits = bits * 2; r[1] = mid; }
    even = !even;
    if (++bit === 5) { out += B32[bits]; bits = 0; bit = 0; }
  }
  return out;
}

function geohashBounds(hash) {
  let latR = [-90, 90], lngR = [-180, 180], even = true;
  for (const ch of hash) {
    const v = B32.indexOf(ch);
    for (let i = 4; i >= 0; i--) {
      const r = even ? lngR : latR, mid = (r[0] + r[1]) / 2;
      if ((v >> i) & 1) r[0] = mid; else r[1] = mid;
      even = !even;
    }
  }
  return { latR, lngR };
}

function geohashCentre(hash) {
  const { latR, lngR } = geohashBounds(hash);
  return [(latR[0] + latR[1]) / 2, (lngR[0] + lngR[1]) / 2];
}

/** The hash itself plus its 8 neighbours (longitude wraps; no cells past the poles). */
function geohashWithNeighbours(hash) {
  const { latR, lngR } = geohashBounds(hash);
  const [lat, lng] = geohashCentre(hash);
  const dLat = latR[1] - latR[0], dLng = lngR[1] - lngR[0];
  const out = new Set();
  for (const dy of [-1, 0, 1]) {
    for (const dx of [-1, 0, 1]) {
      const y = lat + dy * dLat;
      if (y <= -90 || y >= 90) continue;
      const x = ((lng + dx * dLng + 540) % 360) - 180;
      out.add(geohash(y, x, hash.length));
    }
  }
  return [...out];
}

function haversineKm(lat1, lng1, lat2, lng2) {
  const rad = Math.PI / 180, dLat = (lat2 - lat1) * rad, dLng = (lng2 - lng1) * rad;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(a));
}

/** Initial bearing from point 1 to point 2, in degrees clockwise from north. */
function bearingDeg(lat1, lng1, lat2, lng2) {
  const rad = Math.PI / 180;
  const y = Math.sin((lng2 - lng1) * rad) * Math.cos(lat2 * rad);
  const x = Math.cos(lat1 * rad) * Math.sin(lat2 * rad) -
    Math.sin(lat1 * rad) * Math.cos(lat2 * rad) * Math.cos((lng2 - lng1) * rad);
  return (Math.atan2(y, x) / rad + 360) % 360;
}

// ---------------------------------------------------------------------------
// State and storage (per-viewer conveniences only; the page works without them).
// ---------------------------------------------------------------------------
// [English name (also the saved key), lat, lng, local names]
const CITIES = [
  ["Toronto", 43.6532, -79.3832, { ja: "トロント", ko: "토론토", "zh-TW": "多倫多" }],
  ["New York", 40.7128, -74.006, { ja: "ニューヨーク", ko: "뉴욕", "zh-TW": "紐約" }],
  ["Vancouver", 49.2827, -123.1207, { ja: "バンクーバー", ko: "밴쿠버", "zh-TW": "溫哥華" }],
  ["London", 51.5074, -0.1278, { ja: "ロンドン", ko: "런던", "zh-TW": "倫敦" }],
  ["Paris", 48.8566, 2.3522, { ja: "パリ", ko: "파리", "zh-TW": "巴黎" }],
  ["Tokyo", 35.6762, 139.6503, { ja: "東京", ko: "도쿄", "zh-TW": "東京" }],
  ["Kyoto", 35.0116, 135.7681, { ja: "京都", ko: "교토", "zh-TW": "京都" }],
  ["Seoul", 37.5665, 126.978, { ja: "ソウル", ko: "서울", "zh-TW": "首爾" }],
  ["Taipei", 25.033, 121.5654, { ja: "台北", ko: "타이베이", "zh-TW": "臺北" }],
  ["Sydney", -33.8688, 151.2093, { ja: "シドニー", ko: "시드니", "zh-TW": "雪梨" }],
  ["Melbourne", -37.8136, 144.9631, { ja: "メルボルン", ko: "멜버른", "zh-TW": "墨爾本" }],
];

const RADII_KM = [50, 100, 250, 500, 1000, 2000];
// Below this many reports a go_now stage is shown, but as a tentative call.
const SOLID_REPORTS = 4;

const store = {
  get: safeGet,
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
};

const params = new URLSearchParams(location.search);
const DATA = params.has("fixtures") ? "/data/fixtures/" : "/data/";
const SHOW_UNVALIDATED = params.has("all"); // dev only: show targets not yet validated

const state = {
  targets: [],
  index: null,
  places: [], // picker entries: {key, lat, lng, label(), group}
  place: null, // {lat, lng, entry: picker entry, or null for "your location"}
  loadedShards: new Set(),
  cells: {}, // target id -> [cell with distanceKm, bearing]
  target: null,
  radiusKm: RADII_KM.includes(Number(store.get("radius"))) ? Number(store.get("radius")) : 100,
  units: store.get("units") === "mi" ? "mi" : "km",
  chosenTarget: false,
  showAll: false,
  pickerMsg: null,
  locateSeq: 0, // bumped on every place choice, so a late geolocation answer can't override it
};

const $ = (id) => document.getElementById(id);
const MAX_CARDS = 12;

function fmtDistance(km) {
  const v = state.units === "mi" ? km * 0.621371 : km;
  const digits = v < 10 ? 1 : 0;
  return `${new Intl.NumberFormat(LANG, { maximumFractionDigits: digits }).format(v)} ${t("units_" + state.units)}`;
}

async function getJSON(path) {
  const res = await fetch(DATA + path, { cache: "no-cache" });
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Location
// ---------------------------------------------------------------------------
const targetName = (tg) => tg.local_names?.[LANG] || tg.display_name;
// "Autumn leaves (maples)" -> "Autumn leaves", for use inside a sentence that has its own brackets.
const targetShortName = (tg) => targetName(tg).replace(/\s*\([^)]*\)/g, "").trim();
const stageLabel = (stage) => stage.local_labels?.[LANG] || stage.label;
// The place's label is worked out at render time so it follows a language change.
const placeLabel = (place) => (place.entry ? place.entry.label() : t("your_location"));
const sameLang = (a, b) => a.toLowerCase().split("-")[0] === b.toLowerCase().split("-")[0];

function countryName(code) {
  try { return new Intl.DisplayNames(LANG, { type: "region" }).of(code); } catch { return code; }
}

/** Cities, then famous spots grouped by country. Spots use their local name in their own language. */
function buildPlaces(spots) {
  const cities = CITIES.map((c) => ({
    key: c[0], lat: c[1], lng: c[2], group: "cities", label: () => c[3]?.[LANG] || c[0],
  }));
  const spotPlaces = spots.map((s) => ({
    key: `spot:${s.id}`, lat: s.lat, lng: s.lng, group: s.country,
    label: () => (s.local_name && sameLang(s.lang, LANG) ? s.local_name : s.name),
  }));
  return [...cities, ...spotPlaces];
}

function fillCityOptions() {
  const sel = $("city");
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "—";
  const groups = new Map();
  for (const p of state.places) {
    if (!groups.has(p.group)) {
      const g = document.createElement("optgroup");
      g.label = p.group === "cities" ? t("cities") : t("spots_in", { country: countryName(p.group) });
      groups.set(p.group, g);
    }
    const o = document.createElement("option");
    o.value = p.key;
    o.textContent = p.label();
    groups.get(p.group).append(o);
  }
  const chosen = sel.value;
  sel.replaceChildren(blank, ...groups.values());
  sel.value = chosen;
}

function setupCityPicker() {
  const sel = $("city");
  sel.addEventListener("change", () => {
    const p = state.places.find((x) => x.key === sel.value);
    if (!p) return;
    store.set("city", p.key);
    useLocation({ lat: p.lat, lng: p.lng, entry: p });
  });
  $("use-location").addEventListener("click", () => locate(true));
  $("cancel-place").addEventListener("click", () => {
    $("locate").hidden = true;
    $("change-place").focus();
  });
}

function showPicker(msgKey) {
  $("locate").hidden = false;
  // Cancel only makes sense when there is a place to go back to.
  $("cancel-place").hidden = !state.place;
  state.pickerMsg = msgKey;
  $("locate-msg").textContent = msgKey ? t(msgKey) : "";
  $("locate-msg").hidden = !msgKey;
  $("status").textContent = "";
}

function locate(force = false) {
  const lat = parseFloat(params.get("lat")), lng = parseFloat(params.get("lng"));
  if (!force && Number.isFinite(lat) && Number.isFinite(lng)) {
    return useLocation({ lat, lng, entry: null });
  }
  const saved = state.places.find((p) => p.key === store.get("city"));
  if (!force && saved) return useLocation({ lat: saved.lat, lng: saved.lng, entry: saved });
  if (!("geolocation" in navigator)) return showPicker("location_failed");

  // Show the picker while the browser asks, so nobody waits on a blank page.
  showPicker("locating");
  const seq = ++state.locateSeq;
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      if (seq !== state.locateSeq) return; // the user picked a place meanwhile
      store.set("city", "");
      useLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude, entry: null });
    },
    (err) => {
      if (seq !== state.locateSeq) return;
      showPicker(err.code === err.PERMISSION_DENIED ? "location_declined" : "location_failed");
    },
    { timeout: 8000, maximumAge: 30 * 60 * 1000 },
  );
}

async function useLocation(place) {
  state.locateSeq++;
  state.place = place;
  $("locate").hidden = true;
  $("status").textContent = t("loading");
  try {
    await loadCells();
  } catch (e) {
    console.error(e);
    $("status").textContent = t("load_failed");
    return;
  }
  $("status").textContent = "";
  state.chosenTarget = false;
  state.showAll = false;
  render();
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------
function visibleTargets() {
  return state.targets.filter((tg) => tg.validated || SHOW_UNVALIDATED);
}

async function loadCells() {
  const { lat, lng } = state.place;
  const wanted = geohashWithNeighbours(geohash(lat, lng, 2)).filter((h) => h in state.index.shards);
  const shards = await Promise.all(wanted.map((h) => getJSON(`shards/${h}.json`)));
  const cells = {};
  for (const shard of shards) {
    for (const [tid, list] of Object.entries(shard.targets || {})) {
      for (const c of list) {
        (cells[tid] ||= []).push({
          ...c,
          distanceKm: haversineKm(lat, lng, c.lat, c.lng),
          bearing: bearingDeg(lat, lng, c.lat, c.lng),
        });
      }
    }
  }
  state.cells = cells;
  state.loadedShards = new Set(wanted);
}

function nearbyCells(tid) {
  return (state.cells[tid] || []).filter((c) => c.distanceKm <= state.radiusKm);
}

function stageInfo(target, stageId) {
  const i = target.stages.findIndex((s) => s.id === stageId);
  return i < 0 ? null : { ...target.stages[i], index: i };
}

function isGoNow(target, cell) {
  return Boolean(stageInfo(target, cell.stage)?.go_now);
}

function isSolid(cell) {
  return cell.report_count >= SOLID_REPORTS;
}

function sortCells(target, cells) {
  // go_now first, then by how close the stage is to go_now (just before it, then just after it,
  // then further away), then "not enough reports"; ties by distance.
  const go = target.stages.map((s, i) => (s.go_now ? i : -1)).filter((i) => i >= 0);
  const lo = go.length ? Math.min(...go) : target.stages.length - 1;
  const hi = go.length ? Math.max(...go) : lo;
  const rank = (c) => {
    const s = stageInfo(target, c.stage);
    if (!s) return 1000;
    if (s.index >= lo && s.index <= hi) return 0;
    return s.index < lo ? (lo - s.index) * 2 - 1 : (s.index - hi) * 2;
  };
  return [...cells].sort((a, b) => rank(a) - rank(b) || a.distanceKm - b.distanceKm);
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------
function render() {
  const targets = visibleTargets().filter((tg) => nearbyCells(tg.id).length > 0);
  $("results").hidden = false;
  renderUpdated();
  $("widen").hidden = true;

  if (targets.length === 0) {
    state.target = null;
    renderChips(targets);
    $("cards").replaceChildren();
    $("more").hidden = true;
    renderNothingNearby();
    return;
  }
  if (!state.chosenTarget || !targets.some((tg) => tg.id === state.target?.id)) {
    // Featured plant: the one with the most go_now cells nearby, then the most cells.
    const score = (tg) => {
      const cs = nearbyCells(tg.id);
      return [cs.filter((c) => isGoNow(tg, c)).length, cs.length];
    };
    state.target = [...targets].sort((a, b) => {
      const [ga, na] = score(a), [gb, nb] = score(b);
      return gb - ga || nb - na;
    })[0];
  }
  renderChips(targets);
  const cells = sortCells(state.target, nearbyCells(state.target.id));
  $("headline").textContent = headlineText(state.target, cells);
  // Only "not enough reports" nearby: say so, and point past the radius like the empty state.
  if (!$("headline").textContent) renderNothingNearby("thin_nearby");
  // Keep the page short: the best few staged places first. Places with too few reports to judge
  // only take the list when there is nothing else; otherwise they wait behind one tap.
  const staged = cells.filter((c) => stageInfo(state.target, c.stage)).length;
  const shown = state.showAll ? cells : cells.slice(0, staged ? Math.min(staged, MAX_CARDS) : MAX_CARDS);
  $("cards").replaceChildren(...shown.map((c) => renderCard(state.target, c)));
  const rest = cells.slice(shown.length);
  const more = $("more");
  more.hidden = rest.length === 0;
  const thinOnly = !rest.some((c) => stageInfo(state.target, c.stage));
  more.textContent = t(thinOnly ? "show_more_thin" : "show_more", { count: rest.length });
}

function renderChips(targets) {
  const box = $("chips");
  box.replaceChildren();
  box.hidden = targets.length === 0;
  box.setAttribute("aria-label", t("plant"));
  if (targets.length === 1) {
    // One plant: say which, but don't dress it up as a control that does nothing.
    const label = document.createElement("span");
    label.className = "plant-label";
    label.textContent = targetName(targets[0]);
    box.append(label);
    return;
  }
  for (const tg of targets) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.setAttribute("aria-pressed", String(tg.id === state.target?.id));
    b.textContent = targetName(tg);
    b.addEventListener("click", () => {
      state.target = tg;
      state.chosenTarget = true;
      state.showAll = false;
      render();
    });
    box.append(b);
  }
}

function adviceKey(cell) {
  const fresh = Date.now() - new Date(cell.latest_report_at).getTime() < 3 * 86400 * 1000;
  if (!fresh || !isSolid(cell)) return "worth_a_look";
  // On a Sunday "this weekend" is nearly over.
  return new Date().getDay() === 0 ? "go_soon" : "go_weekend";
}

function headlineText(target, cells) {
  const best = cells.find((c) => isGoNow(target, c));
  if (best) {
    return t("go_now_line", {
      stage: stageLabel(stageInfo(target, best.stage)),
      distance: fmtDistance(best.distanceKm),
      name: best.name || "",
      reports: t("reports_recent", {
        reports: t("reports_count", { count: best.report_count }),
        ago: timeAgo(best.latest_report_at),
      }),
      advice: t(adviceKey(best)),
    });
  }
  const staged = cells.filter((c) => stageInfo(target, c.stage));
  if (staged.length === 0) return "";
  const closest = staged.reduce((a, b) => (b.distanceKm < a.distanceKm ? b : a));
  return t("best_line", {
    name: closest.name || "",
    distance: fmtDistance(closest.distanceKm),
    stage: stageLabel(stageInfo(target, closest.stage)),
  });
}

/**
 * The closest loaded cell beyond the radius: at its peak if any, else one with a stage, else (only
 * when nothing at all is nearby) any sighting.
 */
function closestBeyondRadius(allowThin) {
  const maxKm = RADII_KM[RADII_KM.length - 1];
  const best = [null, null, null]; // peak, staged, thin
  for (const tg of visibleTargets()) {
    for (const c of state.cells[tg.id] || []) {
      if (c.distanceKm <= state.radiusKm || c.distanceKm > maxKm) continue;
      const tier = isGoNow(tg, c) ? 0 : stageInfo(tg, c.stage) ? 1 : 2;
      if (!best[tier] || c.distanceKm < best[tier].cell.distanceKm) best[tier] = { tg, cell: c, go: tier === 0 };
    }
  }
  return best[0] || best[1] || (allowThin ? best[2] : null);
}

function renderNothingNearby(baseKey = "nothing_nearby") {
  const base = t(baseKey, { radius: fmtDistance(state.radiusKm), place: placeLabel(state.place) });
  const near = closestBeyondRadius(baseKey === "nothing_nearby");
  if (near) {
    // Something is in the data we already have: name it and offer a one-tap wider search.
    const radius = RADII_KM.find((r) => r >= near.cell.distanceKm);
    $("headline").textContent = base + t("sentence_gap") + t(near.go ? "nearest_peak_near" : "nearest_season_near", {
      name: near.cell.name || "",
      plant: targetShortName(near.tg),
      distance: fmtDistance(near.cell.distanceKm),
    });
    const widen = $("widen");
    widen.textContent = t("widen", { radius: fmtDistance(radius) });
    widen.hidden = false;
    widen.onclick = () => {
      setRadius(radius);
      state.target = near.tg;
      state.chosenTarget = true;
      render();
    };
    return;
  }
  if (baseKey !== "nothing_nearby") {
    $("headline").textContent = base;
    return;
  }
  // Otherwise look at other regions. Only regions we haven't loaded, so the estimate never points
  // back at the user's own area; centres are approximate (~1,250 km wide), so round generously.
  const names = new Map(visibleTargets().map((tg) => [tg.id, targetShortName(tg)]));
  const nearest = (field) => {
    let best = null;
    for (const [hash, info] of Object.entries(state.index.shards)) {
      if (state.loadedShards.has(hash)) continue;
      const ids = (info[field] || []).filter((id) => names.has(id));
      if (ids.length === 0) continue;
      const [lat, lng] = geohashCentre(hash);
      const d = haversineKm(state.place.lat, state.place.lng, lat, lng);
      if (!best || d < best.d) best = { d, plant: names.get(ids[0]) };
    }
    return best;
  };
  const say = (key, best) =>
    t(key, { plant: best.plant, distance: fmtDistance(Math.max(100, Math.round(best.d / 100) * 100)) });
  const peak = nearest("go_now");
  const season = peak ? null : nearest("in_season");
  const tail = peak ? say("nearest_region", peak) : season ? say("nearest_in_season", season) : t("nearest_none");
  $("headline").textContent = base + t("sentence_gap") + tail;
}

function compass(deg) {
  return t("compass").split(",")[Math.round(deg / 45) % 8];
}

/** Links come from third-party data; export already drops non-http(s) URLs, this is a backstop. */
function webUrl(url) {
  try { return ["http:", "https:"].includes(new URL(url).protocol) ? url : null; } catch { return null; }
}

function evidenceLabel(e, i) {
  if (e.source === "inaturalist") return `iNaturalist ${i + 1}`;
  try { return new URL(e.link).hostname.replace(/^www\./, ""); } catch { return String(i + 1); }
}

function renderCard(target, c) {
  const li = $("card-tpl").content.firstElementChild.cloneNode(true);
  const stage = stageInfo(target, c.stage);
  const name = c.name || `${c.lat}, ${c.lng}`;
  li.querySelector(".place").textContent = name;

  const badge = li.querySelector(".badge");
  badge.textContent = stage ? stageLabel(stage) : t("not_enough_reports");
  badge.dataset.stage = stage ? (stage.go_now ? "go" : `s${stage.index}`) : "none";
  // A go_now call from very few photos is shown as tentative (outlined, not filled).
  if (stage?.go_now && !isSolid(c)) badge.classList.add("tentative");
  if (stage) badge.style.setProperty("--progress", String(stage.index / Math.max(1, target.stages.length - 1)));

  // Direction from the user tells apart cells that share a name ("Toronto", "Toronto", ...).
  const bits = [t("dist_dir", { distance: fmtDistance(c.distanceKm), dir: compass(c.bearing) })];
  if (c.report_count > 0) {
    bits.push(t("reports_recent", {
      reports: t("reports_count", { count: c.report_count }),
      ago: timeAgo(c.latest_report_at),
    }));
  } else if (c.in_season_signals > 0) {
    bits.push(t("in_season_hint", { count: c.in_season_signals }));
  }
  if (c.is_famous_spot) bits.push(t("famous_spot"));
  li.querySelector(".meta").textContent = bits.join(" · ");

  const evidence = (c.evidence || []).filter((e) => webUrl(e.link));
  const photo = evidence.find((e) => webUrl(e.thumb));
  if (photo) {
    const fig = li.querySelector(".evidence");
    fig.hidden = false;
    li.querySelector(".evidence-link").href = photo.link;
    const img = li.querySelector("img");
    img.src = photo.thumb;
    img.alt = t("photo_alt", { place: name });
    li.querySelector("figcaption").textContent = photo.attribution || "";
  }

  const sources = li.querySelector(".sources");
  if (evidence.length) {
    const label = document.createElement("span");
    label.textContent = t("originals");
    sources.append(label);
  }
  evidence.forEach((e, i) => {
    const a = document.createElement("a");
    a.href = e.link;
    a.rel = "noopener";
    a.target = "_blank";
    a.textContent = evidenceLabel(e, i);
    sources.append(a);
  });

  // Famous spots are searched by name; other places use the median photo location.
  const dest = c.directions_query ? encodeURIComponent(c.directions_query) : `${c.lat},${c.lng}`;
  li.querySelector(".google").href = `https://www.google.com/maps/dir/?api=1&destination=${dest}`;
  li.querySelector(".apple").href = `https://maps.apple.com/?daddr=${dest}`;
  li.querySelector(".osm").href = `https://www.openstreetmap.org/directions?to=${dest}`;
  return li;
}

function renderUpdated() {
  $("updated").textContent = state.index?.generated_at
    ? t("updated", { ago: timeAgo(state.index.generated_at) })
    : "";
}

function fillRadiusOptions() {
  // Values stay in km; labels follow the chosen unit, so "Within" never mislabels the filter.
  const sel = $("radius");
  sel.replaceChildren(...RADII_KM.map((km) => {
    const o = document.createElement("option");
    o.value = String(km);
    o.textContent = fmtDistance(km);
    return o;
  }));
  sel.value = String(state.radiusKm);
}

function setRadius(km) {
  state.radiusKm = km;
  store.set("radius", String(km));
  $("radius").value = String(km);
}

function applyStaticStrings() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  $("about").textContent = t("about");
  document.querySelectorAll("[data-units]").forEach((b) => {
    b.textContent = t("units_" + b.dataset.units);
    b.setAttribute("aria-pressed", String(b.dataset.units === state.units));
  });
  document.querySelector(".seg").setAttribute("aria-label", t("units"));
  $("lang").setAttribute("aria-label", t("language"));
  $("spots-link").href = `${langHome(LANG)}spots/`;
  fillRadiusOptions();
}

function setupLangPicker() {
  const sel = $("lang");
  sel.replaceChildren(...Object.entries(LANG_NAMES).map(([code, name]) => {
    const o = document.createElement("option");
    o.value = code;
    o.textContent = name;
    o.lang = code;
    return o;
  }));
  sel.value = LANG;
  sel.addEventListener("change", () => {
    setLang(sel.value);
    store.set("lang", LANG);
    // On a language home, open the chosen language's own home (its title and link tags are in
    // its HTML); a ?lang= link just keeps its parameter in step.
    if (!params.has("lang") && (PAGE_LANG || location.pathname === "/")) {
      const qs = params.toString();
      location.assign(langHome(LANG) + (qs ? `?${qs}` : ""));
      return;
    }
    if (params.has("lang")) {
      params.set("lang", LANG);
      history.replaceState(null, "", `?${params}`);
    }
    applyStaticStrings();
    fillCityOptions();
    $("locate-msg").textContent = state.pickerMsg ? t(state.pickerMsg) : "";
    if (state.place && !$("results").hidden) render();
  });
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
async function main() {
  setLang(LANG);
  setupLangPicker();
  applyStaticStrings();
  setupCityPicker();

  $("radius").addEventListener("change", (e) => {
    setRadius(Number(e.target.value));
    render();
  });
  document.querySelectorAll("[data-units]").forEach((b) => {
    b.addEventListener("click", () => {
      state.units = b.dataset.units;
      store.set("units", state.units);
      applyStaticStrings();
      if (state.place) render();
    });
  });
  $("more").addEventListener("click", () => {
    state.showAll = true;
    render();
  });
  $("change-place").addEventListener("click", () => {
    // Keep the current place (and saved choice) until a new one is picked; Cancel goes back.
    $("city").value = "";
    showPicker(null);
    $("city").focus();
  });

  try {
    const [targets, index] = await Promise.all([getJSON("targets.json"), getJSON("index.json")]);
    state.targets = targets.targets;
    state.index = index;
  } catch (e) {
    console.error(e);
    $("status").textContent = t("load_failed");
    return;
  }
  // Famous spots are a nicety for the picker; the page works without them.
  const spots = await getJSON("spots.json").then((d) => d.spots || [], () => []);
  state.places = buildPlaces(spots);
  fillCityOptions();
  locate();
}

main();
