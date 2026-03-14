# FishSave — Overfishing Risk & Seafood Price Inflation

**FishSave** helps governments understand how overfishing in their country affects seafood price inflation. It forecasts overfishing and inflation for the next **5 and 10 years**, scores **risk** by country, and recommends **policy implementations** from a database—tailored by risk level—with reasoning, example actions, and optional audio explanations. Officials can **accept** or **reject** recommendations; when rejected, the next policy from the database is shown on the dashboard.

---

## What the project does

- **Forecast** next 5 and 10 years of **overfishing rate** (OFR) and **seafood price inflation** per country using historical catch data and time-series models.
- **Score risk** so governments can see how significantly their overfishing activity impacts seafood price inflation (risk score in [0, 1]).
- **Recommend policy implementations** from a policy database, filtered/tailored by risk level (Low / Medium / High).
- **Policy popup:** For each recommendation, a popup shows:
  - **What the policy means** — reasoning and explanation.
  - **Plan** — example measurable actions to implement the policy.
- **Explain:** Explains how the listed policy and planned actions help **reduce overfishing** and **by how much** they reduce overfishing’s impact on seafood price inflation (text + optional **audio** via TTS).
- **Accept or reject:** Users can accept a recommendation or reject it. On reject, the app fetches the **next** policy from the database and displays it on the dashboard; they can accept when they find the best option to slow seafood price inflation caused by overfishing.

---

## Dataset

