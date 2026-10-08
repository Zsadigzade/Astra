// `npm run setup`: create the root .env from .env.example (never overwrites an existing one), then say what to do next.
import { copyFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const env = join(root, ".env");

if (existsSync(env)) {
  console.log(".env already exists, left untouched.");
} else {
  copyFileSync(join(root, ".env.example"), env);
  console.log("Created .env from .env.example (it is git-ignored; never commit real keys).");
}
console.log(`
Next:
  1. Fill in the keys you have in .env (APIFY_TOKEN, ELEVENLABS_API_KEY + voice IDs, MASUMI_* ...).
  2. npm run doctor        shows what is ready and what is still missing, per integration
  3. npm run doctor:live   adds the read-only live checks (Masumi node, voices, Codex)
  4. npm start             runs the whole system`);
