/**
 * WCAG 2.1 contrast matrix for PinDB theme tokens in src/pindb/static/input.css.
 * Resolves --color-pin-* per theme (mocha = @theme defaults + variant overlays).
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const INPUT_CSS = join(__dirname, "..", "src", "pindb", "static", "input.css");
const MIN_RATIO = Number(process.env.PIN_CONTRAST_MIN ?? "4.5");
/** `full` = every surface × every text token (strict). `semantic` = documented pairings (default). */
const MATRIX = process.env.PIN_CONTRAST_MATRIX ?? "semantic";

function belowMin(ratio, min) {
  return ratio + 1e-3 < min;
}

/** Surfaces that commonly sit behind body copy or controls. */
const SURFACE_KEYS = [
  "main",
  "main-hover",
  "pin-base-550",
  "pin-base-500",
  "pin-base-450",
  "pin-base-400",
];

const TEXT_KEYS = [
  "pin-base-text",
  "pin-base-100",
  "pin-base-150",
  "pin-base-200",
  "pin-base-250",
  "pin-base-300",
];

/**
 * Semantic checks (WCAG AA 4.5:1 for normal text):
 * - Full neutral ramp on primary shell: main, base-500, base-550 (typical body + muted).
 * - Hover and input surfaces (main-hover, base-450): text through base-200 only
 *   (controls rarely use base-250/300 as foreground on these).
 *
 * Use `PIN_CONTRAST_MATRIX=full` to audit every surface × text combination
 * (includes pin-base-400 × full ramp).
 */
function contrastChecks() {
  if (MATRIX === "full") {
    const out = [];
    for (const bg of SURFACE_KEYS) {
      for (const fg of TEXT_KEYS) {
        out.push({ bg, fg, min: MIN_RATIO });
      }
    }
    return out;
  }
  if (MATRIX !== "semantic") {
    console.error(`Unknown PIN_CONTRAST_MATRIX=${MATRIX} (use semantic|full)`);
    process.exit(1);
  }
  const out = [];
  const shell = ["main", "pin-base-500", "pin-base-550"];
  const controlSurfaces = ["main-hover", "pin-base-450"];
  const strongText = [
    "pin-base-text",
    "pin-base-100",
    "pin-base-150",
    "pin-base-200",
  ];
  for (const bg of shell) {
    for (const fg of TEXT_KEYS) {
      out.push({ bg, fg, min: MIN_RATIO });
    }
  }
  for (const bg of controlSurfaces) {
    for (const fg of strongText) {
      out.push({ bg, fg, min: MIN_RATIO });
    }
  }
  return out;
}

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

function extractThemeBlock(css) {
  const marker = "@theme";
  const i = css.indexOf(marker);
  if (i < 0) return null;
  const brace = css.indexOf("{", i);
  if (brace < 0) return null;
  return extractBalancedBlock(css, brace);
}

