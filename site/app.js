// Peak Season site: static, no framework, no third-party scripts.
// Loads only the user's regional shard (plus neighbours) and renders place cards.
"use strict";

// ---------------------------------------------------------------------------
// Strings. Every user-visible string lives here so translations can be added later.
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
  },
};
const LANG = "en";
const PLURALS = new Intl.PluralRules(LANG);

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
const RTF = new Intl.RelativeTimeFormat(LANG, { numeric: "auto" });

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
const CITIES = [
  ["Toronto", 43.6532, -79.3832],
  ["New York", 40.7128, -74.006],
  ["Vancouver", 49.2827, -123.1207],
  ["London", 51.5074, -0.1278],
  ["Paris", 48.8566, 2.3522],
  ["Tokyo", 35.6762, 139.6503],
  ["Kyoto", 35.0116, 135.7681],
  ["Seoul", 37.5665, 126.978],
  ["Taipei", 25.033, 121.5654],
  ["Sydney", -33.8688, 151.2093],
  ["Melbourne", -37.8136, 144.9631],
];

const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
};

const params = new URLSearchParams(location.search);
const DATA = params.has("fixtures") ? "data/fixtures/" : "data/";
const SHOW_UNVALIDATED = params.has("all"); // dev only: show targets not yet validated

const state = {
  targets: [],
  index: null,
  place: null, // {lat, lng, label}
  cells: {}, // target id -> [cell with distanceKm]
  target: null,
  radiusKm: Number(store.get("radius")) || 100,
  units: store.get("units") === "mi" ? "mi" : "km",
  chosenTarget: false,
  showAll: false,
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
function setupCityPicker() {
  const sel = $("city");
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "—";
  sel.append(blank);
  CITIES.forEach(([name], i) => {
    const o = document.createElement("option");
    o.value = String(i);
    o.textContent = name;
    sel.append(o);
  });
  sel.addEventListener("change", () => {
    const c = CITIES[Number(sel.value)];
    if (!sel.value || !c) return;
    store.set("city", c[0]);
    useLocation({ lat: c[1], lng: c[2], label: c[0] });
  });
  $("use-location").addEventListener("click", () => locate(true));
}

function showPicker(msgKey) {
  $("locate").hidden = false;
  $("locate-msg").textContent = msgKey ? t(msgKey) : "";
  $("status").textContent = "";
}

function locate(force = false) {
  const lat = parseFloat(params.get("lat")), lng = parseFloat(params.get("lng"));
  if (!force && Number.isFinite(lat) && Number.isFinite(lng)) {
    return useLocation({ lat, lng, label: t("your_location") });
  }
  const saved = CITIES.find((c) => c[0] === store.get("city"));
  if (!force && saved) return useLocation({ lat: saved[1], lng: saved[2], label: saved[0] });
  if (!("geolocation" in navigator)) return showPicker("location_failed");

  $("status").textContent = t("locating");
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      store.set("city", "");
      useLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude, label: t("your_location") });
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
    b.textContent = tg.display_name;
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
      stage: stageInfo(target, best.stage).label,
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
    stage: stageInfo(target, closest.stage).label,
  });
}

function nothingNearbyText() {
  const base = t("nothing_nearby", { radius: fmtDistance(state.radiusKm), place: state.place.label });
  const names = new Map(visibleTargets().map((tg) => [tg.id, tg.display_name]));
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
  return `${base} ${tail}`;
}

function renderCard(target, c) {
  const li = $("card-tpl").content.firstElementChild.cloneNode(true);
  const stage = stageInfo(target, c.stage);
  li.querySelector(".place").textContent = c.name || `${c.lat}, ${c.lng}`;

  const badge = li.querySelector(".badge");
  badge.textContent = stage ? stage.label : t("not_enough_reports");
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
  $("units").textContent = state.units === "km" ? "km → mi" : "mi → km";
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
async function main() {
  document.documentElement.lang = LANG;
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
