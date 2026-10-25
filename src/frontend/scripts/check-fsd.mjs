/**
 * Проверка границ слоёв Feature-Sliced Design.
 *
 * Скрипт смотрит только на импорты через алиас `@/`. Срез может зависеть от срезов
 * строго нижних слоёв, не тянуться к чужому срезу своего слоя и обращаться к чужому
 * срезу сущностей, фич, виджетов и страниц только через его публичный вход (`index`).
 * `shared` проверяется мягче: его сегменты вправе опираться друг на друга.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const sourceRoot = join(here, "..", "src");

const LAYERS = ["shared", "entities", "features", "widgets", "pages", "app"];
const LAYER_INDEX = new Map(LAYERS.map((layer, index) => [layer, index]));
const STRICT_SLICE_LAYERS = new Set(["entities", "features", "widgets", "pages"]);

const IMPORT_PATTERN = /(?:from|import)\s*\(?\s*["'](@\/[^"']+)["']/g;

/** Возвращает все файлы исходников интерфейса.
 *
 * Args:
 *   directory: Каталог обхода.
 *
 * Returns:
 *   Список файлов `.ts` и `.tsx`.
 */
function collectFiles(directory) {
  const found = [];
  for (const entry of readdirSync(directory)) {
    const path = join(directory, entry);
    if (entry === "node_modules" || entry.startsWith(".")) {
      continue;
    }
    if (statSync(path).isDirectory()) {
      found.push(...collectFiles(path));
    } else if (/\.(ts|tsx)$/.test(entry) && !/\.d\.ts$/.test(entry)) {
      found.push(path);
    }
  }
  return found;
}

/** Разбирает путь файла до слоя и среза.
 *
 * Args:
 *   path: Абсолютный путь файла.
 *
 * Returns:
 *   Слой, срез и признак файла вне слоёв.
 */
function describeFile(path) {
  const parts = relative(sourceRoot, path).split(sep);
  const layer = parts[0];
  if (!LAYER_INDEX.has(layer)) {
    return { layer: "app", slice: "root", outside: true };
  }
  return { layer, slice: parts[1] ?? "root", outside: false };
}

/** Разбирает спецификатор `@/...` на слой, срез и путь глубже среза.
 *
 * Args:
 *   specifier: Строка импорта с алиасом.
 *
 * Returns:
 *   Слой, срез и остальные сегменты.
 */
function parseSpecifier(specifier) {
  const parts = specifier.replace(/^@\//, "").split("/");
  return { layer: parts[0], slice: parts[1] ?? "root", rest: parts.slice(2) };
}

const problems = [];

for (const path of collectFiles(sourceRoot)) {
  const from = describeFile(path);
  if (from.outside) {
    continue;
  }
  const text = readFileSync(path, "utf8");
  for (const match of text.matchAll(IMPORT_PATTERN)) {
    const target = parseSpecifier(match[1]);
    const toIndex = LAYER_INDEX.get(target.layer);
    if (toIndex === undefined) {
      continue;
    }
    const fromIndex = LAYER_INDEX.get(from.layer);
    const label = `${relative(sourceRoot, path).split(sep).join("/")} → ${match[1]}`;

    if (from.layer === "shared" && target.layer === "shared") {
      continue;
    }
    if (toIndex > fromIndex) {
      problems.push(`${label}: импорт вверх по слоям — «${from.layer}» не зависит от «${target.layer}»`);
    } else if (toIndex === fromIndex && target.slice !== from.slice) {
      problems.push(`${label}: чужой срез того же слоя «${from.layer}»`);
    }

    if (STRICT_SLICE_LAYERS.has(target.layer) && target.rest.length > 0) {
      problems.push(`${label}: обход публичного входа — идите через «@/${target.layer}/${target.slice}»`);
    }
  }
}

if (problems.length > 0) {
  console.error("Проверка границ FSD не пройдена:");
  for (const problem of problems) {
    console.error(`  - ${problem}`);
  }
  process.exit(1);
}

console.log("Проверка границ FSD пройдена.");
