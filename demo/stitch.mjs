// Cuts and joins the demo with ffmpeg: one segment per scene in scenes.mjs, then crossfades.
// Inputs: out/clips.json + out/clips/*.webm (record.mjs) and out/cards/*.png (cards.mjs).
// Output: out/peak-season-demo.mp4 (1080p, 30 fps, H.264, silent stereo track for players
// that expect audio).
import { execFileSync } from "node:child_process";
import { mkdir, readFile } from "node:fs/promises";
import { SCENES, PHONE_BOX, FPS, FADE } from "./scenes.mjs";

const OUT = new URL("./out/", import.meta.url).pathname;
const SEG = `${OUT}segments/`;
const clips = JSON.parse(await readFile(`${OUT}clips.json`, "utf8"));

const ffmpeg = (args) => execFileSync("ffmpeg", ["-v", "error", "-y", ...args], { stdio: "inherit" });
const duration = (file) =>
  Number(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", file]));
const x264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-r", String(FPS)];

function cardSegment(s, file) {
  ffmpeg(["-loop", "1", "-framerate", String(FPS), "-t", String(s.seconds), "-i", `${OUT}cards/${s.id}.png`, ...x264, file]);
}

function screenSegment(s, file) {
  const clip = clips[s.clip];
  // Trim marks come from wall-clock time in record.mjs; keep them inside the actual video.
  const start = Math.max(0, clip.start);
  const end = Math.min(clip.end, duration(clip.file) - 0.05);
  const secs = (end - start).toFixed(3);
  const inputs = s.captions.flatMap((_, i) => ["-loop", "1", "-framerate", String(FPS), "-t", secs, "-i", `${OUT}cards/${s.id}-${i}.png`]);
  const v = s.captions.length; // index of the clip input
  const { x, y, width, height } = PHONE_BOX;
  const chain = [
    `[${v}:v]trim=start=${start}:end=${end},setpts=PTS-STARTPTS,fps=${FPS},scale=${width}:${height}:flags=lanczos[phone]`,
  ];
  // Later captions fade in over the first one, while the clip keeps playing underneath.
  let base = "[0:v]";
  s.captions.slice(1).forEach((c, i) => {
    chain.push(`[${i + 1}:v]format=rgba,fade=t=in:st=${c.at}:d=0.4:alpha=1[c${i + 1}]`);
    chain.push(`${base}[c${i + 1}]overlay=0:0[b${i + 1}]`);
    base = `[b${i + 1}]`;
  });
  chain.push(`${base}[phone]overlay=${x}:${y}:shortest=1,format=yuv420p[out]`);
  ffmpeg([...inputs, "-i", clip.file, "-filter_complex", chain.join(";"), "-map", "[out]", ...x264, file]);
}

await mkdir(SEG, { recursive: true });
const segments = [];
for (const s of SCENES) {
  const file = `${SEG}${s.id}.mp4`;
  if (s.kind === "card") cardSegment(s, file);
  else screenSegment(s, file);
  segments.push({ file, secs: duration(file) });
  console.log(`${s.id}: ${segments.at(-1).secs.toFixed(2)}s`);
}

// Crossfade chain: each fade starts FADE seconds before the running total ends.
const chain = [];
let prev = "[0:v]";
let total = segments[0].secs;
segments.slice(1).forEach((seg, i) => {
  const offset = (total - FADE).toFixed(3);
  chain.push(`${prev}[${i + 1}:v]xfade=transition=fade:duration=${FADE}:offset=${offset}[x${i + 1}]`);
  prev = `[x${i + 1}]`;
  total += seg.secs - FADE;
});
chain.push(`${prev}fade=t=in:st=0:d=0.6,fade=t=out:st=${(total - 0.8).toFixed(3)}:d=0.8[v]`);

const final = `${OUT}peak-season-demo.mp4`;
ffmpeg([
  ...segments.flatMap((s) => ["-i", s.file]),
  "-f", "lavfi", "-t", total.toFixed(3), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
  "-filter_complex", chain.join(";"),
  "-map", "[v]", "-map", `${segments.length}:a`,
  ...x264, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest",
  final,
]);
console.log(`${final}: ${duration(final).toFixed(1)}s`);
