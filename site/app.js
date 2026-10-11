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
    locating: "Finding your location…",
    loading: "Loading reports…",
    pick_city: "Or pick a city:",
    use_my_location: "Use my location",
    location_declined: "Location is off. Pick a city to see what's in season near it.",
    location_failed: "Couldn't get your location. Pick a city instead.",
    change_place: "Change place",
    within: "Within",
    units_km: "km",
    units_mi: "mi",
    load_failed: "Couldn't load the data. Please try again later.",
    nothing_nearby: "Nothing in season within {radius} of {place} right now.",
    nearest_region: "The nearest region with something at its peak: {plant}, about {distance} away.",
    nearest_in_season: "The nearest region where it's in season: {plant}, about {distance} away.",
    nearest_none: "Nothing is in season anywhere we track right now.",
    your_location: "you",
    go_now_line: "{stage} {distance} away at {name}. {reports}. {advice}",
    best_line: "Nothing at its best nearby yet. Closest: {name}, {distance} away ({stage}).",
    go_weekend: "Go this weekend.",
    worth_a_look: "Worth a look.",
    reports_count: "{count, plural, one {# report} other {# reports}}",
    reports_recent: "{reports}, newest {ago}",
    not_enough_reports: "Not enough reports",
    in_season_hint: "{count, plural, one {# sighting} other {# sightings}} this week",
    from_source: "Photo",
    see_original: "See original",
    famous_spot: "Famous spot",
    show_more: "{count, plural, one {Show # more place} other {Show # more places}}",
    updated: "Last updated {ago}.",
    about:
      "Reports come from iNaturalist and the web, checked by Gemma, an open-weight AI model, running on a free GitHub Actions runner. Photos stay with their owners; we only link to them.",
    language: "Language",
    sentence_gap: " ",
  },
  ja: {
    tagline: "近くで今いちばん見頃の自然を。",
    locating: "現在地を取得しています…",
    loading: "レポートを読み込んでいます…",
    pick_city: "または都市を選んでください：",
    use_my_location: "現在地を使う",
    location_declined: "位置情報がオフです。都市を選ぶと、その近くで今シーズン中のものがわかります。",
    location_failed: "現在地を取得できませんでした。都市を選んでください。",
    change_place: "場所を変更",
    within: "半径",
    units_km: "km",
    units_mi: "マイル",
    load_failed: "データを読み込めませんでした。しばらくしてからもう一度お試しください。",
    nothing_nearby: "{place}から{radius}以内に、今シーズン中のものはありません。",
    nearest_region: "見頃のものがある最寄りの地域：{plant}、約{distance}先。",
    nearest_in_season: "シーズン中の最寄りの地域：{plant}、約{distance}先。",
    nearest_none: "現在、追跡しているどの地域にもシーズン中のものはありません。",
    your_location: "現在地",
    go_now_line: "{distance}先の{name}が{stage}です。{reports}。{advice}",
    best_line: "近くにはまだ見頃の場所はありません。最寄り：{name}（{distance}先、{stage}）。",
    go_weekend: "今週末に行きましょう。",
    worth_a_look: "行ってみる価値があります。",
    reports_count: "レポート{count}件",
    reports_recent: "{reports}、最新は{ago}",
    not_enough_reports: "レポート不足",
    in_season_hint: "今週の観察{count}件",
    from_source: "写真",
    see_original: "元の投稿",
    famous_spot: "名所",
    show_more: "さらに{count}か所を表示",
    updated: "最終更新：{ago}。",
    about:
      "レポートは iNaturalist とウェブから集め、無料の GitHub Actions ランナー上で動くオープンウェイトAIモデル Gemma が確認しています。写真は撮影者のもので、ここではリンクのみ表示しています。",
    language: "言語",
    sentence_gap: "",
  },
  ko: {
    tagline: "지금 내 주변에서 자연이 가장 아름다운 곳.",
    locating: "위치를 찾는 중…",
    loading: "제보를 불러오는 중…",
    pick_city: "또는 도시를 선택하세요:",
    use_my_location: "내 위치 사용",
    location_declined: "위치 정보가 꺼져 있습니다. 도시를 선택하면 근처의 제철 풍경을 볼 수 있어요.",
    location_failed: "위치를 가져올 수 없습니다. 도시를 선택해 주세요.",
    change_place: "장소 변경",
    within: "반경",
    units_km: "km",
    units_mi: "마일",
    load_failed: "데이터를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.",
    nothing_nearby: "지금 {place} 반경 {radius} 안에는 제철인 것이 없습니다.",
    nearest_region: "절정인 곳이 있는 가장 가까운 지역: {plant}, 약 {distance} 거리.",
    nearest_in_season: "제철인 가장 가까운 지역: {plant}, 약 {distance} 거리.",
    nearest_none: "지금은 추적 중인 어느 지역에도 제철인 것이 없습니다.",
    your_location: "내 위치",
    go_now_line: "{distance} 거리의 {name}: {stage}. {reports}. {advice}",
    best_line: "근처에는 아직 절정인 곳이 없습니다. 가장 가까운 곳: {name}, {distance} 거리 ({stage}).",
    go_weekend: "이번 주말에 가 보세요.",
    worth_a_look: "가 볼 만합니다.",
    reports_count: "제보 {count}건",
    reports_recent: "{reports}, 최신 {ago}",
    not_enough_reports: "제보 부족",
    in_season_hint: "이번 주 관찰 {count}건",
    from_source: "사진",
    see_original: "원본 보기",
    famous_spot: "명소",
    show_more: "{count}곳 더 보기",
    updated: "마지막 업데이트: {ago}.",
    about:
      "제보는 iNaturalist와 웹에서 모으며, 무료 GitHub Actions 러너에서 실행되는 오픈 웨이트 AI 모델 Gemma가 확인합니다. 사진은 원작자의 것이며, 여기서는 링크만 제공합니다.",
    language: "언어",
    sentence_gap: " ",
  },
  "zh-TW": {
    tagline: "現在，你附近哪裡的自然景色正值最美。",
    locating: "正在取得你的位置…",
    loading: "正在載入回報…",
    pick_city: "或選擇城市：",
    use_my_location: "使用我的位置",
    location_declined: "位置功能已關閉。選擇一個城市，看看附近有什麼正當季。",
    location_failed: "無法取得你的位置，請改選城市。",
    change_place: "更換地點",
    within: "半徑",
    units_km: "公里",
    units_mi: "英里",
    load_failed: "無法載入資料，請稍後再試。",
    nothing_nearby: "目前{place}方圓{radius}內沒有正當季的景色。",
    nearest_region: "最近有景色正值最佳時期的地區：{plant}，約{distance}外。",
    nearest_in_season: "最近正當季的地區：{plant}，約{distance}外。",
    nearest_none: "目前我們追蹤的地區都沒有正當季的景色。",
    your_location: "你的位置",
    go_now_line: "{distance}外的{name}：{stage}。{reports}。{advice}",
    best_line: "附近還沒有正值最佳時期的地點。最近的是{name}，{distance}外（{stage}）。",
    go_weekend: "這個週末就去吧。",
    worth_a_look: "值得去看看。",
    reports_count: "{count} 則回報",
    reports_recent: "{reports}，最新一則{ago}",
    not_enough_reports: "回報不足",
    in_season_hint: "本週 {count} 筆觀察",
    from_source: "照片",
    see_original: "查看原文",
    famous_spot: "知名景點",
    show_more: "再顯示 {count} 個地點",
    updated: "最後更新：{ago}。",
    about:
      "回報來自 iNaturalist 與網路，由在免費 GitHub Actions 執行器上運行的開放權重 AI 模型 Gemma 檢查。照片屬於原作者，我們只提供連結。",
    language: "語言",
    sentence_gap: "",
  },
};
// Language names shown in the picker, each in its own language.
const LANG_NAMES = { en: "English", ja: "日本語", ko: "한국어", "zh-TW": "繁體中文" };

