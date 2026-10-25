// Renders every card and caption in scenes.mjs from HTML to 1920x1080 PNGs (out/cards/).
// Screen scenes get one PNG per caption, with an empty phone frame that stitch.mjs fills.
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import { SCENES, PHONE_BOX } from "./scenes.mjs";

const OUT = new URL("./out/cards/", import.meta.url).pathname;
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

// Colours from site/styles.css, so the video looks like the product.
const CSS = `
  * { box-sizing: border-box; margin: 0; }
  html, body { width: 1920px; height: 1080px; overflow: hidden; }
  body {
    font-family: system-ui, -apple-system, "Hiragino Sans", "Apple SD Gothic Neo", "PingFang TC", sans-serif;
    color: #1f1d1a;
    background:
      radial-gradient(1200px 800px at 85% 10%, rgba(240, 138, 93, 0.22), transparent 60%),
      radial-gradient(900px 700px at 0% 100%, rgba(63, 125, 78, 0.14), transparent 60%),
      #fbf8f3;
  }
  .eyebrow { font-size: 30px; font-weight: 600; color: #b5441b; letter-spacing: 0.01em; }
  h1 { font-size: 92px; line-height: 1.05; letter-spacing: -0.02em; font-weight: 750; }
  .body { font-size: 38px; line-height: 1.4; color: #4a453e; }
  .leaf { width: 14px; height: 14px; border-radius: 50%; display: inline-block; margin-right: 14px; vertical-align: middle; }

  .card { height: 100%; display: flex; flex-direction: column; justify-content: center; padding: 0 180px; gap: 28px; }
  .card h1 { font-size: 128px; }
  .card .body { max-width: 1300px; }

  .screen { position: relative; height: 100%; }
  .phone {
    position: absolute; left: ${PHONE_BOX.x - 20}px; top: ${PHONE_BOX.y - 20}px;
    width: ${PHONE_BOX.width + 40}px; height: ${PHONE_BOX.height + 40}px;
    background: #1f1d1a; border-radius: 52px; box-shadow: 0 40px 80px rgba(31, 29, 26, 0.28);
  }
  .caption {
    position: absolute; left: 820px; right: 140px; top: 0; bottom: 0;
    display: flex; flex-direction: column; justify-content: center; gap: 26px;
  }

  .flow { display: flex; align-items: stretch; gap: 0; margin: 20px 0 10px; }
  .step { flex: 1; background: #fff; border: 2px solid #e6e0d6; border-radius: 22px; padding: 30px 32px; }
  .step b { display: block; font-size: 38px; margin-bottom: 8px; }
  .step span { font-size: 28px; color: #6a645b; line-height: 1.35; }
  .arrow { align-self: center; font-size: 56px; color: #b5441b; padding: 0 22px; }
  .play {
    position: absolute; right: 200px; top: 50%; transform: translateY(-50%);
    width: 220px; height: 220px; border-radius: 50%; background: #b5441b;
    box-shadow: 0 30px 60px rgba(181, 68, 27, 0.35);
  }
  .play::after {
    content: ""; position: absolute; left: 86px; top: 62px;
    border-left: 78px solid #fff; border-top: 48px solid transparent; border-bottom: 48px solid transparent;
  }
  .links { display: grid; gap: 14px; font-size: 44px; font-weight: 600; color: #b5441b; margin-top: 16px; }
`;

const leaves = `<span class="leaf" style="background:#c2410c"></span>`;

function cardHtml(s) {
  const flow = s.flow
    ? `<div class="flow">${s.flow
        .map(([b, sub]) => `<div class="step"><b>${esc(b)}</b><span>${esc(sub)}</span></div>`)
        .join('<div class="arrow">→</div>')}</div>`
    : "";
  const links = s.links ? `<div class="links">${s.links.map((l) => `<div>${esc(l)}</div>`).join("")}</div>` : "";
  return `<div class="card">
    <div class="eyebrow">${leaves}${esc(s.eyebrow)}</div>
    <h1>${esc(s.title)}</h1>
    ${flow}
    ${s.body ? `<p class="body">${esc(s.body)}</p>` : ""}
    ${links}
  </div>`;
}

function screenHtml(c) {
  return `<div class="screen">
    <div class="phone"></div>
    <div class="caption">
      <div class="eyebrow">${leaves}${esc(c.eyebrow)}</div>
      <h1>${esc(c.title)}</h1>
      <p class="body">${esc(c.body)}</p>
    </div>
  </div>`;
}

await mkdir(OUT, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const render = async (html, file) => {
  await page.setContent(`<!doctype html><meta charset="utf-8"><style>${CSS}</style>${html}`);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: `${OUT}${file}` });
  console.log(file);
};
// README poster: the title card with a play button (GitHub can't embed a player).
const title = SCENES.find((s) => s.id === "title");
await render(`${cardHtml(title)}<div class="play"></div>`, "poster.png");
for (const s of SCENES) {
  if (s.kind === "card") await render(cardHtml(s), `${s.id}.png`);
  else for (const [i, c] of s.captions.entries()) await render(screenHtml(c), `${s.id}-${i}.png`);
}
await browser.close();
