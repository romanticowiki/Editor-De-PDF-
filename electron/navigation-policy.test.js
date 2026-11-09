"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { isAllowedExternalUrl, isTrustedAppUrl } = require("./navigation-policy");

test("external links allow only HTTP and HTTPS", () => {
  assert.equal(isAllowedExternalUrl("https://example.com/help"), true);
  assert.equal(isAllowedExternalUrl("http://example.com/help"), true);
  assert.equal(isAllowedExternalUrl("file:///C:/private.txt"), false);
  assert.equal(isAllowedExternalUrl("javascript:alert(1)"), false);
  assert.equal(isAllowedExternalUrl("custom-protocol:payload"), false);
  assert.equal(isAllowedExternalUrl("not a url"), false);
});

test("navigation stays on the exact loopback origin selected for the backend", () => {
  assert.equal(isTrustedAppUrl("http://127.0.0.1:43123/#/editor-pdf", 43123), true);
  assert.equal(isTrustedAppUrl("http://127.0.0.1:43123/api/v1/health", 43123), true);
  assert.equal(isTrustedAppUrl("http://localhost:43123/", 43123), false);
  assert.equal(isTrustedAppUrl("http://127.0.0.1:43124/", 43123), false);
  assert.equal(isTrustedAppUrl("https://example.com/", 43123), false);
  assert.equal(isTrustedAppUrl("invalid", 43123), false);
});
