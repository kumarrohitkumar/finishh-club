# Deploying

Everything is prepared. Three steps, about 8 minutes, all free.

---

## 1. API → Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/kumarrohitkumar/finishh-club)

Click the button. It reads `render.yaml`, so the Docker build, the health check
and the **Singapore** region are already set.

Sign in with GitHub. Then it asks for four environment variables — the exact
values are in **`RENDER_ENV_VARS.txt`** on your machine (gitignored):

| Variable | Value |
|---|---|
| `DATABASE_URL` | the Neon **Singapore** string |
| `GROQ_API_KEY` | your Groq key |
| `GROQ_MODEL` | `openai/gpt-oss-20b` |
| `ALLOWED_ORIGINS` | leave empty — filled in at step 3 |

You get a URL like `https://finishh-api.onrender.com`.

**Check it worked:** open `<your-url>/health` — it should return `{"status":"ok"}`.
The first request can take ~50 seconds while the free instance wakes.

---

## 2. Frontend → Vercel

Go to **vercel.com** → **Add New** → **Project** → import `finishh-club`.

Two settings matter:

| Setting | Value |
|---|---|
| **Root Directory** | `frontend` ← easy to miss, and nothing works without it |
| Framework | Vite (detected automatically) |

Add one environment variable:

```
VITE_API_URL = https://your-api.onrender.com
```

Deploy. You get a URL like `https://finishh-club.vercel.app`.

> Vite bakes `VITE_API_URL` in **at build time**. If you change it later you
> must redeploy, not just restart.

---

## 3. Connect the two

Back in Render → your service → **Environment**:

```
ALLOWED_ORIGINS = https://finishh-club.vercel.app
```

Save. Render restarts.

Without this the browser blocks every request from your site to the API, and
the page looks broken with no visible error except in the console.

---

## 4. Daily data refresh

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

```
Name:  DATABASE_URL
Value: the same Neon Singapore string
```

`.github/workflows/refresh.yml` then runs every weekday at 23:30 IST — appends
the day's NAV and recomputes every meter. Nothing else to configure.

---

## Afterwards

- **Delete `RENDER_ENV_VARS.txt`.** It holds your database password in plain text
- **Delete the old Ohio Neon project** at console.neon.tech (`divine-dust-05046500`)
- **Delete `.env.local.ohio-backup`** once the Singapore database is proven

---

## What to expect on the free tier

| | |
|---|---|
| First visit after 15 min idle | ~50 seconds while Render wakes |
| After that | fast — the connection pool is already warm |
| Neon | suspends when idle too, adds ~500 ms to the first query |
| Cost | ₹0, except Groq which is also free |

The cold start is the one real downside. For a personal app it is fine. Paying
Render $7/month removes it if it ever becomes annoying.

---

## If something breaks

| Symptom | Cause |
|---|---|
| Site loads, no data | `ALLOWED_ORIGINS` missing or wrong — check the browser console for a CORS error |
| `/health` 404s | Root Directory not set to `frontend` on Vercel, or the Render build failed |
| Everything times out at first | Normal. Free instance waking. Wait 50 seconds |
| Isaa says out of capacity | Groq's 200k tokens/day is spent. It resets |
| Data stops updating | GitHub disables scheduled workflows after 60 days of no repo activity |
