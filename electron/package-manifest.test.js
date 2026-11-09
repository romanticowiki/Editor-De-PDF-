"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = __dirname;
const packageJson = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));

function localRequires(source) {
  return [...source.matchAll(/require\(["'](\.\/[^"']+)["']\)/g)].map((match) => match[1]);
}

test("every local module required by the Electron entrypoint is packaged", () => {
  const entrypoint = fs.readFileSync(path.join(root, packageJson.main), "utf8");
  const packagedFiles = new Set(packageJson.build.files);

  for (const request of localRequires(entrypoint)) {
    const relativeFile = `${request.slice(2)}.js`;
    assert.ok(fs.existsSync(path.join(root, relativeFile)), `missing source module: ${relativeFile}`);
    assert.ok(packagedFiles.has(relativeFile), `build.files omits local module: ${relativeFile}`);
  }
});

test("the corrected installer keeps the existing identity and uses one install scope", () => {
  assert.equal(packageJson.version, "0.3.1");
  assert.equal(packageJson.build.appId, "com.epdf.app");
  assert.equal(packageJson.build.nsis.guid, "1dc1bdf5-b7bd-5394-97f0-381fce99df89");
  assert.equal(packageJson.build.nsis.perMachine, true);
  assert.equal(packageJson.build.nsis.include, "build/installer.nsh");
  assert.equal(packageJson.build.nsis.deleteAppDataOnUninstall, false);
});

test("the NSIS policy blocks same-version reinstalls and accidental downgrades", () => {
  const policy = fs.readFileSync(path.join(root, "build", "installer.nsh"), "utf8");

  assert.match(policy, /\$\{VersionCompare\}/);
  assert.match(policy, /La misma versi[oó]n/);
  assert.match(policy, /versi[oó]n anterior/);
  assert.match(policy, /ReadRegStr \$R0 HKLM "\$\{UNINSTALL_REGISTRY_KEY\}" "DisplayVersion"/);
  assert.match(policy, /ReadRegStr \$R2 HKCU "\$\{INSTALL_REGISTRY_KEY\}" "InstallLocation"/);
});
