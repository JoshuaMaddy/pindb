/** One-off: print suggested hsl(L%) for semantic muted text ramp per theme. Run from repo root. */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const INPUT = join(__dirname, "..", "src", "pindb", "static", "input.css");

function extractBalancedBlock(css, openBraceIndex) {
  let depth = 0;
  for (let k = openBraceIndex; k < css.length; k++) {
    if (css[k] === "{") depth++;
    else if (css[k] === "}") {
      depth--;
      if (depth === 0) return css.slice(openBraceIndex + 1, k);
    }
  }
  return null;
}

function parseVariants(css) {
  const layerIdx = css.indexOf("@layer theme");
  const search = layerIdx >= 0 ? css.slice(layerIdx) : css;
  const re = /@variant\s+([\w-]+)\s*\{/g;
  const out = [];
  let m;
  while ((m = re.exec(search)) !== null) {
    const open = layerIdx + m.index + m[0].length - 1;
    const body = extractBalancedBlock(css, open);
    if (body) out.push({ name: m[1], body });
  }
  return out;
}

function parsePinColorDeclarations(block) {
  const vars = {};
  const declRe = /--color-([\w-]+)\s*:\s*([^;]+);/g;
  let m;
  while ((m = declRe.exec(block)) !== null) {
    vars[m[1]] = m[2].trim();
  }
  return vars;
}

function resolveVars(rawMap) {
  const map = { ...rawMap };
  for (let r = 0; r < 20; r++) {
    let changed = false;
    for (const [key, val] of Object.entries(map)) {
      const m = val.match(/^var\(\s*--color-([\w-]+)\s*\)$/i);
      if (m && map[m[1]] && !map[m[1]].startsWith("var(")) {
        map[key] = map[m[1]];
        changed = true;
      }
    }
    if (!changed) break;
  }
  return map;
}

function parseHsl(raw) {
  const s = raw.replace(/\/\*[\s\S]*?\*\//g, "").trim();
  const m = s.match(
    /hsl\(\s*([0-9.]+)\s*(?:deg)?\s*,\s*([0-9.]+)\s*%\s*,\s*([0-9.]+)\s*%\s*\)/i,
  );
  if (!m) return null;
  return { h: Number(m[1]), s: Number(m[2]), l: Number(m[3]) };
}

function hslToRgb(h, sat, light) {
  h /= 360;
  const s = sat / 100;
  const l = light / 100;
  if (s === 0) {
    const v = Math.round(l * 255);
    return [v, v, v];
  }
  const hue2rgb = (p, q, t) => {
    let tt = t;
    if (tt < 0) tt += 1;
    if (tt > 1) tt -= 1;
    if (tt < 1 / 6) return p + (q - p) * 6 * tt;
    if (tt < 1 / 2) return q;
    if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6;
    return p;
  };
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  return [
    Math.round(Math.min(255, Math.max(0, hue2rgb(p, q, h + 1 / 3) * 255))),
    Math.round(Math.min(255, Math.max(0, hue2rgb(p, q, h) * 255))),
    Math.round(Math.min(255, Math.max(0, hue2rgb(p, q, h - 1 / 3) * 255))),
  ];
}

function srgbToLinear(c) {
  const x = c / 255;
  return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
}

function luminance(rgb) {
  const [r, g, b] = rgb.map(srgbToLinear);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(a, b) {
  const L1 = luminance(a);
  const L2 = luminance(b);
  return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
}

const CHROME = [
  "darker",
  "darker-hover",
  "main",
  "main-hover",
  "lighter",
  "lighter-hover",
];
const FG = ["base-text", "accent"];

function rgbMapFromRaw(raw) {
  const resolved = resolveVars(raw);
  const rgb = {};
  for (const [k, v] of Object.entries(resolved)) {
    if (v.startsWith("var(")) continue;
    const p = parseHsl(v);
    if (p) rgb[k] = hslToRgb(p.h, p.s, p.l);
  }
  return rgb;
}

function minContrastOnChrome(rgbMap) {
  let min = 99;
  for (const bg of CHROME) {
    const b = rgbMap[bg];
    if (!b) continue;
    for (const fg of FG) {
      const f = rgbMap[fg];
      if (!f) continue;
      min = Math.min(min, contrastRatio(b, f));
    }
  }
  return min;
}

function tuneSingle(raw, key) {
  const isLight = (() => {
    const m = resolveVars(raw);
    const p500 = parseHsl(m.main);
    return p500 && p500.l >= 50;
  })();

  const rawCopy = { ...raw };

  for (let step = 0; step < 200; step++) {
    const rgbMap = rgbMapFromRaw(rawCopy);
    if (minContrastOnChrome(rgbMap) >= 4.5) {
      return { [key]: rawCopy[key] };
    }
    const parsed = parseHsl(rawCopy[key]);
    if (!parsed) return null;
    if (isLight) {
      parsed.l = Math.max(8, parsed.l - 0.6);
    } else {
      parsed.l = Math.min(88, parsed.l + 0.6);
    }
    rawCopy[key] = `hsl(${parsed.h}deg, ${parsed.s}%, ${parsed.l}%)`;
  }
  return null;
}

const css = readFileSync(INPUT, "utf8");
const themeBlock = (() => {
  const i = css.indexOf("@theme");
  const b = css.indexOf("{", i);
  return extractBalancedBlock(css, b);
})();
const variants = parseVariants(css);
const mochaRaw = parsePinColorDeclarations(themeBlock);
const themes = [{ name: "mocha", raw: mochaRaw }];
for (const { name, body } of variants) {
  themes.push({
    name,
    raw: { ...mochaRaw, ...parsePinColorDeclarations(body) },
  });
}

for (const { name, raw } of themes) {
  const out = tuneSingle(raw, "base-text");
  console.log(`\n## ${name}`);
  if (!out) {
    console.log("FAILED to converge");
    continue;
  }
  console.log(`base-text: ${out["base-text"]}`);
}
