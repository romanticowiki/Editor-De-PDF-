"use strict";

function isAllowedExternalUrl(value) {
  try {
    return new Set(["http:", "https:"]).has(new URL(value).protocol);
  } catch {
    return false;
  }
}

function isTrustedAppUrl(value, port) {
  try {
    return new URL(value).origin === `http://127.0.0.1:${port}`;
  } catch {
    return false;
  }
}

module.exports = { isAllowedExternalUrl, isTrustedAppUrl };
