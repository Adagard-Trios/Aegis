# Deploying services/medverse-ai/ to Hugging Face Spaces

This service runs on a separate HF Space (16 GB free RAM) so the
LangGraph + Chroma stack doesn't OOM Render's 512 MB free tier. The
HF Space repo is independent of this GitHub repo — pushes here don't
auto-sync there.

## One-time setup

1. **Create the Space** at <https://huggingface.co/new-space>:
   - SDK: **Docker** (critical — not Streamlit/Gradio)
   - Hardware: **CPU basic** (free, 16 GB RAM)
   - Visibility: Public (private requires HF Pro)

2. **Set required secrets** at `Settings → Variables and secrets`:
   - `GROQ_API_KEY` — your Groq API key (required)
   - `MEDVERSE_AI_KEY` — shared key the mobile + Render proxy attach in
     `X-Medverse-Ai-Key`. Required in production. Generate any 32-byte
     hex string. Set the same value in Render's `MEDVERSE_AI_KEY` env
     var and bake into mobile via `--dart-define=AI_KEY=<value>`.
   - Per-specialty keys (optional — fall back to `GROQ_API_KEY`):
     `CARDIOLOGY_EXPERT_GROQ_API_KEY`, `PULMONARY_EXPERT_GROQ_API_KEY`,
     `NEUROLOGY_EXPERT_GROQ_API_KEY`, `DERMATOLOGY_EXPERT_GROQ_API_KEY`,
     `GYNECOLOGY_EXPERT_GROQ_API_KEY`, `OCULOMETRIC_EXPERT_GROQ_API_KEY`,
     `GENERAL_PHYSICIAN_GROQ_API_KEY`.

3. **Optional env vars**:
   - `MEDVERSE_AI_CORS_ORIGINS` — comma-separated allowlist (overrides
     the default Render + localhost set). Tighten this when shipping
     to a known frontend domain.
   - `MEDVERSE_AI_RATE_PER_MIN` — sliding-window rate limit per
     `X-Medverse-Ai-Key` value (or per IP when no key). Default `30`.
     Set `0` to disable.

## Deploying code changes

After editing anything under `services/medverse-ai/`, run from the
repo root:

```bash
HF_USERNAME=nivakaran \
HF_SPACE=MedVerse \
HF_TOKEN=hf_xxx \
./scripts/deploy-hf.sh
```

The script clones the Space repo, mirrors `services/medverse-ai/` into
it, commits, and pushes — then wipes the temp dir so the embedded
token doesn't linger in `.git/config` on disk.

**Token hygiene**: generate a Write-scoped token at
<https://huggingface.co/settings/tokens>, run the script once, then
revoke the token. Don't reuse tokens across sessions — every commit
that lands in chat / logs / a screenshot is a leak.

## Verifying a deploy

After the Space flips to Running (~3–5 min for code-only changes,
~8–10 min when requirements.txt or weights changed):

```bash
SPACE_URL="https://${HF_USERNAME}-$(echo ${HF_SPACE} | tr '[:upper:]' '[:lower:]').hf.space"

# Liveness
curl "$SPACE_URL/health"

# Diagnostics — surfaces every flag, secret, ML-adapter is_loaded, +
# rate_limit_per_min so a deploy regression is one curl away.
curl "$SPACE_URL/health/diagnostics" | jq

# End-to-end agent test (requires MEDVERSE_AI_KEY if set on the Space)
curl -X POST "$SPACE_URL/api/agent/ask" \
  -H "Content-Type: application/json" \
  -H "X-Medverse-Ai-Key: $MEDVERSE_AI_KEY" \
  -d '{"specialty":"cardiology","message":"Quick assessment","snapshot":{"vitals":{"heart_rate":72,"spo2":98}}}'
```

Watch for in `/health/diagnostics`:
- `groq_client.ok: true`
- `langgraph.ok: true`
- `ml_adapters.fetal_health.is_loaded: true` (and `parkinson_screener`)
- `secrets_present.GROQ_API_KEY: true`
- `ai_key_required: true` (when MEDVERSE_AI_KEY is set on the Space)

## Troubleshooting

- **401 Unauthorized on push**: the token wasn't created with **Write**
  scope, or it was revoked. Make a fresh one.
- **Build fails with "models/.../model.pkl not found"**: weights file
  wasn't tracked by Git LFS. Run `git lfs track "*.pkl"` in the Space
  clone, re-add, push.
- **Space stays "Building" >15 min**: open the Space's Build Log tab —
  `pip install` may be hung on a wheel that needs `build-essential`.
  The Dockerfile already installs it, so this usually means a corrupt
  Docker layer cache; trigger a Factory Rebuild from Settings.
- **First /api/agent/ask hangs**: cold-start. LangGraph + Chroma init
  takes ~10 s on the first request. Subsequent calls are 3–8 s. The
  mobile app sends a /health pre-warm on app foreground to mitigate.
