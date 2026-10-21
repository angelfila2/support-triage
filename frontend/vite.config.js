import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import { fileURLToPath } from "node:url";
import process from "node:process";

const frontendDirectory = fileURLToPath(new URL(".", import.meta.url));
const backendDirectory = fileURLToPath(new URL("../backend", import.meta.url));
const loopbackHosts = new Set(["localhost", "127.0.0.1", "[::1]"]);

// This runs inside Vite's Node server, never inside browser code.
export default defineConfig(({ mode }) => {
  const backend = loadEnv(mode, backendDirectory, "");
  const frontend = loadEnv(mode, frontendDirectory, "VITE_");
  const target = new URL(process.env.VITE_API_URL || frontend.VITE_API_URL || "http://127.0.0.1:8000");
  if (!loopbackHosts.has(target.hostname) || target.username || target.password || !["http:", "https:"].includes(target.protocol)) {
    throw new Error("The automatic local API connection requires a localhost backend URL.");
  }
  const token = process.env.API_WRITE_TOKEN || backend.API_WRITE_TOKEN || "";
  const authRequired = (process.env.AUTH_REQUIRED || backend.AUTH_REQUIRED || "true").toLowerCase() === "true";
  if (authRequired && token.length < 32) {
    throw new Error("Set API_WRITE_TOKEN to at least 32 characters in backend/.env, then restart the frontend.");
  }

  // A web page on another origin must not borrow this local proxy's credential.
  const localRequestsOnly = (request, response, next) => {
    if (!/^\/(api|health)(\/|\?|$)/.test(request.url || "")) return next();
    const address = request.socket.remoteAddress;
    const local = ["127.0.0.1", "::1", "::ffff:127.0.0.1"].includes(address);
    let sameOrigin = true;
    if (request.headers.origin) {
      try { sameOrigin = new URL(request.headers.origin).host === request.headers.host; }
      catch { sameOrigin = false; }
    }
    if (!local || !sameOrigin || request.headers["sec-fetch-site"] === "cross-site") {
      response.writeHead(403, { "Content-Type": "application/json" });
      return response.end(JSON.stringify({ detail: "This connection is only available from the local app." }));
    }
    next();
  };

  const proxy = Object.fromEntries(["/api", "/health"].map((route) => [route, {
    target: target.origin,
    changeOrigin: true,
    configure(server) {
      server.on("proxyReq", (request) => {
        if (token) request.setHeader("Authorization", `Bearer ${token}`);
        else request.removeHeader("Authorization");
      });
    },
  }]));

  return {
    plugins: [react(), {
      name: "local-backend-connection",
      configureServer(server) { server.middlewares.use(localRequestsOnly); },
      configurePreviewServer(server) { server.middlewares.use(localRequestsOnly); },
    }],
    server: { host: "127.0.0.1", proxy },
    preview: { host: "127.0.0.1", proxy },
  };
});
