// Records the demo's screen clips from the live site with Playwright.
// Each scene gets its own browser context (a first visit, no saved place) and its own video.
// Writes out/clips/<scene>.webm plus out/clips.json with the trim points for stitch.mjs.
import { chromium } from "playwright";
import { mkdir, rename, writeFile } from "node:fs/promises";

const BASE = process.env.DEMO_URL || "https://peak-season-dvl.pages.dev";
const OUT = new URL("./out/clips/", import.meta.url).pathname;
// Playwright's video does not upscale for deviceScaleFactor (the page lands in the top-left
// quarter of the frame), so record a 2x window and zoom the page 2x: phone layout, sharp text.
const PHONE = { width: 390, height: 844 };
const ZOOM = 2;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** A visible tap marker, so viewers can see what was touched. */
async function tap(page, locator, { click = true } = {}) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  // boundingBox is in window pixels; the marker lives inside the zoomed page.
  await page.evaluate(({ x, y }) => {
    const dot = document.createElement("div");
    Object.assign(dot.style, {
      position: "fixed", left: `${x - 22}px`, top: `${y - 22}px`, width: "44px", height: "44px",
      borderRadius: "50%", background: "rgba(181, 68, 27, 0.35)", border: "2px solid rgba(181, 68, 27, 0.8)",
      zIndex: 99999, pointerEvents: "none",
    });
    document.body.append(dot);
    dot.animate([{ transform: "scale(0.6)", opacity: 1 }, { transform: "scale(1.4)", opacity: 0 }],
      { duration: 700, easing: "ease-out" }).onfinish = () => dot.remove();
  }, { x: (box.x + box.width / 2) / ZOOM, y: (box.y + box.height / 2) / ZOOM });
  await sleep(250);
  if (click) await locator.click();
}

async function scrollBy(page, dy, ms = 1200) {
  await page.evaluate((dy) => window.scrollBy({ top: dy, behavior: "smooth" }), dy);
  await sleep(ms);
}

const SCENES = {
  // Location allowed: straight to the answer, then the cards with their credited photos.
  async toronto(page, mark) {
    await page.goto(`${BASE}/`);
    mark("start");
    await page.locator("#cards li").first().waitFor();
    await sleep(4000);
    await scrollBy(page, 330);
    await sleep(2500);
    await scrollBy(page, 520);
    await sleep(2000);
    mark("end");
  },

  // Japanese UI, Tokyo picked from the list: Gemma's reading of Japanese news reports.
  async tokyo(page, mark) {
    await page.goto(`${BASE}/ja/`);
    await page.locator("#city").waitFor();
    await page.locator('#city option[value="Tokyo"]').waitFor({ state: "attached" });
    mark("start");
    await sleep(1800);
    await tap(page, page.locator("#city"), { click: false });
    await page.selectOption("#city", "Tokyo");
    await page.locator("#cards li").first().waitFor();
    await sleep(4500);
    await scrollBy(page, 360);
    await sleep(3000);
    mark("end");
  },

  // Nowhere nearby at its peak: the page names the closest one and widens in one tap.
  async widen(page, mark) {
    await page.goto(`${BASE}/`);
    await page.locator('#city option[value="Kyoto"]').waitFor({ state: "attached" });
    mark("start");
    await sleep(1200);
    await tap(page, page.locator("#city"), { click: false });
    await page.selectOption("#city", "Kyoto");
    await page.locator("#headline").filter({ hasText: /\S/ }).waitFor();
    await sleep(4000);
    const widen = page.locator("#widen");
    if (await widen.isVisible()) {
      await tap(page, widen);
      await sleep(4000);
    } else {
      console.warn("widen: no widen button for Kyoto with today's data");
    }
    mark("end");
  },
};

const GEO = { toronto: { latitude: 43.6532, longitude: -79.3832 } };

await mkdir(OUT, { recursive: true });
const browser = await chromium.launch();
const clips = {};
for (const [name, run] of Object.entries(process.argv.length > 2 ? Object.fromEntries(
  Object.entries(SCENES).filter(([n]) => process.argv.includes(n))) : SCENES)) {
  const size = { width: PHONE.width * ZOOM, height: PHONE.height * ZOOM };
  const context = await browser.newContext({
    viewport: size,
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
    colorScheme: "light",
    // The tap marker is injected from here; the site's own CSP stays as deployed.
    bypassCSP: true,
    ...(GEO[name] ? { geolocation: GEO[name], permissions: ["geolocation"] } : {}),
    recordVideo: { dir: OUT, size },
  });
  await context.addInitScript((zoom) => {
    document.addEventListener("DOMContentLoaded", () => { document.documentElement.style.zoom = String(zoom); });
  }, ZOOM);
  const t0 = Date.now(); // the video starts when the page is created
  const page = await context.newPage();
  const marks = {};
  await run(page, (label) => { marks[label] = (Date.now() - t0) / 1000; });
  const video = page.video();
  await context.close();
  const file = `${OUT}${name}.webm`;
  await rename(await video.path(), file);
  clips[name] = { file, ...marks };
  console.log(`${name}: ${marks.start.toFixed(2)}s -> ${marks.end.toFixed(2)}s`);
}
await browser.close();
await writeFile(new URL("./out/clips.json", import.meta.url), JSON.stringify(clips, null, 2));
