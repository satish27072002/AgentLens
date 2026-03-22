# AgentLens — DigitalOcean Deployment Guide

Deploy AgentLens to DigitalOcean App Platform using your free credits.

| Component | Service | Cost |
|-----------|---------|------|
| Frontend | Static Site | FREE |
| Backend | Basic ($5/mo) | $5/mo |
| Database | Dev Database | FREE (256MB) |
| **Total** | | **~$5/mo** |

---

## Steps

1. **Push your code to GitHub** (if not already done)

2. **Go to** [cloud.digitalocean.com/apps](https://cloud.digitalocean.com/apps) → **Create App**

3. **Connect your GitHub repo** → select the `AGENTSLENS_PROJECT` repository

4. **DigitalOcean auto-detects components.** Configure them:

   **Backend (Service):**
   - Source Directory: `/backend`
   - Type: Web Service
   - Plan: Basic ($5/mo)
   - Dockerfile path: `Dockerfile`
   - HTTP Port: 8000
   - Routes: `/api`, `/health`
   - Environment variables:
     ```
     AUTH0_DOMAIN        = dev-f40hclgqhiimob42.us.auth0.com
     AUTH0_AUDIENCE      = https://api.agentlens.dev
     CORS_ORIGINS        = ${APP_URL},http://localhost:5173
     DATABASE_URL        = ${db.DATABASE_URL}
     ```

   **Frontend (Static Site):**
   - Source Directory: `/frontend`
   - Build Command: `npm install && npm run build`
   - Output Directory: `dist`
   - Routes: `/`
   - Catchall document: `index.html`
   - Environment variables:
     ```
     VITE_AUTH0_DOMAIN    = dev-f40hclgqhiimob42.us.auth0.com
     VITE_AUTH0_CLIENT_ID = u7j28n99TAxPrOpxxVbwtLId6T0ZX6mj
     VITE_AUTH0_AUDIENCE  = https://api.agentlens.dev
     VITE_API_URL         = ${APP_URL}
     ```

   **Database:**
   - Add Database → Dev Database (free)
   - Engine: PostgreSQL 16
   - Name: `db`

5. **Click Deploy** → wait ~5 minutes

6. **Update Auth0 settings** with your new app URL:
   - Auth0 Dashboard → Applications → AgentLens → Settings
   - Allowed Callback URLs: `https://your-app.ondigitalocean.app/login`
   - Allowed Logout URLs: `https://your-app.ondigitalocean.app`
   - Allowed Web Origins: `https://your-app.ondigitalocean.app`

7. **Test:** Visit `https://your-app.ondigitalocean.app` and log in

---

## Alternative: Deploy via CLI

```bash
# Install doctl
brew install doctl
doctl auth init

# Deploy using the spec file
doctl apps create --spec .do/app.yaml
```

---

## After Deployment

### Update Auth0 Callback URLs

In Auth0 Dashboard → Applications → AgentLens → Settings, add your production URLs:

- **Allowed Callback URLs:** `https://YOUR_APP.ondigitalocean.app/login`
- **Allowed Logout URLs:** `https://YOUR_APP.ondigitalocean.app`
- **Allowed Web Origins:** `https://YOUR_APP.ondigitalocean.app`

Keep the localhost entries too (comma-separated) for local development.

### Seed Data (optional)

```bash
# Find your API key in the database or create one via the Settings page
python backend/scripts/seed_data.py \
  --url https://YOUR_BACKEND_URL \
  --api-key al_your_key_here
```

### Verify Deployment

```bash
# Health check
curl https://YOUR_BACKEND_URL/health

# Should return: {"status":"ok","service":"agentlens-backend"}
```