/** ?lang= first, then the viewer's saved choice, then the browser's preferred languages. */
function pickLang() {
  const wanted = [new URLSearchParams(location.search).get("lang"), safeGet("lang"), ...(navigator.languages || [])];
  for (const tag of wanted) {
    if (!tag) continue;
    if (tag in I18N) return tag;
    const base = tag.toLowerCase().split("-")[0];
    if (base === "zh") return "zh-TW"; // the only Chinese UI so far
    if (base in I18N) return base;
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
  let s = (I18N[LANG] && I18N[LANG][key]) ?? I18N.en[key] ?? key;
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

const store = {
  get: safeGet,
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
};

const params = new URLSearchParams(location.search);
const DATA = params.has("fixtures") ? "data/fixtures/" : "data/";
const SHOW_UNVALIDATED = params.has("all"); // dev only: show targets not yet validated

const state = {
  targets: [],
  index: null,
  place: null, // {lat, lng, city: CITIES entry or null for "your location"}
  cells: {}, // target id -> [cell with distanceKm]
  target: null,
  radiusKm: Number(store.get("radius")) || 100,
  units: store.get("units") === "mi" ? "mi" : "km",
  chosenTarget: false,
  showAll: false,
  pickerMsg: null,
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
const cityName = (c) => c[3]?.[LANG] || c[0];
const targetName = (tg) => tg.local_names?.[LANG] || tg.display_name;
const stageLabel = (stage) => stage.local_labels?.[LANG] || stage.label;
// The place's label is worked out at render time so it follows a language change.
const placeLabel = (place) => (place.city ? cityName(place.city) : t("your_location"));

function fillCityOptions() {
  const sel = $("city");
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "—";
  const options = CITIES.map((c, i) => {
    const o = document.createElement("option");
    o.value = String(i);
    o.textContent = cityName(c);
    return o;
  });
  const chosen = sel.value;
  sel.replaceChildren(blank, ...options);
  sel.value = chosen;
}

function setupCityPicker() {
  const sel = $("city");
  fillCityOptions();
  sel.addEventListener("change", () => {
    const c = CITIES[Number(sel.value)];
    if (!sel.value || !c) return;
    store.set("city", c[0]);
    useLocation({ lat: c[1], lng: c[2], city: c });
  });
  $("use-location").addEventListener("click", () => locate(true));
}

function showPicker(msgKey) {
  $("locate").hidden = false;
  state.pickerMsg = msgKey;
  $("locate-msg").textContent = msgKey ? t(msgKey) : "";
  $("status").textContent = "";
}

function locate(force = false) {
  const lat = parseFloat(params.get("lat")), lng = parseFloat(params.get("lng"));
  if (!force && Number.isFinite(lat) && Number.isFinite(lng)) {
    return useLocation({ lat, lng, city: null });
  }
  const saved = CITIES.find((c) => c[0] === store.get("city"));
  if (!force && saved) return useLocation({ lat: saved[1], lng: saved[2], city: saved });
  if (!("geolocation" in navigator)) return showPicker("location_failed");

  $("status").textContent = t("locating");
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      store.set("city", "");
      useLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude, city: null });
    },
    (err) => showPicker(err.code === err.PERMISSION_DENIED ? "location_declined" : "location_failed"),
    { timeout: 8000, maximumAge: 30 * 60 * 1000 },
  );
}

