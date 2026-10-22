# 🏀 CourtVision

🏆 **Best AI/ML Hack — HACK(H)ER 413 (Feb 2026)**

AI-powered NBA platform for new fans: game predictions, AI scouting reports, and a fact-checker for sports-media hot takes. Built in 24 hours.

**Devpost:** https://devpost.com/software/courtvision-ydejwi

## Team
- **Arjya Misra** ([@codeArjya](https://github.com/codeArjya))
- **Ethan Au-Yeung** ([@ethancfay](https://github.com/ethancfay)) – XGBoost game-prediction model, FastAPI backend, and Gemini scouting/fact-check features
- **Zakariya Gdihi** – presentation and demo
- **Santiago Rojas Vasquez**

NBA live stats dashboard + AI predictions + media takes feed.
**Stack:** Next.js 14 · FastAPI · Gemini 1.5 Flash · Supabase · Upstash Redis · XGBoost · balldontlie
---
## 🚀 Full Setup Walkthrough
Follow these steps to spin up the entire Full Stack application, complete with Live Data ingestion and the Machine Learning prediction pipeline.
### 1. Supabase Setup
1. Create a free project at [supabase.com](https://supabase.com).
2. Go to **SQL Editor** and run the full SQL block from `prompt.md` to create the tables (`games`, `predictions`, `player_cards`, `media_takes`, etc.).
3. Copy your **Project URL** and **service_role key** from Settings → API.
### 2. Upstash Redis Setup
1. Create a free Redis database at [upstash.com](https://upstash.com).
2. Copy the **UPSTASH_REDIS_REST_URL** and **UPSTASH_REDIS_REST_TOKEN**.
### 3. Environment Variables
#### Backend
Navigate to the backend directory and set up your environment:
```bash
cd backend
cp .env.example .env
```
Fill in the following values in your new `.env` file:
- `GEMINI_API_KEY`: Your Google Gemini API Key.
- `SUPABASE_URL`: Your Supabase Project URL.
- `SUPABASE_SERVICE_KEY`: Your Supabase Service Role Key.
- `UPSTASH_REDIS_REST_URL`: Your Upstash REST URL.
- `UPSTASH_REDIS_REST_TOKEN`: Your Upstash REST Token.
#### Frontend
Navigate to the frontend directory:
```bash
cd frontend
cp .env.local.example .env.local
```
Fill in the following values:
- `NEXT_PUBLIC_API_URL`: `http://localhost:8000` (for local development)
- `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase Project URL.
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase Anon Key.
---
### 4. Backend Installation & ML Initialization
To power the AI and ML models, you need to install the dependencies, fetch the real historical data, and train the XGBoost models.
**1. Install Python Dependencies**
```bash
cd backend
pip install -r requirements.txt
```
**2. Bootstrap Database Tables**
Fetch all current NBA players and the last 3 seasons of historical game data necessary to train the AI:
```bash
python -m app.scripts.bootstrap_players
python -m app.scripts.bootstrap_historical
```
**3. Train the ML Pipeline**
Run the XGBoost training script. This will extract the 15 requested feature sets from the historical database and generate the model artifacts (saved in `app/ml/artifacts/`):
```bash
python -m app.ml.train
```
**4. Run the API Server**
Start the FastAPI background scheduler and live endpoints:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
You can verify it's running cleanly by checking: http://localhost:8000/health
---
### 5. Frontend Development
Now that the backend is streaming live predictions, spin up the React interface:
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at: http://localhost:3000
---
## 🛠️ API Routes Overview
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | API and ML Model loaded status |
| GET | `/api/games` | Today's live NBA games (Hit balldontlie → Cache → DB) |
| GET | `/api/predictions/{game_id}` | XGBoost AI prediction for a specific game |
| POST | `/api/player-card` | Gemini-powered AI scouting report for a player |
| GET | `/api/takes` | Live feed of all media takes |
| POST | `/api/takes/vote` | Vote agree/disagree on a media take |
| POST | `/api/admin/trigger-ingest` | Manually run the APScheduler live ingest job |
| POST | `/api/admin/trigger-retrain` | Manually run the XGBoost retraining job |
---
## 🌩️ Deployment
### Backend → Railway
1. Push your repository to GitHub.
2. Create a new Railway project → connect repo → set root to `backend/`.
3. Load all backend environment variables (`GEMINI_API_KEY`, etc.) into Railway.
4. Railway will auto-detect the provided `railway.toml` and run `uvicorn`.
### Frontend → Vercel
1. Create a Vercel project → connect repo → set root to `frontend/`.
2. Load all frontend environment variables. Ensure `NEXT_PUBLIC_API_URL` points to your active Railway domain.
3. Deploy!
