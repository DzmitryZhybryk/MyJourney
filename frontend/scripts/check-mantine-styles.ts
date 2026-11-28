/*
 * Checks that src/mantineStyles.ts imports exactly the Mantine stylesheets the app needs, in the
 * order of @mantine/core/styles.css. That file is the concatenation of the per-component ones, so
 * a subset in the same order keeps the cascade of every kept rule unchanged.
 *
 * Needed = the global stylesheets + one per `<Name>.module.mjs` reachable in Mantine's ESM import
 * graph from the components the app imports (each such module maps 1:1 to styles/<Name>.css).
 * A missing file renders a component unstyled, which neither tsc nor tests notice.
 *
 * Run: make mantine-styles (part of make check). On failure it prints the expected file.
 */
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { basename, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("../", import.meta.url));
const SRC = join(ROOT, "src");
const STYLES_MODULE = join(SRC, "mantineStyles.ts");
const MANTINE = join(ROOT, "node_modules/@mantine/core");
const ESM_INDEX = join(MANTINE, "esm/index.mjs");
const STYLES_DIR = join(MANTINE, "styles");
const FULL_STYLESHEET = join(MANTINE, "styles.css");
const GLOBAL_STYLESHEETS = ["baseline.css", "default-css-variables.css", "global.css"];
const CSS_MODULE_SUFFIX = ".module.mjs";

const MANTINE_NAMED_IMPORT = /import\s+(type\s+)?\{([^}]*)\}\s*from\s*["']@mantine\/core["']/gu;
const MANTINE_REFERENCE = /(?:from\s*|import\s*\(\s*)["']@mantine\/core["']/gu;
const RELATIVE_SPECIFIER = /(?:import|export)\s[^"';]*?["'](\.{1,2}\/[^"']+)["']/gu;
const INDEX_IMPORT = /import\s*\{([^}]*)\}\s*from\s*["'](\.\/[^"']+)["']/gu;
const INDEX_EXPORT = /export\s*\{([^}]*)\}/gu;
const STYLESHEET_IMPORT = /import\s+["']@mantine\/core\/styles\/([^"']+)["']/gu;

function listSourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return entry.name === "test" ? [] : listSourceFiles(path);
    const isSource = /\.tsx?$/u.test(entry.name) && !entry.name.includes(".test.");
    return isSource && path !== STYLES_MODULE ? [path] : [];
  });
}

/** `a`, `b as c`, `type d` → names exported by Mantine that exist at runtime (`a`, `b`). */
function runtimeNames(specifiers: string): string[] {
  return specifiers
    .split(",")
    .map((specifier) => specifier.trim())
    .filter((specifier) => specifier !== "" && !specifier.startsWith("type "))
    .map((specifier) => specifier.split(/\s+as\s+/u)[0]);
}

/**
 * Names the app imports from @mantine/core at runtime. Only `import { X } from "@mantine/core"` is
 * understood; a namespace, dynamic or re-export reference would hide components, so it fails.
 */
function findUsedMantineNames(): Set<string> {
  const names = new Set<string>();
  for (const file of listSourceFiles(SRC)) {
    const source = readFileSync(file, "utf8");
    const namedImports = [...source.matchAll(MANTINE_NAMED_IMPORT)];
    if ([...source.matchAll(MANTINE_REFERENCE)].length !== namedImports.length) {
      throw new Error(`${relative(ROOT, file)}: only \`import { X } from "@mantine/core"\` is supported`);
    }

    for (const match of namedImports) {
      if (match[1]) continue;
      for (const name of runtimeNames(match[2])) names.add(name);
    }
  }

  return names;
}

/** Exported name → absolute path of the ESM module that defines it, from Mantine's index. */
function readIndexModules(): Map<string, string> {
  const index = readFileSync(ESM_INDEX, "utf8");
  const moduleByLocal = new Map<string, string>();
  for (const [, specifiers, path] of index.matchAll(INDEX_IMPORT)) {
    for (const specifier of specifiers.split(",")) {
      const [imported, local = imported] = specifier.trim().split(/\s+as\s+/u);
      if (imported) moduleByLocal.set(local, resolve(dirname(ESM_INDEX), path));
    }
  }

  const moduleByExported = new Map<string, string>();
  for (const [, specifiers] of index.matchAll(INDEX_EXPORT)) {
    for (const specifier of specifiers.split(",")) {
      const [local, exported = local] = specifier.trim().split(/\s+as\s+/u);
      const path = moduleByLocal.get(local);
      if (path) moduleByExported.set(exported, path);
    }
  }

  return moduleByExported;
}