- **Primary:** [Worldwide Fishing Catch Statistics 1950–2018 (Kaggle)](https://www.kaggle.com/datasets/thebumpkin/worldwide-fishing-catch-statitstics-1950-2018)  
  Columns: Country, Year, Species, Catch (tons).

---

## Formulas and ML computation

The pipeline uses the following definitions and models.

### 1. Overfishing risk (OFR)

For country \(c\) and year \(t\), catch relative to **initial (first non-zero) catch**:

\[
\text{OFR}_{c,t} = \frac{\text{catch}_{c,t}}{\text{catch}_{c,\text{initial}}} \times 100
\]

- **Used for:** Measuring pressure on fish stocks; base for OFR change and proxy price index.

### 2. Year-on-year OFR change (%)

\[
\text{OFR\_change}_{c,t} = \frac{\text{OFR}_{c,t} - \text{OFR}_{c,t-1}}{\text{OFR}_{c,t-1}} \times 100
\]

- **Used for:** Time-series inputs and risk components (slope/sum over forecast windows).

### 3. Proxy price index (PriceIndex)

Iterative update with sensitivity \(\beta\) (e.g. 0.5):

\[
\text{PriceIndex}_t = \text{PriceIndex}_{t-1} \times \left(1 + \beta \times \frac{\text{OFR\_change}_t}{100}\right)
\]

- **Used for:** Proxy for seafood price level; regression target in the downstream ML model; basis for inflation %.

### 4. Inflation (%)

\[
\text{Inflation\_pct}_t = \frac{\text{PriceIndex}_t - \text{PriceIndex}_{t-1}}{\text{PriceIndex}_{t-1}} \times 100
\]

- **Used for:** Forecast outputs (next 5/10 years) and as a component of risk score.

### 5. Risk score (per country, 5y and 10y)

From forecast tables (e.g. `forecast_next5years.csv`, `forecast_next10years.csv`) with columns `Country`, `Year`, `OFR_change`, `Inflation_pct`:

1. **Per country:** Compute over the forecast window:
   - `slope_OFR_change` — linear regression slope of OFR_change vs year  
   - `slope_Inflation_pct` — slope of Inflation_pct vs year  
   - `sum_OFR_change` — sum of OFR_change  
   - `sum_Inflation_pct` — sum of Inflation_pct  

2. **Normalize** each of these four components to [0, 1] across countries (min–max). Constant series → 0.5.

3. **Risk score** = mean of the four normalized components:

\[
\text{risk\_score} = \frac{1}{4}\big(\tilde{s}_{\text{OFR}} + \tilde{s}_{\text{inf}} + \tilde{S}_{\text{OFR}} + \tilde{S}_{\text{inf}}\big)
\]

where \(\tilde{s}\) are normalized slopes and \(\tilde{S}\) are normalized sums. Done separately for 5-year and 10-year windows → `risk_score_5y`, `risk_score_10y`.

- **Used for:** Ranking countries by “inflation due to overfishing” risk; tailoring policy recommendations by risk level.

### 6. Forecasting (next 5 and 10 years)

- **Catch series:** ARIMA models (orders chosen from a small set, e.g. (0,1,0), (0,1,1), (1,1,1), …) fit on historical catch; best order by validation MAE. Forecast steps = from last data year through next 5 or 10 years.
- **From forecast catch:** Same formulas as above to get OFR → OFR_change → PriceIndex → Inflation_pct for each future year.
- **Outputs:** `forecast_next5years.csv`, `forecast_next10years.csv` (Country, Year, OFR_change, Inflation_pct).

### 7. Downstream ML model (PriceIndex regression)

- **Purpose:** Predict **PriceIndex** from a fixed 10-year window of catch (or derived features).
- **Inputs:** `train_features_updated.csv`, `val_features_updated.csv`, `test_features_updated.csv` (10-year windows: train 1991–2000, val 2001–2010, test 2016–2025).
- **Model:** `RandomForestRegressor` (e.g. 100 trees).
- **Target:** PriceIndex.
- **Outputs:** `model.joblib`, `eval_report.json` (MAE/RMSE).

---

## Project structure

```
.
├── index.html              # Frontend: dashboard, country/horizon selection, policy popup, Explain, Accept/Reject
├── 404.html
├── firebase.json            # Firebase Hosting (public: .)
├── .firebaserc              # Firebase project (overfishing-2d415)
├── package.json             # npm (Firebase CLI)
├── requirements.txt        # Python backend deps
├── Dockerfile               # Cloud Run TTS API
├── .env                     # API keys (not committed): COHERE, ELEVENLABS, etc.
│
├── Data & features
├── FishStats2018.csv        # Raw catch data (Kaggle)
├── data_agent.py            # Load/aggregate catch data
├── feature_agent.py         # OFR, OFR_change, PriceIndex → country_features.csv
├── country_features.csv
├── split_train_val_test.py  # Train/val/test splits
├── train_features.csv, val_features.csv, test_features.csv
├── update_pipeline.py       # Updated feature CSVs
├── train_features_updated.csv, val_features_updated.csv, test_features_updated.csv
│
├── Forecasting
├── forecast_agent.py
├── forecast_ofr_2019_2025.py
├── forecast_next_5_10_years.py   # ARIMA → forecast_next5years.csv, forecast_next10years.csv
├── forecast_next5years.csv, forecast_next10years.csv
├── enrich_forecast_predictions.py
├── evaluate_forecast_model.py
│
├── Risk & policy
├── compute_risk_score.py     # risk_score_5y, risk_score_10y from slopes/sums + min-max norm
├── risk_score.csv
├── train_risk_classifier.py # Risk category (Low/Medium/High)
├── risk_score_with_category.csv
├── policy_chunks.py         # Policy DB chunks
├── ingest_policy_chroma.py  # ChromaDB policy embeddings
├── query_policy_chroma.py
├── recommend_by_risk.py     # Risk-based policy recommendations (Chroma + Gemini)
├── explain_why_reduces_overfishing.py
├── explain_policy_impact_for_elevenlabs.py  # Cohere explanation for TTS
│
├── ML model (PriceIndex)
├── train_model.py           # RandomForestRegressor on 10-year windows → model.joblib
├── model.joblib
├── eval_report.json
│
├── TTS API (Explain audio)
├── policy_tts_api.py        # FastAPI: /api/policy-explanation-audio, /api/risk-explanation-audio
│
├── DB / optional
├── neon_schema.sql, neon_pgvector.sql
├── load_country_risk_to_neon.py, load_forecast_metrics_to_neon.py
├── embed_and_store.py, query_embeddings.py
├── scrape_policy_sources.py
└── DEPLOY.md                # Deployment notes
```

(Config and generated CSVs like `forecast_*.csv`, `risk_score*.csv`, `*_updated.csv` live in project root; `node_modules/` and Firebase cache are omitted.)

---

## Setup and run

### Frontend (local)

- Open `index.html` in a browser, or serve the directory with any static server.  
- For the live app: **https://overfishing-2d415.web.app** (Firebase Hosting).

### Backend (TTS / Explain API)

- **Env:** Create `.env` with `GEMINI_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY`, `ELEVENLABS_API_KEY`, optional `ELEVENLABS_VOICE_ID`.
- **Install:** `pip install -r requirements.txt`
- **Run:** `uvicorn policy_tts_api:app --reload --port 8010`
- **Endpoints:**  
  - `POST /api/policy-explanation-audio` — policy explanation audio  
  - `POST /api/risk-explanation-audio` — risk explanation audio  
  - `GET /health`, `GET /` — health and service info  

### Pipeline (reproduce forecasts and risk)

1. Features: `python feature_agent.py` (and split/update pipeline as needed).  
2. Forecasts: `python forecast_next_5_10_years.py` → `forecast_next5years.csv`, `forecast_next10years.csv`.  
3. Risk: `python compute_risk_score.py` → `risk_score.csv`.  
4. (Optional) Risk category: `train_risk_classifier.py` → `risk_score_with_category.csv`.  
5. (Optional) PriceIndex model: `python train_model.py` → `model.joblib`, `eval_report.json`.

---

## Deploy

- **Frontend:** `npx firebase deploy --only hosting` (Hosting URL: https://overfishing-2d415.web.app).  
- **TTS API:** Deploy `policy_tts_api` to **Google Cloud Run** (e.g. `gcloud run deploy fishsave-tts-api --source . --region us-central1 --allow-unauthenticated`). Set env vars `ELEVENLABS_API_KEY` and optionally `ELEVENLABS_VOICE_ID` in the Cloud Run service.  
- Point the frontend’s `API_BASE` in `index.html` to your Cloud Run URL.

---

## License and acknowledgments

- Dataset: [Worldwide Fishing Catch Statistics 1950–2018](https://www.kaggle.com/datasets/thebumpkin/worldwide-fishing-catch-statitstics-1950-2018) (Kaggle).  
- Built for sustainability and government decision support; suitable for submission and reuse with attribution.