function parseVariants(css) {
  const layerIdx = css.indexOf("@layer theme");
  const search = layerIdx >= 0 ? css.slice(layerIdx) : css;
  const re = /@variant\s+([\w-]+)\s*\{/g;
  const out = [];
  let m;
  while ((m = re.exec(search)) !== null) {
    const name = m[1];
    const open =
      layerIdx >= 0
        ? layerIdx + m.index + m[0].length - 1
        : m.index + m[0].length - 1;
    const body = extractBalancedBlock(css, open);
    if (body) out.push({ name, body });
  }
  return out;
}

function parsePinColorDeclarations(block) {
  const vars = {};
  const declRe = /--color-(pin-[\w-]+)\s*:\s*([^;]+);/g;
  let m;
  while ((m = declRe.exec(block)) !== null) {
    vars[m[1]] = m[2].trim();
  }
  return vars;
}

function parseHslToRgb(raw) {
  const s = raw.replace(/\/\*[\s\S]*?\*\//g, "").trim();
  const match = s.match(
    /hsl\(\s*([0-9.]+)\s*(?:deg)?\s*,\s*([0-9.]+)\s*%\s*,\s*([0-9.]+)\s*%\s*\)/i,
  );
  if (!match) return null;
  const h = Number(match[1]) / 360;
  const sat = Number(match[2]) / 100;
  const light = Number(match[3]) / 100;

  if (sat === 0) {
    const v = Math.round(light * 255);
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

  const q = light < 0.5 ? light * (1 + sat) : light + sat - light * sat;
  const p = 2 * light - q;
  const r = Math.round(
    Math.min(255, Math.max(0, hue2rgb(p, q, h + 1 / 3) * 255)),
  );
  const g = Math.round(Math.min(255, Math.max(0, hue2rgb(p, q, h) * 255)));
  const b = Math.round(
    Math.min(255, Math.max(0, hue2rgb(p, q, h - 1 / 3) * 255)),
  );
  return [r, g, b];
}

function srgbToLinear(c) {
  const x = c / 255;
  return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
}

function luminance(rgb) {
  const [r, g, b] = rgb.map(srgbToLinear);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(rgbA, rgbB) {
  const L1 = luminance(rgbA);
  const L2 = luminance(rgbB);
  const lighter = Math.max(L1, L2);
  const darker = Math.min(L1, L2);
  return (lighter + 0.05) / (darker + 0.05);
}

function resolveVars(rawMap) {
  const map = { ...rawMap };
  for (let round = 0; round < 20; round++) {
    let changed = false;
    for (const [key, val] of Object.entries(map)) {
      const m = val.match(/^var\(\s*--color-(pin-[\w-]+)\s*\)$/i);
      if (m) {
        const target = m[1];
        if (map[target] && !map[target].startsWith("var(")) {
          map[key] = map[target];
          changed = true;
        }
      }
    }
    if (!changed) break;
  }
  return map;
}

function rgbForToken(resolved, token) {
  const v = resolved[token];
  if (!v) return { error: `missing ${token}` };
  if (v.startsWith("var(")) return { error: `unresolved ${token}: ${v}` };
  const rgb = parseHslToRgb(v);
  if (!rgb) return { error: `unparseable ${token}: ${v}` };
  return { rgb };
}

function buildThemeMaps(baseBlock, variants) {
  const mochaRaw = parsePinColorDeclarations(baseBlock);
  const themes = [{ name: "mocha", raw: mochaRaw }];
  for (const { name, body } of variants) {
    const overlay = parsePinColorDeclarations(body);
    themes.push({ name, raw: { ...mochaRaw, ...overlay } });
  }
  return themes.map(({ name, raw }) => ({
    name,
    resolved: resolveVars(raw),
  }));
}

function main() {
  const css = readFileSync(INPUT_CSS, "utf8");
  const themeBlock = extractThemeBlock(css);
  if (!themeBlock) {
    console.error("Could not find @theme { ... } in input.css");
    process.exit(1);
  }
  const variants = parseVariants(css);
  const themes = buildThemeMaps(themeBlock, variants);

  const checks = contrastChecks();
  const failures = [];

  for (const { name, resolved } of themes) {
    for (const { bg: bgKey, fg: fgKey, min } of checks) {
      const bg = rgbForToken(resolved, bgKey);
      if ("error" in bg) {
        failures.push({
          theme: name,
          bg: bgKey,
          fg: fgKey,
          ratio: null,
          err: bg.error,
          min,
        });
        continue;
      }
      const fg = rgbForToken(resolved, fgKey);
      if ("error" in fg) {
        failures.push({
          theme: name,
          bg: bgKey,
          fg: fgKey,
          ratio: null,
          err: fg.error,
          min,
        });
        continue;
      }
      const ratio = contrastRatio(bg.rgb, fg.rgb);
      if (belowMin(ratio, min)) {
        failures.push({
          theme: name,
          bg: bgKey,
          fg: fgKey,
          ratio: Number(ratio.toFixed(2)),
          err: null,
          min,
        });
      }
    }
  }

  if (failures.length > 0) {
    console.error(
      `Theme contrast: ${failures.length} pair(s) below required ratio (matrix=${MATRIX}, min=${MIN_RATIO})\n`,
    );
    for (const f of failures) {
      if (f.err) {
        console.error(`  ${f.theme}: ${f.bg} vs ${f.fg} — ${f.err}`);
      } else {
        console.error(
          `  ${f.theme}: ${f.fg} on ${f.bg} → ${f.ratio}:1 (need ${f.min}:1)`,
        );
      }
    }
    process.exit(1);
  }

  const nChecks = checks.length;
  console.log(
    `Theme contrast OK: all ${themes.length} themes pass (matrix=${MATRIX}, ` +
      `${nChecks} pair(s) per theme, min=${MIN_RATIO}:1).`,
  );
}

main();
