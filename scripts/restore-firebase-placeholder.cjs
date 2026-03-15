/**
 * Put __FIREBASE_WEB_API_KEY__ back in index.html so you can commit safely to a public repo.
 */
const fs = require("fs");
const path = require("path");

const indexPath = path.join(__dirname, "..", "index.html");
let html = fs.readFileSync(indexPath, "utf8");

if (html.includes("__FIREBASE_WEB_API_KEY__")) {
  console.log("index.html already uses the placeholder.");
  process.exit(0);
}

// Single apiKey in index.html (Firebase Web config)
const replaced = html.replace(/apiKey:\s*"[^"]+"/, 'apiKey: "__FIREBASE_WEB_API_KEY__"');
if (replaced === html) {
  console.error("Could not find apiKey line to restore. Check index.html.");
  process.exit(1);
}
fs.writeFileSync(indexPath, replaced, "utf8");
console.log("Restored __FIREBASE_WEB_API_KEY__ placeholder — safe to commit index.html.");