async function useLocation(place) {
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
        (cells[tid] ||= []).push({ ...c, distanceKm: haversineKm(lat, lng, c.lat, c.lng) });
      }
    }
  }
  state.cells = cells;
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

function sortCells(target, cells) {
  // go_now first, then further-along stages, then "not enough reports"; ties by distance.
  const rank = (c) => {
    const s = stageInfo(target, c.stage);
    if (!s) return 1000;
    return s.go_now ? -1 : target.stages.length - s.index;
  };
  return [...cells].sort((a, b) => rank(a) - rank(b) || a.distanceKm - b.distanceKm);
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------
function render() {
  const targets = visibleTargets().filter((tg) => nearbyCells(tg.id).length > 0);
  $("results").hidden = false;
  renderChips(targets);

  if (targets.length === 0) {
    state.target = null;
    $("cards").replaceChildren();
    $("headline").textContent = nothingNearbyText();
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
  // Keep the page short: the best few places first, the rest one tap away.
  const shown = state.showAll ? cells : cells.slice(0, MAX_CARDS);
  $("cards").replaceChildren(...shown.map((c) => renderCard(state.target, c)));
  const more = $("more");
  more.hidden = shown.length === cells.length;
  more.textContent = t("show_more", { count: cells.length - shown.length });
}

function renderChips(targets) {
  const box = $("chips");
  box.replaceChildren();
  box.hidden = targets.length === 0;
  for (const tg of targets) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.setAttribute("role", "tab");
    b.setAttribute("aria-selected", String(tg.id === state.target?.id));
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

function headlineText(target, cells) {
  const best = cells.find((c) => isGoNow(target, c));
  if (best) {
    const fresh = Date.now() - new Date(best.latest_report_at).getTime() < 3 * 86400 * 1000;
    return t("go_now_line", {
      stage: stageLabel(stageInfo(target, best.stage)),
      distance: fmtDistance(best.distanceKm),
      name: best.name || "",
      reports: t("reports_recent", {
        reports: t("reports_count", { count: best.report_count }),
        ago: timeAgo(best.latest_report_at),
      }),
      advice: t(fresh ? "go_weekend" : "worth_a_look"),
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

function nothingNearbyText() {
  const base = t("nothing_nearby", { radius: fmtDistance(state.radiusKm), place: placeLabel(state.place) });
  const names = new Map(visibleTargets().map((tg) => [tg.id, targetName(tg)]));
  const nearest = (field) => {
    let best = null;
    for (const [hash, info] of Object.entries(state.index.shards)) {
      const ids = (info[field] || []).filter((id) => names.has(id));
      if (ids.length === 0) continue;
      const [lat, lng] = geohashCentre(hash);
      const d = haversineKm(state.place.lat, state.place.lng, lat, lng);
      if (!best || d < best.d) best = { d, plant: names.get(ids[0]) };
    }
    return best;
  };
  // Region centres are approximate (a region is ~1,250 km wide), so round generously.
  const say = (key, best) =>
    t(key, { plant: best.plant, distance: fmtDistance(Math.max(100, Math.round(best.d / 100) * 100)) });
  const peak = nearest("go_now");
  const season = peak ? null : nearest("in_season");
  const tail = peak ? say("nearest_region", peak) : season ? say("nearest_in_season", season) : t("nearest_none");
  return base + t("sentence_gap") + tail;
}

function renderCard(target, c) {
  const li = $("card-tpl").content.firstElementChild.cloneNode(true);
  const stage = stageInfo(target, c.stage);
  li.querySelector(".place").textContent = c.name || `${c.lat}, ${c.lng}`;

  const badge = li.querySelector(".badge");
  badge.textContent = stage ? stageLabel(stage) : t("not_enough_reports");
  badge.dataset.stage = stage ? (stage.go_now ? "go" : `s${stage.index}`) : "none";
  if (stage) badge.style.setProperty("--progress", String(stage.index / Math.max(1, target.stages.length - 1)));

  const bits = [fmtDistance(c.distanceKm)];
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

  const photo = (c.evidence || []).find((e) => e.thumb);
  if (photo) {
    const fig = li.querySelector(".evidence");
    fig.hidden = false;
    li.querySelector(".evidence-link").href = photo.link;
    li.querySelector("img").src = photo.thumb;
    li.querySelector("figcaption").textContent = photo.attribution || "";
  }

  const sources = li.querySelector(".sources");
  (c.evidence || []).forEach((e, i) => {
    const a = document.createElement("a");
    a.href = e.link;
    a.rel = "noopener";
    a.target = "_blank";
    a.textContent = `${t("see_original")} ${i + 1}`;
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

function applyStaticStrings() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  $("about").textContent = t("about");
  $("units").textContent =
    state.units === "km" ? `${t("units_km")} → ${t("units_mi")}` : `${t("units_mi")} → ${t("units_km")}`;
  $("lang").setAttribute("aria-label", t("language"));
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
    // Keep a shared ?lang= link in step with the choice.
    if (params.has("lang")) {
      params.set("lang", LANG);
      history.replaceState(null, "", `?${params}`);
    }
    applyStaticStrings();
    fillCityOptions();
    renderUpdated();
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

  $("radius").value = String(state.radiusKm);
  $("radius").addEventListener("change", (e) => {
    state.radiusKm = Number(e.target.value);
    store.set("radius", e.target.value);
    render();
  });
  $("units").addEventListener("click", () => {
    state.units = state.units === "km" ? "mi" : "km";
    store.set("units", state.units);
    applyStaticStrings();
    render();
  });
  $("more").addEventListener("click", () => {
    state.showAll = true;
    render();
  });
  $("change-place").addEventListener("click", () => {
    store.set("city", "");
    $("city").value = "";
    showPicker(null);
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
  renderUpdated();
  locate();
}

main();
