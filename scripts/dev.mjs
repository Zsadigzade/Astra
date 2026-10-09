// One command for the whole demo: `npm start` runs the seller + buyer (backend/scripts/up.py)
// and the dashboard (Vite) together. Ctrl+C stops all of it.
//   node scripts/dev.mjs              backend + dashboard (opens the browser; NO_OPEN=1 to skip)
//   node scripts/dev.mjs --web-only   dashboard only
//   node scripts/dev.mjs --api-only   backend only
import { spawn, spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const args = new Set(process.argv.slice(2));
const wantApi = !args.has("--web-only");
const wantWeb = !args.has("--api-only");
const isWin = process.platform === "win32";
const color = { api: "\x1b[36m", web: "\x1b[35m", dev: "\x1b[90m" };

const log = (tag, line) => process.stdout.write(`${color[tag]}[${tag}]\x1b[0m ${line}\n`);

// Minimal .env reader (KEY=value, # comments, optional quotes). Like python-dotenv, real environment
// variables win. Only used to hand the buyer's API_TOKEN to the dashboard; never printed.
function dotenv(file) {
  const out = {};
  if (!existsSync(file)) return out;
  for (const raw of readFileSync(file, "utf8").split(/\r?\n/)) {
    const m = raw.match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!m) continue;
    let value = m[2].trim();
    const q = value[0];
    if ((q === '"' || q === "'") && value.indexOf(q, 1) > 0) value = value.slice(1, value.indexOf(q, 1));
    else value = value.replace(/\s+#.*$/, "").trim();
    out[m[1]] = value;
  }
  return out;
}
const apiToken = process.env.API_TOKEN ?? dotenv(join(root, ".env")).API_TOKEN ?? "";

if (wantApi && spawnSync(isWin ? "uv --version" : "uv", isWin ? { shell: true, stdio: "ignore" } : ["--version"], isWin ? undefined : { stdio: "ignore" }).status !== 0) {
  log("dev", "uv is not installed or not on PATH. Install it from https://docs.astral.sh/uv/ and retry.");
  process.exit(1);
}
if (wantWeb && !existsSync(join(root, "frontend", "node_modules"))) {
  log("dev", "installing frontend dependencies...");
  const r = isWin
    ? spawnSync("npm install --no-audit --no-fund", { cwd: join(root, "frontend"), shell: true, stdio: "inherit" })
    : spawnSync("npm", ["install", "--no-audit", "--no-fund"], { cwd: join(root, "frontend"), stdio: "inherit" });
  if (r.status !== 0) process.exit(r.status ?? 1);
}

const children = new Map();
let stopping = false;

function start(tag, cmd, cmdArgs, cwd, env = {}, onLine = () => {}) {
  // One command string on Windows (needed for .cmd shims) avoids Node's args-with-shell deprecation warning.
  const child = (isWin ? spawn(`${cmd} ${cmdArgs.join(" ")}`, { cwd, shell: true, env: { ...process.env, PYTHONUNBUFFERED: "1", FORCE_COLOR: "1", ...env } })
    : spawn(cmd, cmdArgs, { cwd, env: { ...process.env, PYTHONUNBUFFERED: "1", FORCE_COLOR: "1", ...env } }));
  children.set(tag, child);
  for (const stream of [child.stdout, child.stderr]) {
    let buf = "";
    stream.on("data", (d) => {
      buf += d.toString();
      const lines = buf.split(/\r?\n/);
      buf = lines.pop();
      lines.filter((l) => l.trim()).forEach((l) => { log(tag, l); onLine(l); });
    });
  }
  child.on("exit", (code) => {
    children.delete(tag);
    if (!stopping) {
      log("dev", `${tag} exited${code ? ` with code ${code}` : ""}; stopping the rest.`);
      if (tag === "api" && !apiReady) {
        log("dev", "backend never came up. If a port is unavailable, an earlier session still runs (with the code it "
          + "started with): stop it, then run npm start again.");
      }
      stop(code ?? 0);
    }
  });
}

function kill(child) {
  if (isWin) spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  else child.kill("SIGINT");
}

function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  children.forEach(kill);
  setTimeout(() => process.exit(code), 400);
}

process.on("SIGINT", () => stop(0));
process.on("SIGTERM", () => stop(0));

function startWeb() {
  if (stopping || children.has("web")) return;
  const webArgs = ["run", "dev"];
  if (!process.env.NO_OPEN) webArgs.push("--", "--open");
  // The dashboard sends the buyer token as X-API-Token (and ?token= for SSE/audio).
  start("web", "npm", webArgs, join(root, "frontend"), { VITE_API_TOKEN: process.env.VITE_API_TOKEN ?? apiToken });
}

// The dashboard starts only after up.py reports both services healthy ("UP  buyer ..."). Starting it
// alongside a backend that fails fast (busy port, ledger safety) left an orphaned Vite on Windows.
let apiReady = false;
if (wantApi) {
  start("api", "uv", ["run", "python", "scripts/up.py"], join(root, "backend"), {}, (line) => {
    if (!apiReady && /^UP\s/.test(line.trim())) {
      apiReady = true;
      if (wantWeb) startWeb();
    }
  });
} else if (wantWeb) startWeb();
log("dev", `starting ${[wantApi && "backend (:8000 buyer, :8001 seller)", wantWeb && (wantApi ? "dashboard (:5173, once the backend is up)" : "dashboard (:5173)")].filter(Boolean).join(" + ")}. Ctrl+C stops everything.`);
