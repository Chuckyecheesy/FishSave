# Firebase API key — secure it without breaking FishSave

Your `index.html` uses the Firebase Web SDK with a **browser API key**. That key is **not** a password (Firebase Rules protect your data), but anyone can copy it and run up quota unless you **restrict** it in Google Cloud.

Follow these steps **in order** so you never lock yourself out.

---

## Phase 0 — Before you change anything

You only use **Firebase Hosting** (not GitHub Pages). Your real URLs are:

1. **Production**
   - `https://overfishing-2d415.web.app/`
   - `https://overfishing-2d415.firebaseapp.com/`  
   (Both point at the same site; restrict **both** so the key works no matter which link people use.)

2. **Local testing** — use a server, not `file://`:
   - `firebase serve` → usually `http://localhost:5000`
   - Or any `http://localhost:PORT` / `http://127.0.0.1:PORT` you use.

Open **https://overfishing-2d415.web.app** once to confirm the app works before you change the key.

---

## Phase 1 — Add HTTP referrer restrictions (do this first)

This limits the key so only **your** sites can use it. Wrong referrers = blank/errors; correct list = no change in behavior.

1. Open **[API credentials for project overfishing-2d415](https://console.cloud.google.com/apis/credentials?project=overfishing-2d415)** (Google Cloud Console).
2. Open the API key that matches the `apiKey` in your `index.html` (often named like **Browser key (auto created by Firebase)**).
3. Under **Application restrictions**, choose **HTTP referrers (web sites)**.
4. Click **Add an item** and add **each** line below (Firebase Hosting only):

| Purpose           | Referrer to add |
|-------------------|-----------------|
| Firebase Hosting  | `https://overfishing-2d415.web.app/*` |
| Firebase Hosting  | `https://overfishing-2d415.firebaseapp.com/*` |
| Local — `firebase serve` (default port **5000**) | `http://localhost:5000/*` |
| Local — same, alternate host | `http://127.0.0.1:5000/*` |
| Other local ports (if you use them) | e.g. `http://localhost:3000/*`, `http://localhost:8080/*` — **one line per port** (Google does not accept `localhost:*`) |

*If you ever host the same app on GitHub Pages or another domain, add another line like `https://YOUR_USER.github.io/YOUR_REPO/*` for that site only.*

5. **Save**.

6. **Test immediately**:
   - Open **https://overfishing-2d415.web.app** and **https://overfishing-2d415.firebaseapp.com** (optional: both).
   - If you use local dev, run `firebase serve` and open `http://localhost:5000`.
   - Hard refresh (Ctrl+Shift+R / Cmd+Shift+R).
   - If something fails, you forgot a referrer — add it and save again.

**Local dev:** Google’s form usually **does not** accept `http://localhost:*/*`. Add **`http://localhost:5000/*`** (and `http://127.0.0.1:5000/*`) for default `firebase serve`. If you use another port, add that URL too. If you **only** test on the live Firebase URLs, you can skip localhost entries.

---

## Phase 2 — API restrictions (optional but recommended)

Still on the same key → **API restrictions** → **Restrict key** → **Select APIs**.

For your current code (only `initializeApp` + `firebase-app.js`), start with:

- **Firebase Installations API**

If you later add **Authentication**, also add:

- **Identity Toolkit API**
- **Token Service API**

If you add **Firestore**:

- **Cloud Firestore API**

If you add **Storage**:

- **Cloud Storage for Firebase API**

Save, then **test the app again** on every URL. If a feature breaks, check the browser **Network** tab for failed Google API calls and add the missing API to this list.

---

## Phase 3 — Key was public on GitHub → rotate the key

Restrictions stop *new* abuse from random domains; the old key string is still in git history.

1. In **Google Cloud Console** → **APIs & Services** → **Credentials**.
2. You can **regenerate** the key or **create** a new browser key, then:
   - Apply the **same** referrer + API restrictions as above.
3. In [Firebase Console](https://console.firebase.google.com/) → your project → **Project settings** (gear) → **Your apps** → Web app: confirm the config or update if Google gives you a new web API key string.
4. In this repo, update **only** the `apiKey` value inside `index.html` in `firebaseConfig` to the **new** key.
5. Deploy / push and test again.

---

## Phase 4 — GitHub cleanup

1. Stop committing the old key: ensure new commits use the **rotated** key (still visible in client code — that’s normal for Firebase Web; restrictions are what matter).
2. To remove the old key from **history**, use [GitHub’s guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) or BFG Repo-Cleaner — coordinate with anyone who has cloned the repo.

---

## Quick troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| Firebase / blank errors after save | Referrer not listed for the exact origin you’re using |
| Works on one Firebase URL but not the other | Add the missing `web.app` or `firebaseapp.com` referrer |
| Local broken after restrict | Add the exact origin, e.g. `http://localhost:5000/*` (wildcard port is often invalid) |
| Specific feature fails after API restrict | Add the API that feature needs (see Phase 2) |

---

## What we did **not** change in code

Your app logic (`initializeApp`, `window.firebaseApp`, forecasts, API calls) is unchanged. Securing the key is done in **Google Cloud Console** (+ optional `apiKey` string update after rotation in `index.html`).
