# Public GitHub + Firebase (Option B)

The repo keeps **`apiKey: "__FIREBASE_WEB_API_KEY__"`** in `index.html` so the real key is **not** in git. Production deploys inject the key via **GitHub Actions**.

## One-time setup (project owner)

### 1. GitHub repository secrets

**GitHub → your repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|-------------|--------|
| `FIREBASE_WEB_API_KEY` | Firebase Console → Project settings → Your apps → Web app → `apiKey` (Browser key string) |
| `FIREBASE_TOKEN` | Run **locally** in this folder: `npx firebase login:ci` — paste the token it prints |

### 2. Default branch

The workflow deploys on push to **`main`** or **`master`**. Rename branch or edit `.github/workflows/deploy-hosting.yml` if you use another name.

### 3. Your machine (local dev)

Add to **`.env`** (already gitignored):

```bash
FIREBASE_WEB_API_KEY=paste_same_key_as_github_secret
```

Then before local Firebase / static test:

```bash
npm run firebase:inject
npx firebase serve
# or open index.html via server after inject
```

### 4. Before every commit to a public repo

Restore the placeholder so you never push the real key:

```bash
npm run firebase:restore-placeholder
git add index.html
git commit ...
```

**Workflow:** inject → test locally → restore-placeholder → commit → push → Actions deploys with secret.

## Judges / teammates cloning the repo

- **Use the live site** (e.g. https://overfishing-2d415.web.app) for demos.
- To run locally: add `FIREBASE_WEB_API_KEY` to `.env`, run `npm run firebase:inject`, then serve.

## Deploy without Actions

If you deploy from your laptop only:

```bash
npm run firebase:inject
npx firebase deploy --only hosting
npm run firebase:restore-placeholder   # before git commit
```
