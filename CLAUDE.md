@.claude/instructions.md

## REST API (Render — 2026-02-26 新增)

- **生產 URL：** `https://idea-reality-mcp.onrender.com`
- **入口：** `api/main.py`（FastAPI wrapper，直接 import scoring engine）
- **端點：**
  - `GET /health` — liveness probe
  - `POST /api/check` — body: `{idea_text, depth}` → 回傳完整 report dict
- **CORS：** 允許 mnemox.ai、mnemox-ai.github.io、localhost
- **部署：** `render.yaml`（free tier，sleep/wake acceptable）
- **PRODUCTHUNT_TOKEN：** optional，未設時 gracefully skip PH source
