# Free Deployment Guide

Step-by-step instructions for deploying to 5 free hosting platforms.
No credit card required for any of these (within free tier limits).

---

## Before You Deploy

### Choose your LLM strategy

| Strategy | Cost | Latency | Setup |
|----------|------|---------|-------|
| **Anthropic Claude** (Haiku) | ~$0.001/query | Fast | Set `ANTHROPIC_API_KEY` |
| **Ollama** (llama3 local) | Free | Slower | Needs dedicated VM |
| **Mock** (testing only) | Free | Instant | No key needed |

For cloud deployments, Anthropic Haiku is the easiest. For fully free, see the
Fly.io section which can run Ollama alongside the app.

---

## Option 1: Railway.app ⭐ Recommended

**Free tier**: 500 hours/month, 512 MB RAM, 1 GB disk, custom domain included.

### Steps

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# In your project directory
cd mcp-assistant
railway init          # creates a new Railway project
railway up            # deploys from current directory
```

### Set environment variables

In Railway dashboard → your project → Variables:

```
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001
EMBEDDING_MODEL=all-MiniLM-L6-v2
DEBUG=false
INTERNAL_API_KEY=your-random-secret
```

### Custom domain

Railway dashboard → Settings → Domains → Generate Domain
Your app will be live at: `https://mcp-assistant-production.up.railway.app`

### Persistent storage note

Railway free tier does NOT persist files between deploys. The vector store
will be re-indexed on every startup from `knowledge_base/`. This is fine for
small doc sets. For persistence, commit your `vector_store/` to the repo
or upgrade to Railway's $5/mo hobby plan with volumes.

---

## Option 2: Render.com

**Free tier**: 750 hours/month, spins down after 15 min inactivity (cold start ~30s).

### Steps

1. Push code to GitHub:
   ```bash
   git init && git add . && git commit -m "initial commit"
   gh repo create mcp-assistant --public --source=. --push
   ```

2. Go to [render.com](https://render.com) → New → Web Service

3. Connect your GitHub repo

4. Render auto-detects `render.yaml` — review settings

5. Under **Environment** tab, add:
   ```
   ANTHROPIC_API_KEY = sk-ant-...
   INTERNAL_API_KEY  = your-random-secret
   ```

6. Click **Deploy**

### Persistent disk (optional, $1/mo)

In `render.yaml` the disk is already configured:
```yaml
disk:
  name: data
  mountPath: /app/vector_store
  sizeGB: 1
```
This keeps your ChromaDB data between deploys.

---

## Option 3: Fly.io

**Free tier**: 3 shared VMs (256 MB each), 3 GB total storage, 160 GB bandwidth.
Best option for running **Ollama locally** (fully free, no API key).

### Deploy app only (with Anthropic key)

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh
fly auth signup   # or fly auth login

# In project directory
fly launch        # auto-detects Dockerfile, creates fly.toml

# Set secrets
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly secrets set LLM_PROVIDER=anthropic
fly secrets set INTERNAL_API_KEY=your-secret

# Deploy
fly deploy

# Check logs
fly logs
```

### Deploy with Ollama (100% free)

```bash
# Create a larger VM for Ollama (needs ~4GB RAM for llama3)
fly launch --vm-size shared-cpu-4x

fly secrets set LLM_PROVIDER=ollama
fly secrets set OLLAMA_BASE_URL=http://localhost:11434

# SSH into VM and pull model
fly ssh console
ollama pull llama3   # downloads ~4GB
```

Add to `fly.toml`:
```toml
[processes]
  app = "bash -c 'ollama serve & uvicorn main:app --host 0.0.0.0 --port 8080'"
```

### Persistent volume

```bash
fly volumes create mcp_data --size 1   # 1 GB free
```

Add to `fly.toml`:
```toml
[mounts]
  source = "mcp_data"
  destination = "/app/vector_store"
```

---

## Option 4: Hugging Face Spaces

**Free tier**: Always-on CPU, 16 GB RAM, 50 GB disk. No cold starts.
Best for demos — public URL, shareable.

### Steps

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Choose **Docker** as the SDK
3. Upload all files (or link GitHub repo)
4. Add secrets in **Settings → Repository secrets**:
   ```
   ANTHROPIC_API_KEY = sk-ant-...
   ```
5. HF Spaces runs the Dockerfile automatically

### Note on port

HF Spaces expects port `7860`. Update your start command:
```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

Or add to `Dockerfile`:
```dockerfile
ENV PORT=7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
```

---

## Option 5: Google Cloud Run

**Free tier**: 2M requests/month, 360K CPU-seconds, 180K GB-seconds memory.

### Steps

```bash
# Install gcloud CLI and authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Build and push container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/mcp-assistant

# Deploy to Cloud Run
gcloud run deploy mcp-assistant \
  --image gcr.io/YOUR_PROJECT_ID/mcp-assistant \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars "LLM_PROVIDER=anthropic,LLM_MODEL=claude-haiku-4-5-20251001" \
  --set-secrets "ANTHROPIC_API_KEY=anthropic-key:latest"
```

### Store secrets in Secret Manager

```bash
echo -n "sk-ant-..." | gcloud secrets create anthropic-key --data-file=-
```

### Persistent storage

Cloud Run is stateless. Use Google Cloud Storage for ChromaDB persistence:
```bash
# Mount GCS bucket as volume (Cloud Run v2)
gcloud run deploy mcp-assistant \
  --add-volume name=chroma,type=cloud-storage,bucket=YOUR_BUCKET \
  --add-volume-mount volume=chroma,mount-path=/app/vector_store
```

---

## Post-Deploy Checklist

After deploying to any platform:

- [ ] Visit `https://your-app.com/health` — should return `{"status": "healthy"}`
- [ ] Visit `https://your-app.com/docs` — Swagger UI loads
- [ ] Upload a test document via `POST /api/v1/documents/upload`
- [ ] Run a test query via `POST /api/v1/qa/ask`
- [ ] Check logs for any errors

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | `anthropic` | `anthropic` or `ollama` |
| `LLM_MODEL` | No | `claude-haiku-4-5-20251001` | Model name |
| `ANTHROPIC_API_KEY` | If using Anthropic | — | Your API key |
| `OLLAMA_BASE_URL` | If using Ollama | `http://localhost:11434` | Ollama endpoint |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Local embedding model |
| `CHROMA_PERSIST_DIR` | No | `./vector_store` | ChromaDB storage path |
| `TOP_K_RESULTS` | No | `5` | Chunks retrieved per query |
| `SIMILARITY_THRESHOLD` | No | `0.3` | Min relevance score (0–1) |
| `MAX_CONTEXT_TOKENS` | No | `3000` | Token budget for context |
| `MEMORY_MAX_TURNS` | No | `10` | Conversation history length |
| `INTERNAL_API_KEY` | Recommended | `dev-secret-key` | Protects `/admin` endpoints |
| `DEBUG` | No | `false` | Enable debug mode + hot reload |

---

## Monitoring & Logs

All platforms expose logs. Key things to watch:

```
✓ Embedding model loaded        ← sentence-transformers ready
✓ VectorStore ready             ← ChromaDB connected
✓ Auto-indexed N documents      ← startup indexing complete
✓ MCP-Context-Assistant ready   ← app fully started
```

Errors to look out for:
- `LLM init failed` — check API key and provider config
- `sentence-transformers unavailable` — using hash fallback (still works)
- `Ollama not running` — start `ollama serve` or switch to Anthropic
