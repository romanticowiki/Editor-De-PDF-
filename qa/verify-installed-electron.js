"use strict";

// QA end-to-end de la ventana instalada. Electron se inicia con --remote-debugging-port y este
// script usa el protocolo de Chromium para recorrer la UI, subir un PDF y comprobar la descarga.

const fs = require("node:fs");
const path = require("node:path");

const port = Number(process.env.EPDF_CDP_PORT || 0);
const inputPdf = path.resolve(process.env.EPDF_TEST_PDF || "");
const downloadDir = path.resolve(process.env.EPDF_DOWNLOAD_DIR || "");

if (!port || !fs.existsSync(inputPdf) || !downloadDir) {
  throw new Error("Define EPDF_CDP_PORT, EPDF_TEST_PDF y EPDF_DOWNLOAD_DIR.");
}
fs.mkdirSync(downloadDir, { recursive: true });

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitFor(description, operation, timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const result = await operation();
      if (result) return result;
    } catch (error) {
      lastError = error;
    }
    await delay(250);
  }
  throw new Error(`${description} no ocurrió a tiempo${lastError ? `: ${lastError}` : ""}`);
}

async function pageTarget() {
  return waitFor("la página de Electron", async () => {
    const response = await fetch(`http://127.0.0.1:${port}/json/list`);
    const targets = await response.json();
    return targets.find((target) => target.type === "page" && target.url.startsWith("http://127.0.0.1:"));
  }, 90_000);
}

function connect(webSocketUrl) {
  const socket = new WebSocket(webSocketUrl);
  const pending = new Map();
  let nextId = 1;

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    const request = pending.get(message.id);
    if (!request) return;
    pending.delete(message.id);
    if (message.error) request.reject(new Error(`${message.error.code}: ${message.error.message}`));
    else request.resolve(message.result);
  });

  const opened = new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });

  return {
    async send(method, params = {}) {
      await opened;
      const id = nextId++;
      const result = new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
      socket.send(JSON.stringify({ id, method, params }));
      return result;
    },
    close() {
      socket.close();
    },
  };
}

async function main() {
  const target = await pageTarget();
  const client = connect(target.webSocketDebuggerUrl);
  const evaluate = async (expression) => {
    const response = await client.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
    return response.result.value;
  };

  try {
    await client.send("Runtime.enable");
    await client.send("DOM.enable");
    await client.send("Page.enable");
    await client.send("Page.setDownloadBehavior", { behavior: "allow", downloadPath: downloadDir });

    const initial = await waitFor("el catálogo de EPDF", async () => {
      const state = await evaluate("({title: document.title, origin: location.origin, text: document.body.innerText})");
      return state.text.includes("Comprimir PDF") ? state : false;
    }, 90_000);

    const opened = await evaluate(`(() => {
      const link = [...document.querySelectorAll("a")].find((node) => node.textContent.includes("Comprimir PDF"));
      if (!link) return false;
      link.click();
      return true;
    })()`);
    if (!opened) throw new Error("No se encontró la herramienta Comprimir PDF.");

    await waitFor("el selector de PDF", () => evaluate("Boolean(document.querySelector('input[type=file]'))"));
    const documentNode = await client.send("DOM.getDocument", { depth: -1, pierce: true });
    const inputNode = await client.send("DOM.querySelector", {
      nodeId: documentNode.root.nodeId,
      selector: "input[type=file]",
    });
    if (!inputNode.nodeId) throw new Error("No se encontró el input de archivo.");
    await client.send("DOM.setFileInputFiles", { nodeId: inputNode.nodeId, files: [inputPdf] });

    await waitFor("la selección del PDF", () => evaluate(`document.body.innerText.includes(${JSON.stringify(path.basename(inputPdf))})`));
    await waitFor("el botón Comprimir habilitado", () => evaluate(`(() => {
      const button = [...document.querySelectorAll("button")].find((node) => node.textContent.trim() === "Comprimir");
      return Boolean(button && !button.disabled);
    })()`));

    const before = new Set(fs.readdirSync(downloadDir));
    await evaluate(`(() => {
      const button = [...document.querySelectorAll("button")].find((node) => node.textContent.trim() === "Comprimir");
      button.click();
    })()`);

    const downloaded = await waitFor("la descarga procesada", () => {
      const files = fs.readdirSync(downloadDir).filter((name) => !before.has(name) && name.endsWith(".pdf"));
      const complete = files.find((name) => !fs.existsSync(path.join(downloadDir, `${name}.crdownload`)));
      return complete && path.join(downloadDir, complete);
    }, 90_000);
    const successText = await waitFor("la confirmación visual", async () => {
      const text = await evaluate("document.body.innerText");
      return text.includes("Listo") ? text : false;
    });

    process.stdout.write(`${JSON.stringify({
      title: initial.title,
      origin: initial.origin,
      route: await evaluate("location.hash"),
      downloaded,
      bytes: fs.statSync(downloaded).size,
      success: successText.includes("Listo"),
    })}\n`);
  } finally {
    client.close();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
