// The demo's storyboard: shared by cards.mjs (renders the text) and stitch.mjs (cuts the video).
// A "card" is a full-screen title card. A "screen" is a recorded clip in a phone frame, with one
// or more captions beside it; `at` is seconds into the scene when that caption takes over.

export const SCENES = [
  {
    id: "title",
    kind: "card",
    seconds: 4,
    eyebrow: "Autumn leaves · cherry blossoms · anywhere in the world",
    title: "Peak Season",
    body: "Where nature is at its peak near you, right now.",
  },
  {
    id: "toronto",
    kind: "screen",
    clip: "toronto",
    captions: [
      {
        at: 0,
        eyebrow: "Toronto · location on",
        title: "One answer: where to go now",
        body: "The closest place at its peak, how fresh the reports are, and directions in your own map app.",
      },
      {
        at: 5.5,
        eyebrow: "Every call has evidence",
        title: "Real photos, credited and linked",
        body: "Each stage comes from recent iNaturalist photos checked by Gemma. Shown with the photographer's licence, linked to the original, never rehosted.",
      },
    ],
  },
  {
    id: "tokyo",
    kind: "screen",
    clip: "tokyo",
    captions: [
      {
        at: 0,
        eyebrow: "Tokyo · 日本語",
        title: "Gemma reads the news, in any language",
        body: "Japanese news of a rare autumn cherry bloom at Ueno Park, found with SerpApi and read by Gemma. The page also speaks 한국어 and 繁體中文.",
      },
    ],
  },
  {
    id: "widen",
    kind: "screen",
    clip: "widen",
    captions: [
      {
        at: 0,
        eyebrow: "Kyoto · no dead ends",
        title: "No peak nearby? It finds the closest",
        body: "Too few reports to judge means no status, never a guess. Instead it names the closest peak and widens the search in one tap.",
      },
    ],
  },
  {
    id: "how",
    kind: "card",
    seconds: 8,
    eyebrow: "How it works",
    title: "Open-weight AI. $0 a month.",
    flow: [
      ["iNaturalist photos", "+ web reports via SerpApi"],
      ["Gemma, open-weight", "on a free GitHub Actions runner, twice a day"],
      ["Static JSON", "served by Cloudflare Pages"],
    ],
    body: "No server, no per-image cost, photos never sent to a closed AI API. A new plant is one YAML file and a prompt.",
  },
  {
    id: "end",
    kind: "card",
    seconds: 5,
    eyebrow: "Go outside.",
    title: "Peak Season",
    links: ["peak-season-dvl.pages.dev", "github.com/klee1611/peak-season"],
  },
];

// Layout of a screen scene at 1920x1080: the clip is scaled into this box inside a phone frame.
export const PHONE_BOX = { x: 250, y: 70, width: 434, height: 940 };
export const FPS = 30;
export const FADE = 0.5; // seconds of crossfade between scenes
