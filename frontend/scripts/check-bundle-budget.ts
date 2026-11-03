/*
 * Checks the bundle budget (.claude/rules/web/performance.md, "Bundle Budget") on a production build.
 * A page's weight is what the browser must download to show it: the entry point and everything it
 * and the page chunks pull in via static imports, plus their CSS. A dynamic import() (the globe
 * background, neighbouring pages) loads separately and does not count toward the page weight.
 *
 * The graph comes from the Vite manifest, not from chunk text: the manifest separates static and
 * dynamic imports, while in preloading they look the same.
 *
 * Run: make budget (builds with the manifest and checks). Fails if a page does not fit.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const DIST = fileURLToPath(new URL("../dist/", import.meta.url));
const MANIFEST = `${DIST}.vite/manifest.json`;

interface ManifestChunk {
  file: string;
  isEntry?: boolean;
  imports?: string[];
  css?: string[];
}

type Manifest = Record<string, ManifestChunk>;

interface Budget {
  js: number;
  css: number;
}

// Limits in kB gzip (1 kB = 1000 bytes, as in the Vite report). The numbers and their rationale
// live in performance.md; change them there and here together.
const BUDGETS = {
  landing: { js: 200, css: 25 },
  app: { js: 300, css: 30 },
} satisfies Record<string, Budget>;

interface Page {
  name: string;
  budget: keyof typeof BUDGETS;
  /** Route modules from App.tsx that load lazily: the layout and the page itself. */
  modules: string[];
}

const PAGES: readonly Page[] = [
  { name: "/", budget: "landing", modules: ["src/pages/PublicLayout.tsx", "src/pages/LandingPage.tsx"] },
  { name: "/login", budget: "app", modules: ["src/pages/PublicLayout.tsx", "src/pages/LoginPage.tsx"] },
  { name: "/signup", budget: "app", modules: ["src/pages/PublicLayout.tsx", "src/pages/SignUpPage.tsx"] },
  { name: "/home", budget: "app", modules: ["src/pages/HomePage.tsx"] },
  // The shared map (country borders) loads lazily from the layout on every tab that shows it, so it
  // is counted there explicitly; /journeys/add never loads it.
  {
    name: "/journeys",
    budget: "app",
    modules: [
      "src/pages/journeys/JourneysLayout.tsx",
      "src/pages/journeys/JourneysMapView.tsx",
      "src/pages/journeys/map/JourneysSharedMap.tsx",
    ],
  },
  {
    name: "/journeys/movements",
    budget: "app",
    modules: [
      "src/pages/journeys/JourneysLayout.tsx",
      "src/pages/journeys/MovementsMapView.tsx",
      "src/pages/journeys/map/JourneysSharedMap.tsx",
    ],
  },
  {
    name: "/journeys/all",
    budget: "app",
    modules: [
      "src/pages/journeys/JourneysLayout.tsx",
      "src/pages/journeys/all/AllJourneysView.tsx",
      "src/pages/journeys/map/JourneysSharedMap.tsx",
    ],
  },
  {
    name: "/journeys/add",
    budget: "app",
    modules: ["src/pages/journeys/JourneysLayout.tsx", "src/pages/journeys/AddJourneyPage.tsx"],
  },
];

const manifest = JSON.parse(readFileSync(MANIFEST, "utf8")) as Manifest;

// Sizes use our own gzip level 9, not the numbers from `vite build` output: Vite compresses with a
// different compressor and its gz column differs from this one by 1-3%. Compare limits only with
// this script's output.
const gzipSizes = new Map<string, number>();
function gzipSize(file: string): number {
  let size = gzipSizes.get(file);
  if (size === undefined) {
    size = gzipSync(readFileSync(`${DIST}${file}`), { level: 9 }).length;
    gzipSizes.set(file, size);
  }

  return size;
}

function chunk(key: string): ManifestChunk {
  const found = manifest[key];
  if (!found) {
    throw new Error(`В манифесте нет «${key}» — модуль переименован? Поправь PAGES в ${import.meta.filename}`);
  }

  return found;
}

/** JS and CSS files pulled in by the `roots` modules together with all their static imports. */
function staticClosure(roots: readonly string[]): { js: Set<string>; css: Set<string> } {
  const js = new Set<string>();
  const css = new Set<string>();
  const seen = new Set<string>();
  const stack = [...roots];
  while (stack.length > 0) {
    const key = stack.pop() as string;
    if (seen.has(key)) continue;

    seen.add(key);
    const { file, imports = [], css: styles = [] } = chunk(key);
    js.add(file);
    for (const style of styles) css.add(style);

    stack.push(...imports);
  }

  return { js, css };
}

function totalKb(files: Set<string>): number {
  let bytes = 0;
  for (const file of files) bytes += gzipSize(file);

  return bytes / 1000;
}

const entries = Object.keys(manifest).filter((key) => manifest[key].isEntry);
let isOverBudget = false;
const rows = PAGES.map((page) => {
  const { js, css } = staticClosure([...entries, ...page.modules]);
  const budget: Budget = BUDGETS[page.budget];
  const jsKb = totalKb(js);
  const cssKb = totalKb(css);
  const isOver = jsKb > budget.js || cssKb > budget.css;
  if (isOver) isOverBudget = true;

  return {
    page: page.name,
    budget: page.budget,
    "JS, kB gz": `${jsKb.toFixed(1)} / ${budget.js}`,
    "CSS, kB gz": `${cssKb.toFixed(1)} / ${budget.css}`,
    status: isOver ? "OVER" : "ok",
  };
});

console.table(rows);
if (isOverBudget) {
  console.error("Бюджет превышен: ужми страницу или пересмотри лимит в performance.md с обоснованием.");
  process.exit(1);
}