function collectCssModules(entries: Iterable<string>): Set<string> {
  const visited = new Set<string>();
  const queue = [...entries];
  while (queue.length > 0) {
    const file = queue.pop() as string;
    if (visited.has(file)) continue;
    visited.add(file);
    for (const [, specifier] of readFileSync(file, "utf8").matchAll(RELATIVE_SPECIFIER)) {
      queue.push(resolve(dirname(file), specifier));
    }
  }

  return new Set(
    [...visited]
      .filter((file) => file.endsWith(CSS_MODULE_SUFFIX))
      .map((file) => basename(file, CSS_MODULE_SUFFIX)),
  );
}

/** Every stylesheet without a component module must be a known global one, or it would be dropped. */
function assertGlobalStylesheets(): void {
  const moduleNames = new Set(
    readdirSync(join(MANTINE, "esm"), { recursive: true, encoding: "utf8" })
      .filter((path) => path.endsWith(CSS_MODULE_SUFFIX))
      .map((path) => basename(path, CSS_MODULE_SUFFIX)),
  );
  const unmatched = readdirSync(STYLES_DIR)
    .filter((sheet) => sheet.endsWith(".css") && !sheet.endsWith(".layer.css"))
    .filter((sheet) => !moduleNames.has(basename(sheet, ".css")))
    .sort();
  if (unmatched.join() !== [...GLOBAL_STYLESHEETS].sort().join()) {
    throw new Error(
      `Stylesheets without a component module: ${unmatched.join(", ")}; ` +
        `GLOBAL_STYLESHEETS lists ${GLOBAL_STYLESHEETS.join(", ")}. Update it to match Mantine.`,
    );
  }
}

function expectedStylesheets(): string[] {
  assertGlobalStylesheets();
  const moduleByName = readIndexModules();
  const entries = [...findUsedMantineNames()].map((name) => {
    const path = moduleByName.get(name);
    if (!path) throw new Error(`"${name}" is imported from @mantine/core but not found in its index`);
    return path;
  });

  const componentSheets = [...collectCssModules(entries)].map((name) => `${name}.css`);
  for (const sheet of componentSheets) {
    if (!existsSync(join(STYLES_DIR, sheet))) throw new Error(`No stylesheet ${sheet} in @mantine/core/styles`);
  }

  const full = readFileSync(FULL_STYLESHEET, "utf8");
  const position = (sheet: string): number => {
    const index = full.indexOf(readFileSync(join(STYLES_DIR, sheet), "utf8").trim());
    if (index < 0) throw new Error(`${sheet} is not part of styles.css; the ordering assumption broke`);
    return index;
  };

  return [...GLOBAL_STYLESHEETS, ...componentSheets].sort((a, b) => position(a) - position(b));
}

function actualStylesheets(): string[] {
  if (!existsSync(STYLES_MODULE)) return [];
  return [...readFileSync(STYLES_MODULE, "utf8").matchAll(STYLESHEET_IMPORT)].map((match) => match[1]);
}

const expected = expectedStylesheets();
const actual = actualStylesheets();
if (expected.join("\n") === actual.join("\n")) {
  console.log(`Mantine stylesheets: ${expected.length} files, in sync with the components used.`);
} else {
  const missing = expected.filter((sheet) => !actual.includes(sheet));
  const unused = actual.filter((sheet) => !expected.includes(sheet));
  console.error(`${relative(ROOT, STYLES_MODULE)} is out of sync with the Mantine components used.`);
  if (missing.length > 0) console.error(`Missing: ${missing.join(", ")}`);
  if (unused.length > 0) console.error(`Not needed: ${unused.join(", ")}`);
  if (missing.length === 0 && unused.length === 0) console.error("Wrong order.");
  console.error("\nExpected imports, in this order:\n");
  console.error(expected.map((sheet) => `import "@mantine/core/styles/${sheet}";`).join("\n"));
  process.exit(1);
}
