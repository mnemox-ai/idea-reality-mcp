# 10 Ideas Scan Results — DEV.to Article Data

Re-scanned 2026-03-01 via mnemox.ai/check (Deep mode, English)
After relevance filter fix (commit d351eef)

## Summary Table

| # | Idea | Signal | GitHub Repos | HN Posts | npm Pkgs | Top Stars | Top Competitor |
|---|------|--------|-------------|----------|----------|-----------|---------------|
| 1 | AI-powered code review automation tool | **74** 🔴 | 5,578 | 128 | 1,592,236 | 53,965 | go-gitea/gitea |
| 2 | open source feature flag service | **74** 🔴 | 887 | 17 | 212,912 | 13,230 | Unleash/unleash |
| 3 | AI chatbot customer support open source | **74** 🔴 | 6,912 | 24 | 135,063 | 38,968 | deepset-ai/haystack |
| 4 | markdown note taking app AI search | **74** 🔴 | 919 | 42 | 1,935,685 | 63,332 | toeverything/AFFiNE |
| 5 | LLM API gateway proxy router | **74** 🔴 | 2,048 | 38 | 533,831 | 37,289 | BerriAI/litellm |
| 6 | AI agent memory layer persistent context | **74** 🔴 | 2,975 | 250 | 125,597 | 37,352 | Langchain-Chatchat |
| 7 | MCP server database query natural language | **74** 🔴 | 659 | 20 | 420,668 | 22,805 | vanna-ai/vanna |
| 8 | AI changelog generator git commits | **66** 🟡 | 365 | 1 | 228,135 | 11,440 | orhun/git-cliff |
| 9 | MCP server CI CD pipeline debugging | **74** 🔴 | 1,770 | 53 | 285,708 | 2,001 | Coding-Solo/godot-mcp |
| 10 | bluetooth pet collar firmware ESP32 | **39** 🟢 | 10 | 0 | 2,804 | 16 | PetkitW5BLEMQTT |

## Observations

### Signal Distribution
- **#1-7, #9 = Signal 74** — Almost all AI/dev tools hit the ceiling
- **#8 = Signal 66** — Still HIGH, but slightly less competitive (only 1 HN post, 365 repos)
- **#10 = Signal 39 (MEDIUM)** — The only green light. 10 repos, 0 HN, top repo has 16 stars

### Key Insight: LLM Keyword Extraction Variability
- Signal varies between runs because Haiku 4.5 generates different keywords each time
- Previous scan showed #6-9 at 30-33; this scan shows 66-74
- The evidence numbers (repos, HN, npm) differ significantly between runs
- For the article: use single-run data consistently, note that scores are approximate

### Relevance Verification (post-filter fix)
All 10 ideas now show relevant Similar Projects:
- ✅ #1: analysis-tools-dev/static-analysis, semgrep, phpstan, reviewdog
- ✅ #2: Flagsmith/flagsmith, microsoft/FeatureFlightingManagement, Unleash
- ✅ #3: deepset-ai/haystack, wechaty/wechaty, RasaHQ/rasa
- ✅ #4: sheshbabu/zen (markdown notes), toeverything/AFFiNE (63K★)
- ✅ #5: BerriAI/litellm (37K★), Portkey-AI/gateway, coaidev/coai
- ✅ #6: Langchain-Chatchat (37K★), labring/FastGPT (27K★)
- ✅ #7: vanna-ai/vanna (23K★, text-to-SQL), dataease/SQLBot
- ✅ #8: orhun/git-cliff (11K★), conventional-changelog (8K★)
- ✅ #9: Coding-Solo/godot-mcp (MCP server), datadog-ci (CI/CD)
- ✅ #10: PetkitW5BLEMQTT (pet IoT), esp32_freertos

### Article Classification (updated)
- 🔴 **Don't bother (74)**: #1 code review, #2 feature flags, #3 chatbot, #4 notes, #5 LLM gateway, #6 agent memory, #7 MCP+DB, #9 MCP+CI/CD
- 🟡 **Crowded but has gaps (66)**: #8 changelog generator (only 1 HN post, 365 repos — niche within a niche)
- 🟢 **Build it (39)**: #10 pet collar (10 repos, 0 HN, truly empty space)

### Article Highlight Screenshots
1. **#5 LLM API gateway** — Signal 74, litellm 37K★, Portkey 11K★ = ultra-crowded
2. **#10 bluetooth pet collar** — Signal 39, 0 HN posts, top repo 16★ = wide open
3. **#8 changelog generator** — Signal 66, git-cliff 11K★ but only 1 HN post = room for AI angle

### Bug Status
- ~~Badge bug~~ — NOT a bug. Previous screenshots caught gauge mid-animation (showing intermediate values). Badge uses API response directly and is always correct.
- Signal variability — Known limitation of LLM keyword extraction. Each run generates different keywords.

## Screenshots
All 10 screenshots captured in Claude Code conversation (gauge + evidence + top 2 similar projects each).
Screenshots taken with 42+ second wait (30s API + 12s animation) for stable gauge values.
