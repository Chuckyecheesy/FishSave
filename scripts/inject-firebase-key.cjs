/**
 * Replace __FIREBASE_WEB_API_KEY__ in index.html with FIREBASE_WEB_API_KEY from .env
 * Run before: firebase serve / local testing
 */
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const indexPath = path.join(root, "index.html");
const envPath = path.join(root, ".env");

function readFirebaseKeyFromEnv() {
  if (!fs.existsSync(envPath)) {
    console.error("Missing .env — create it and add:\n  FIREBASE_WEB_API_KEY=your_browser_key");
    process.exit(1);
  }
  const text = fs.readFileSync(envPath, "utf8");
  for (const line of text.split(/\n/)) {
    const trimmed = line.trim();
    if (trimmed.startsWith("#") || !trimmed) continue;
    const m = trimmed.match(/^FIREBASE_WEB_API_KEY\s*=\s*(.+)$/);
    if (m) {
      let v = m[1].trim();
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'")))
        v = v.slice(1, -1);
      if (v && v !== "your_browser_key") return v;
    }
  }
  console.error(".env must contain FIREBASE_WEB_API_KEY=... (Firebase Console → Web app config)");
  process.exit(1);
}

const key = readFirebaseKeyFromEnv();
let html = fs.readFileSync(indexPath, "utf8");
if (!html.includes("__FIREBASE_WEB_API_KEY__")) {
  console.error("index.html has no placeholder __FIREBASE_WEB_API_KEY__ — run: npm run firebase:restore-placeholder");
  process.exit(1);
}
html = html.replace(/__FIREBASE_WEB_API_KEY__/g, key);
fs.writeFileSync(indexPath, html, "utf8");
console.log("Injected FIREBASE_WEB_API_KEY into index.html (do not commit this file with the real key).");
