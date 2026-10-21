import assert from "node:assert/strict";
import { createServer as createHttpServer } from "node:http";
import { once } from "node:events";
import { test } from "node:test";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

test("local API connection authenticates server-side and rejects other origins", async () => {
  const token = "test-only-backend-credential-" + "x".repeat(32);
  let calls = 0;
  const backend = createHttpServer((request, response) => {
    calls++;
    assert.equal(request.headers.authorization, `Bearer ${token}`);
    response.setHeader("Content-Type", "application/json");
    response.end(JSON.stringify({ connected: true }));
  });
  backend.listen(0, "127.0.0.1");
  await once(backend, "listening");
  const previous = Object.fromEntries(["API_WRITE_TOKEN", "VITE_API_URL", "AUTH_REQUIRED"].map(key => [key, process.env[key]]));
  process.env.API_WRITE_TOKEN = token;
  process.env.AUTH_REQUIRED = "true";
  process.env.VITE_API_URL = `http://127.0.0.1:${backend.address().port}`;
  let app;
  try {
    app = await createServer({
      root: fileURLToPath(new URL("..", import.meta.url)),
      configFile: fileURLToPath(new URL("../vite.config.js", import.meta.url)),
      server: { host: "127.0.0.1", port: 0 },
      logLevel: "silent",
    });
    await app.listen();
    const origin = `http://127.0.0.1:${app.httpServer.address().port}`;
    const response = await fetch(`${origin}/api/tickets`, { headers: { Origin: origin, Authorization: "Bearer old-browser-token" } });
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { connected: true });
    assert.equal(calls, 1);
    const denied = await fetch(`${origin}/api/tickets/1/retry`, { method: "POST", headers: { Origin: "https://unrelated.example" } });
    assert.equal(denied.status, 403);
    assert.equal(calls, 1);
    const crossSite = await fetch(`${origin}/api/tickets`, { headers: { "Sec-Fetch-Site": "cross-site" } });
    assert.equal(crossSite.status, 403);
    assert.equal(calls, 1);
    const script = await fetch(`${origin}/src/services/api.js`);
    const source = await script.text();
    assert.equal(source.includes(token), false);
    assert.equal(source.includes("supportflow-token"), false);
  } finally {
    await app?.close();
    backend.close();
    await once(backend, "close");
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
});
