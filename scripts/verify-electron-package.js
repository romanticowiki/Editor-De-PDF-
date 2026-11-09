"use strict";

const fs = require("node:fs");
const path = require("node:path");

const projectRoot = path.resolve(__dirname, "..");
const electronRoot = path.join(projectRoot, "electron");
const asar = require(path.join(electronRoot, "node_modules", "@electron", "asar"));

function normalize(relativePath) {
  return relativePath.replaceAll("\\", "/").replace(/^\/+/, "");
}

function resolveLocalModule(parentFile, request) {
  const unresolved = path.resolve(path.dirname(parentFile), request);
  const candidates = [unresolved, `${unresolved}.js`, `${unresolved}.json`, path.join(unresolved, "index.js")];
  const resolved = candidates.find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile());
  if (!resolved || !resolved.startsWith(`${electronRoot}${path.sep}`)) {
    throw new Error(`No se pudo resolver el módulo local ${request} desde ${parentFile}.`);
  }
  return resolved;
}

function collectRuntimeFiles(entrypoint) {
  const pending = [path.resolve(electronRoot, entrypoint)];
  const discovered = new Set(["package.json"]);

  while (pending.length > 0) {
    const current = pending.pop();
    const relative = normalize(path.relative(electronRoot, current));
    if (discovered.has(relative)) continue;
    discovered.add(relative);

    if (path.extname(current) !== ".js") continue;
    const source = fs.readFileSync(current, "utf8");
    for (const match of source.matchAll(/require\(["'](\.\.?\/[^"']+)["']\)/g)) {
      pending.push(resolveLocalModule(current, match[1]));
    }
  }

  return discovered;
}

function verifyPackage(archivePath) {
  const manifest = JSON.parse(fs.readFileSync(path.join(electronRoot, "package.json"), "utf8"));
  const packaged = new Set(asar.listPackage(archivePath).map(normalize));
  const required = collectRuntimeFiles(manifest.main);
  const missing = [...required].filter((file) => !packaged.has(file));

  if (missing.length > 0) {
    throw new Error(`app.asar no contiene módulos de ejecución requeridos: ${missing.join(", ")}`);
  }

  process.stdout.write(`app.asar verificado: ${[...required].sort().join(", ")}\n`);
}

const archivePath = process.argv[2];
if (!archivePath) {
  process.stderr.write("Uso: node scripts/verify-electron-package.js <ruta-a-app.asar>\n");
  process.exitCode = 2;
} else {
  try {
    verifyPackage(path.resolve(archivePath));
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : error}\n`);
    process.exitCode = 1;
  }
}

module.exports = { collectRuntimeFiles, verifyPackage };
