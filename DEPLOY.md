# Deploy FishSave: Firebase Hosting (frontend) + Cloud Run (backend)

Follow these steps to get the frontend and backend running together in the cloud.

---

## Prerequisites

- **Google Cloud / Firebase**: One Google account; Firebase and Cloud Run use the same GCP project.
- **Local tools**:
  - Node.js (for Firebase CLI)
  - Python 3.10+
  - [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
  - Docker (optional; Cloud Run can build from source with `gcloud run deploy --source .`)

---

## Part 1 – Cloud Run (backend first)

Deploy the FastAPI backend so you get a URL to use in the frontend.

### 1.1 Login and project

```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
```

(Use the same project you use for Firebase, or create one in [Google Cloud Console](https://console.cloud.google.com).)

### 1.2 Deploy from source (no local Docker required)

From the **project root** (`/Applications/overfishing`):

```bash
gcloud run deploy fishsave-api \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

- First time: you may be asked to enable the Cloud Run API; say yes.
- When prompted for **region**, you can press Enter to keep `us-central1`.

When it finishes, the CLI prints something like:

```text
Service [fishsave-api] revision has been deployed and is serving 100 percent of traffic.
Service URL: https://fishsave-api-XXXXXX-uc.a.run.app
```

**Copy that Service URL** — you will use it in the frontend and in the next step.

### 1.3 Set environment variables (secrets)

The container needs your API keys. In [Cloud Console](https://console.cloud.google.com):

1. Go to **Cloud Run** → select **fishsave-api**.
2. Click **Edit & Deploy New Revision**.
3. Open the **Variables & Secrets** tab.
4. Add these **environment variables** (or link Secret Manager secrets if you prefer):

   | Name                 | Value (your real keys) |
   |----------------------|------------------------|
   | `COHERE_API_KEY`     | Your Cohere API key    |
   | `ELEVENLABS_API_KEY` | Your ElevenLabs API key|
   | `ELEVENLABS_VOICE_ID`| Your ElevenLabs voice ID |

5. Click **Deploy**.

### 1.4 Test the backend

```bash
curl https://YOUR-CLOUD-RUN-URL/health
```

You should see: `{"status":"ok"}`.

---

## Part 2 – Point the frontend at Cloud Run

Before deploying the frontend, set the API base URL so the hosted site calls your Cloud Run backend.

1. Open **index.html** in the project root.
2. Find the line:
   ```javascript
   return 'https://YOUR-CLOUD-RUN-URL';  // e.g. https://fishsave-api-xxxxx-uc.a.run.app
   ```
3. Replace `YOUR-CLOUD-RUN-URL` with your **full** Cloud Run URL, e.g.:
   ```javascript
   return 'https://fishsave-api-XXXXXX-uc.a.run.app';
   ```
4. Save the file.

---

## Part 3 – Firebase Hosting (frontend)

### 3.1 Install Firebase CLI and login

```bash
npm install -g firebase-tools
firebase login
```

### 3.2 Create/link a Firebase project

If you don’t have a Firebase project yet:

1. Go to [Firebase Console](https://console.firebase.google.com) → **Add project**.
2. Use the **same** GCP project as Cloud Run, or create a new one (Firebase will create a GCP project for it).

Then in your project folder:

```bash
cd /Applications/overfishing
firebase use YOUR_FIREBASE_PROJECT_ID
```

(Or run `firebase init hosting` and pick the project when prompted; that will also create/update `firebase.json` and `.firebaserc`.)

### 3.3 Prepare the `public` folder

From the project root, run:

```bash
chmod +x scripts/prepare-firebase.sh
./scripts/prepare-firebase.sh
```

This copies `index.html`, the CSVs, and `graphs_5y/` and `graphs_10y/` into `public/`.

### 3.4 Deploy

```bash
firebase deploy --only hosting
```

The CLI will print your Hosting URL, e.g.:

```text
Hosting URL: https://YOUR-PROJECT.web.app
```

Open that URL in a browser. The app should load; when you use “Explain” or “Play explanation”, it will call your Cloud Run backend.

---

## Quick reference

| What              | Command / URL |
|-------------------|----------------|
| Backend deploy    | `gcloud run deploy fishsave-api --source . --region us-central1 --allow-unauthenticated` |
| Backend URL       | `https://fishsave-api-XXXXXX-uc.a.run.app` (from deploy output) |
| Set API keys      | Cloud Run → fishsave-api → Edit → Variables & Secrets |
| Prepare frontend  | `./scripts/prepare-firebase.sh` |
| Frontend deploy   | `firebase deploy --only hosting` |
| Frontend URL      | `https://YOUR-PROJECT.web.app` |

---

## Troubleshooting

- **CORS errors in browser**: The FastAPI app already allows all origins (`allow_origins=["*"]`). If you still see CORS errors, confirm the request is going to your Cloud Run URL (and that you replaced `YOUR-CLOUD-RUN-URL` in `index.html`).
- **429 / quota from Cohere or ElevenLabs**: Your app has fallbacks (e.g. gTTS for audio). For embeddings, ensure `COHERE_FALLBACK_EMBED_MODEL` is set in Cloud Run if you use that.
- **“No explanation text”**: Check that `COHERE_API_KEY` is set in Cloud Run and that the Cohere model names in `explain_policy_impact_for_elevenlabs.py` are valid.
- **Audio fails**: Ensure `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` are set in Cloud Run; the app will fall back to gTTS if ElevenLabs fails.
