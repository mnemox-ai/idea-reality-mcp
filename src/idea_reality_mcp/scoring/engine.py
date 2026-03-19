"""Scoring engine — synthesize reality_signal from source data."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Literal

from ..sources.github import GitHubResults
from ..sources.hn import HNResults
from ..sources.npm import NpmResults
from ..sources.pypi import PyPIResults
from ..sources.producthunt import ProductHuntResults
from ..sources.stackoverflow import StackOverflowResults
from .synonyms import INTENT_ANCHORS, SYNONYMS

# ---------------------------------------------------------------------------
# Keyword extraction constants
# ---------------------------------------------------------------------------

# Common English stop words
STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "don", "now", "and", "but", "or", "if", "while", "that", "which",
    "what", "this", "these", "those", "am", "it", "its", "i", "me", "my",
    "we", "our", "you", "your", "he", "him", "his", "she", "her", "they",
    "them", "their", "who", "whom", "up", "about", "like", "want", "get",
    "new", "also", "one", "two", "way", "many", "much", "well", "still",
    "even", "back", "any", "let", "really", "already", "every",
})

# Stage A boilerplate filter — too generic to anchor a meaningful query.
# Tech keywords (TECH_KEYWORDS) always bypass this filter.
GENERIC_WORDS = frozenset({
    # Original v0.2
    "build", "make", "create", "app", "tool", "using", "use", "thing",
    "something", "platform", "system", "service", "project", "idea",
    "solution", "product", "software", "program", "application",
    # Stage A additions (v0.3) — hard-filter per plan
    "ai", "engine", "framework", "library", "helper", "manager",
    "builder", "generator",
    # Marketing filler
    "powered", "based", "driven", "enabled", "smart", "intelligent",
    "automatic", "automated", "simple", "easy", "better", "best",
    "good", "great", "modern", "fast", "lightweight",
    # Meta words
    "open", "feature", "support", "custom", "provide", "allow",
    "enable", "help", "version", "free",
})

# Compound terms that should be kept together as a single token.
COMPOUND_TERMS = [
    "machine learning", "deep learning", "natural language processing",
    "computer vision", "web app", "web application", "mobile app",
    "command line", "real time", "open source", "data science",
    "neural network", "reinforcement learning", "large language model",
    "artificial intelligence", "api gateway", "message queue",
    "task manager", "file manager", "code review", "code editor",
    "package manager", "version control", "continuous integration",
    "object detection", "image recognition", "text to speech",
    "speech to text", "time series", "knowledge graph",
    "supply chain", "social media", "e commerce", "ecommerce",
    # v0.3 additions
    "model context protocol", "tool calling", "prompt engineering",
    "vector search", "semantic search", "knowledge base",
    "red teaming", "function calling", "retrieval augmented",
    "customer service", "push notification", "job queue",
    "task queue", "log aggregation", "stock trading",
    "fine tuning",
]

# Technology / framework keywords — get priority in ranking and bypass
# GENERIC_WORDS filter even if they would otherwise be excluded.
TECH_KEYWORDS = frozenset({
    "react", "vue", "angular", "svelte", "nextjs", "nuxt", "remix",
    "python", "javascript", "typescript", "rust", "go", "golang",
    "java", "kotlin", "swift", "ruby", "php", "elixir", "scala",
    "django", "flask", "fastapi", "express", "nestjs", "rails",
    "docker", "kubernetes", "terraform", "ansible", "aws", "gcp", "azure",
    "postgres", "postgresql", "mysql", "mongodb", "redis", "sqlite",
    "graphql", "grpc", "rest", "websocket", "mqtt",
    "tensorflow", "pytorch", "keras", "scikit", "pandas", "numpy",
    "openai", "anthropic", "langchain", "llamaindex", "ollama",
    "blockchain", "ethereum", "solana", "bitcoin",
    "electron", "tauri", "flutter", "ionic",
    "mcp", "onnx", "llm", "rag", "cli", "api", "sdk", "orm",
    # v0.3 additions
    "otel", "opentelemetry", "langfuse", "weave", "arize",
    "weaviate", "pinecone", "chroma", "qdrant", "faiss",
    "llamafile", "vllm", "litellm", "guidance", "dspy",
})

# Chinese tech term → English equivalent (v0.3: mixed-language support).
# Applied before tokenisation so Chinese intent is preserved.
# IMPORTANT: Iteration is sorted by key length (longest first) at usage site
# to prevent shorter keys from clobbering longer compound matches.
CHINESE_TECH_MAP: dict[str, str] = {
    # AI / LLM core
    "監控": "monitoring", "監測": "monitoring", "告警": "alerting",
    "評測": "evaluation", "評估": "evaluation", "評分": "scoring",
    "模型": "model", "大模型": "llm", "大語言模型": "llm",
    "微調": "finetuning", "訓練": "training",
    "推理": "inference", "生成": "generation",
    "向量": "embedding", "嵌入": "embedding",
    "檢索": "retrieval", "搜索": "search", "搜尋": "search",
    "護欄": "guardrails", "安全": "safety",
    # Agent / workflow
    "代理": "agent", "智能體": "agent",
    "助手": "assistant", "機器人": "bot",
    "自動化": "automation", "自動": "automation",
    "工作流": "workflow", "流水線": "pipeline",
    # Developer
    "爬蟲": "scraping", "爬取": "scraping", "抓取": "scraping",
    "命令行": "cli", "命令列": "cli", "終端": "terminal",
    "資料庫": "database", "數據庫": "database",
    "部署": "deployment", "佈署": "deployment",
    "測試": "testing", "基準": "benchmark",
    "程式碼": "code", "代碼": "code",
    "編輯器": "editor",
    "日誌": "logging",
    "追蹤": "tracking",  # General "tracking", not infra "tracing"
    "排程": "scheduling", "定時": "cron",
    "快取": "caching", "緩存": "caching",
    "遷移": "migration", "升級": "upgrade",
    "開發": "development", "框架": "framework",
    "前端": "frontend", "後端": "backend",
    "介面": "interface", "套件": "package",
    "串接": "integration", "整合": "integration",
    # Business / SaaS
    "電商": "ecommerce", "商城": "ecommerce", "網店": "ecommerce",
    "後台": "backend", "管理": "management",
    "客戶關係": "crm",  # Compound: must appear before 客戶
    "客服": "customer service", "客戶服務": "customer service",
    "付款": "payment", "支付": "payment", "結帳": "checkout",
    "金流": "payment", "收款": "payment",
    "訂閱": "subscription", "帳單": "billing",
    "通知": "notification", "推播": "notification",
    "預約": "booking", "預訂": "reservation",
    "庫存": "inventory",
    "發票": "invoice",
    "報表": "reporting", "報告": "reporting",
    "權限": "authorization", "認證": "authentication",
    "訂單": "order", "訂餐": "food ordering",
    "會員": "membership", "註冊": "registration",
    "記帳": "accounting", "對帳": "reconciliation",
    "線上": "online", "網路": "web",
    # Content / media
    "數據分析": "data analytics",  # Compound: must appear before 分析
    "分析": "analysis", "儀表板": "dashboard",
    "聊天": "chatbot", "對話": "chat",
    "知識庫": "knowledge base",
    "摘要": "summarization", "翻譯": "translation",
    "分類": "classification", "推薦": "recommendation",
    "標註": "annotation",
    "字幕": "subtitle", "轉錄": "transcription",
    "社群媒體": "social media",  # Compound: must appear before 社群
    "社群": "social", "媒體": "media",
    "發文": "posting", "貼文": "post",
    # Domain specific
    "股票": "stock", "交易": "trading", "金融": "fintech",
    "加密貨幣": "cryptocurrency", "虛擬貨幣": "cryptocurrency",
    "教育": "education", "課程": "course",
    "醫療": "healthcare", "健康": "health", "健保": "health insurance",
    "物流": "logistics", "運送": "shipping", "外送": "delivery",
    "地圖": "map", "定位": "geolocation",
    "機票": "flight booking", "旅遊": "travel",
    "餐廳": "restaurant", "美食": "food",
    "健身": "fitness",
    "價格": "price", "比價": "price comparison",
    "租屋": "rental", "房屋": "housing",
    "食譜": "recipe", "烹飪": "cooking",
    # Cross-domain general-purpose verbs / concepts
    "文件": "document", "文檔": "document",
    "智慧": "smart", "問診": "consultation",
    "模擬": "simulation", "模擬器": "simulator",
    "辨識": "recognition", "識別": "recognition",
    "偵測": "detection", "檢測": "detection", "檢查": "inspection",
    "查詢": "search", "搜尋引擎": "search engine",
    "影像": "image", "圖片": "image", "照片": "photo",
    "計算": "calculation", "計算器": "calculator",
    "學習": "learning", "教學": "teaching", "練習": "practice",
    "考試": "exam", "出題": "quiz", "作業": "homework",
    "設計": "design", "繪圖": "drawing", "繪製": "drawing",
    "轉換": "conversion", "轉檔": "conversion",
    "收集": "collection", "蒐集": "collection",
    "維護": "maintenance", "修復": "repair",
    "配方": "formula", "比較": "comparison",
    "媒合": "matching", "配對": "matching",
    "繳費": "payment",
    "數據": "data", "資料": "data",
    "產品": "product",
    "品質": "quality", "檢驗": "inspection",
    # Extended domains
    "遊戲": "game", "手遊": "mobile game", "電競": "esports",
    "音樂": "music", "樂譜": "music score", "作曲": "composition",
    "畫作": "artwork", "書法": "calligraphy", "藝術": "art",
    "動物": "animal", "寵物": "pet",
    "農業": "agriculture", "農場": "farm", "灌溉": "irrigation",
    "太空": "space", "衛星": "satellite", "軌道": "orbit",
    "物理": "physics", "化學": "chemistry", "實驗": "experiment",
    "量子": "quantum", "分子": "molecular",
    "法律": "legal", "合約": "contract", "律師": "lawyer",
    "判決": "court ruling", "案件": "case",
    "中醫": "tcm", "針灸": "acupuncture", "穴位": "acupoint",
    "藥材": "herbs", "中藥": "herbal medicine", "處方": "prescription",
    "病歷": "medical record", "掛號": "appointment",
    "佛教": "buddhism", "冥想": "meditation",
    "教堂": "church", "宗教": "religion", "經文": "scripture",
    "選舉": "election", "民調": "poll", "公文": "official document",
    "市政": "municipal", "報修": "maintenance request",
    "工廠": "factory", "設備": "equipment", "產線": "production line",
    "供應鏈": "supply chain",
    "社區": "community", "裝修": "renovation",
    # Common education / science
    "數學": "math", "國小": "elementary school",
    "互動": "interactive",
    "溯源": "traceability",
    "家教": "tutor", "導師": "mentor",
    "元素": "element",
}


def extract_keywords(idea_text: str) -> list[str]:
    """Extract search query variants — Stage A/B/C pipeline (v0.3).

    Stage A: Clean input, map Chinese terms, hard-filter boilerplate.
    Stage B: Detect intent anchors (1–2 key intent signals).
    Stage C: Synonym expansion + query template generation (3–8 queries).

    Returns:
        List of 3–8 query strings, intent-anchored and synonym-expanded.
    """
    text = idea_text.strip()

    # --- Stage A: Chinese/mixed-language mapping -----------------------------
    # Sort by key length (longest first) so compound Chinese terms like
    # 客戶關係 are matched before shorter substrings like 客戶.
    for zh, en in sorted(CHINESE_TECH_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if zh in text:
            text = text.replace(zh, f" {en} ")

    lowered = text.lower()

    # Normalize hyphens so "fine-tuning" matches compound "fine tuning",
    # "e-commerce" matches "e commerce", "real-time" matches "real time", etc.
    lowered = lowered.replace("-", " ")

    # Extract compound terms before stripping punctuation
    found_compounds: list[str] = []
    remaining = lowered
    for compound in sorted(COMPOUND_TERMS, key=len, reverse=True):
        if compound in remaining:
            found_compounds.append(compound)
            remaining = remaining.replace(compound, " ")

    # Tokenise: strip non-alphanumeric, minimum 2 chars
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", remaining)
    tokens = [w for w in cleaned.split() if len(w) > 1]

    # Stage A hard filter: STOP_WORDS + GENERIC_WORDS
    # Tech keywords and intent anchors always bypass the generic filter.
    clean_tokens = [
        w for w in tokens
        if w in TECH_KEYWORDS
        or w in INTENT_ANCHORS
        or (w not in STOP_WORDS and w not in GENERIC_WORDS)
    ]

    tech_tokens = [w for w in clean_tokens if w in TECH_KEYWORDS]
    non_tech = [w for w in clean_tokens if w not in TECH_KEYWORDS]

    # All meaningful tokens: compounds first, tech next, then others
    all_tokens: list[str] = found_compounds + tech_tokens + non_tech

    if not all_tokens:
        # Fallback: strip any remaining non-ASCII chars and use whatever survives.
        # Avoids returning raw Chinese text as queries (would fail on English search engines).
        ascii_fallback = re.sub(r"[^a-zA-Z0-9\s]", " ", idea_text.lower()).strip()
        ascii_tokens = [w for w in ascii_fallback.split() if len(w) > 1 and w not in STOP_WORDS]
        if ascii_tokens:
            return [" ".join(ascii_tokens[:5])] * 3
        return [idea_text.strip()[:80]] * 3

    # --- Stage B: Intent anchor detection ------------------------------------
    anchors: list[str] = []
    for token in all_tokens:
        if token in INTENT_ANCHORS and token not in anchors:
            anchors.append(token)
            if len(anchors) >= 2:
                break

    # Non-anchor tokens to combine with anchors
    non_anchor = [t for t in all_tokens if t not in anchors]

    # --- Stage C: Query template generation ----------------------------------
    queries: list[str] = []

    def _add(q: str) -> None:
        q = q.strip()
        if q and q not in queries:
            queries.append(q)

    if anchors:
        anchor = anchors[0]
        # Primary keyword: first non-anchor tech token, then any non-anchor
        tech_non_anchor = [t for t in tech_tokens if t not in anchors]
        primary_candidates = tech_non_anchor + [t for t in non_anchor if t not in tech_tokens]
        primary = primary_candidates[0] if primary_candidates else ""

        # Template 1: anchor + primary keyword
        if primary:
            _add(f"{anchor} {primary}")
        else:
            _add(anchor)

        # Template 2: anchor + top non-anchor tokens (up to 3)
        top_ctx = " ".join(dict.fromkeys(non_anchor[:3]))
        if top_ctx:
            _add(f"{anchor} {top_ctx}")

        # Template 3: domain-first query (non-anchor tokens + anchor)
        # Helps non-tech domains where domain nouns (legal, medical) are more
        # descriptive than the action anchor (automation, analysis, search).
        if len(non_anchor) >= 2:
            _add(f"{' '.join(non_anchor[:3])} {anchor}")
        elif primary:
            _add(f"{primary} {anchor}")

        # Template 4: anchor + primary + github (for GitHub search)
        if primary:
            _add(f"{anchor} {primary} github")

        # Template 5-6: synonym expansion
        # Skip if synonym already contains the primary word (avoids "redis redis")
        syns = SYNONYMS.get(anchor, [])
        if primary:
            for syn in syns[:2]:
                if primary not in syn.split():
                    _add(f"{syn} {primary}")
                else:
                    _add(syn)
        else:
            for syn in syns[:2]:
                _add(syn)

        # Template 7: second anchor if present (always include primary for context)
        if len(anchors) > 1:
            anchor2 = anchors[1]
            if primary:
                _add(f"{anchor} {anchor2} {primary}")
                _add(f"{anchor2} {primary}")
            else:
                _add(f"{anchor} {anchor2}")

        # Template 8: registry-optimised (anchor + tech keyword, no noise)
        if tech_non_anchor:
            _add(f"{anchor} {tech_non_anchor[0]}")

    else:
        # No anchor found — fall back to ranked-token approach (cleaner than v0.2)
        ranked = tech_tokens + sorted(set(non_tech), key=lambda w: (-len(w), w))
        if found_compounds:
            ranked = [found_compounds[0]] + ranked
        ranked = list(dict.fromkeys(ranked))

        _add(" ".join(ranked[:5]))
        _add(" ".join(ranked[:3]))
        _add(" ".join(ranked[:2]))
        if tech_tokens:
            _add(" ".join(tech_tokens[:2]))
        # When few tokens remain, add individual tokens for query variety
        for token in ranked[:3]:
            _add(token)

    # Ensure minimum 3, cap at 8
    while len(queries) < 3:
        queries.append(queries[0] if queries else idea_text.strip()[:80])

    return queries[:8]


# ---------------------------------------------------------------------------
# Source-specific score functions — log-curve continuous scoring
# score = min(100, k * ln(1 + count))
# k calibrated per source via least-squares on target calibration points.
# ---------------------------------------------------------------------------

_K_GITHUB_REPO = 95 / math.log(1001)   # ~13.75  | 1→10, 50→54, 200→73, 1000→95
_K_GITHUB_STAR = 95 / math.log(10001)   # ~10.31  | 10→25, 500→64, 1000→71, 10000→95
_K_HN = 95 / math.log(101)             # ~20.58  | 1→14, 15→57, 30→71, 100→95
_K_NPM_PYPI = 95 / math.log(501)       # ~15.28  | 1→11, 20→47, 100→71, 500→95
_K_PH = 95 / math.log(101)             # ~20.58  | 1→14, 10→49, 30→71, 100→95
_K_SO = 95 / math.log(201)             # ~17.91  | 1→12, 20→54, 50→71, 200→95


def _log_score(count: int, k: float) -> int:
    """Continuous log-curve scoring: min(100, round(k * ln(1 + count)))."""
    if count <= 0:
        return 0
    return min(100, round(k * math.log(1 + count)))


def _github_repo_score(count: int) -> int:
    return _log_score(count, _K_GITHUB_REPO)


def _github_star_score(max_stars: int) -> int:
    return _log_score(max_stars, _K_GITHUB_STAR)


def _hn_score(mentions: int) -> int:
    return _log_score(mentions, _K_HN)


def _npm_score(count: int) -> int:
    """Score npm package count."""
    return _log_score(count, _K_NPM_PYPI)


def _pypi_score(count: int) -> int:
    """Score PyPI package count."""
    return _log_score(count, _K_NPM_PYPI)


def _ph_score(count: int) -> int:
    """Score Product Hunt product count."""
    return _log_score(count, _K_PH)


def _so_score(count: int) -> int:
    """Score Stack Overflow question count."""
    return _log_score(count, _K_SO)


def _filter_relevant_similars(
    similars: list[dict], idea_text: str, keywords: list[str]
) -> list[dict]:
    """Filter out similar projects that don't match any idea keyword.

    Prevents high-star repos from broad keyword matches (e.g. 'natural language')
    from appearing as "similar" when they have nothing to do with the idea.

    Uses a two-tier approach:
    - "Strong match" = 2+ keyword hits → definitely relevant
    - "Weak match" = 1 keyword hit → relevant only if the word is 5+ chars
    - No match → fallback (shown last)
    """
    if not similars:
        return similars

    # Build a set of check-words from idea text + keywords (lowercased, 4+ chars)
    idea_words = set()
    for word in idea_text.lower().split():
        if len(word) >= 4:
            idea_words.add(word)
    for kw in keywords:
        for word in kw.lower().split():
            if len(word) >= 4:
                idea_words.add(word)

    # Remove generic words that match everything (tech + common)
    generic = {
        "the", "and", "for", "with", "that", "this", "from", "your", "tool",
        "app", "based", "using", "open", "source", "project", "system",
        "new", "use", "can", "get", "all", "how", "what", "build",
        "code", "data", "test", "file", "user", "list", "type", "node",
        "free", "just", "like", "help", "need", "work", "make", "auto",
        "best", "easy", "fast", "good", "high", "self", "real", "time",
        "management", "service", "platform", "framework", "library",
        "server", "client", "plugin", "module", "package",
    }
    idea_words -= generic

    if not idea_words:
        return similars

    relevant = []
    fallback = []
    for s in similars:
        text = (s.get("name", "") + " " + s.get("description", "")).lower()
        matches = [w for w in idea_words if w in text]
        if len(matches) >= 2:
            # Strong match — 2+ keywords found
            relevant.append(s)
        elif len(matches) == 1 and len(matches[0]) >= 5:
            # Weak match — only count if the matching word is specific enough
            relevant.append(s)
        else:
            fallback.append(s)

    # Return relevant first, then fallback (so we always have something)
    return relevant + fallback


def filter_by_core_concept(items: list[dict], core_concept: str) -> list[dict]:
    """Filter items to only those mentioning at least one core concept word.

    Extracts core words from core_concept (split by spaces/hyphens, lowercased,
    stop words removed). Items kept if their name/description/detail field
    contains at least one core word (case-insensitive).

    Returns all items unfiltered if core_concept is empty or yields no valid words.
    """
    if not core_concept or not core_concept.strip():
        return items

    # Extract core words: split on spaces and hyphens, lowercase, remove stop words
    raw_words = re.split(r"[\s\-]+", core_concept.strip().lower())
    core_words = [w for w in raw_words if w and w not in STOP_WORDS]

    if not core_words:
        return items

    filtered = []
    for item in items:
        text = " ".join(
            str(item.get(field, ""))
            for field in ("name", "description", "detail")
        ).lower()
        if any(word in text for word in core_words):
            filtered.append(item)

    return filtered


def _duplicate_likelihood(signal: int) -> Literal["low", "medium", "high"]:
    if signal < 30:
        return "low"
    if signal <= 60:
        return "medium"
    return "high"


def _generate_pivot_hints(
    signal: int,
    github: GitHubResults,
    hn: HNResults,
    keywords: list[str],
    lang: str = "en",
) -> list[str]:
    """Generate 3 actionable pivot hints based on the analysis."""
    hints: list[str] = []

    if lang == "zh":
        if signal >= 60:
            hints.append("已偵測到高度競爭。考慮利基差異化，或鎖定未被滿足的受眾群體。")
            if github.top_repos:
                top = github.top_repos[0]
                hints.append(
                    f"領先專案 ({top['name']}, {top['stars']} 星) 可能存在缺口。"
                    "檢查其 issues 和功能請求，尋找未被滿足的需求。"
                )
            hints.append("考慮為現有工具打造整合或插件，而非獨立替代品。")
        elif signal >= 30:
            hints.append("存在中度競爭。專注於當前方案處理不佳的特定使用場景。")
            hints.append("在投入建構前先驗證需求 — 市場存在，但未必需要另一個通用方案。")
            hints.append("關注最新的進入者，尋找你可以領先的新興趨勢。")
        else:
            hints.append("低競爭 — 這可能是藍海機會，或是尚未被開發的利基市場。")
            hints.append("在大量投入前先驗證需求。低競爭也可能意味著低需求。")
            hints.append("搜尋相鄰的問題空間 — 這個點子可能以不同的術語存在。")
    else:
        if signal >= 60:
            hints.append(
                "High existing competition detected. Consider a niche differentiator "
                "or target an underserved audience segment."
            )
            if github.top_repos:
                top = github.top_repos[0]
                hints.append(
                    f"The leading project ({top['name']}, {top['stars']} stars) may have gaps. "
                    "Check its issues and feature requests for unmet needs."
                )
            hints.append(
                "Consider building an integration or plugin for existing tools "
                "rather than a standalone replacement."
            )
        elif signal >= 30:
            hints.append(
                "Moderate competition exists. Focus on a specific use case or workflow "
                "that current solutions handle poorly."
            )
            hints.append(
                "Validate with potential users before building — the market exists "
                "but may not need another general solution."
            )
            hints.append(
                "Look at the most recent entries for emerging trends you could lead."
            )
        else:
            hints.append(
                "Low competition — this could be a greenfield opportunity or a niche "
                "that hasn't gained traction yet."
            )
            hints.append(
                "Validate demand before investing heavily. Low competition can also "
                "mean low demand."
            )
            hints.append(
                "Search adjacent problem spaces — the idea might exist under different "
                "terminology."
            )

    return hints[:3]


# ---------------------------------------------------------------------------
# Signal computation
# ---------------------------------------------------------------------------

# Weight presets
_QUICK_WEIGHTS = {
    "github_repo": 0.6,
    "github_star": 0.2,
    "hn": 0.2,
}

_DEEP_WEIGHTS = {
    "github_repo": 0.22,
    "github_star": 0.09,
    "hn": 0.14,
    "npm": 0.18,
    "pypi": 0.13,
    "ph": 0.14,
    "so": 0.10,
}


def compute_signal(
    idea_text: str,
    keywords: list[str],
    github_results: GitHubResults,
    hn_results: HNResults,
    depth: str,
    *,
    npm_results: NpmResults | None = None,
    pypi_results: PyPIResults | None = None,
    ph_results: ProductHuntResults | None = None,
    so_results: StackOverflowResults | None = None,
    expansion: dict | None = None,
    lang: str = "en",
) -> dict:
    """Compute the full reality check output.

    Returns:
        Complete idea_check response dict.
    """
    g_repo = _github_repo_score(github_results.total_repo_count)
    g_star = _github_star_score(github_results.max_stars)
    h_score = _hn_score(hn_results.total_mentions)

    sources_used = ["github", "hackernews"]

    if depth == "quick" or (npm_results is None and pypi_results is None):
        # Quick mode — original weights
        signal = int(g_repo * 0.6 + g_star * 0.2 + h_score * 0.2)
        n_score = 0
        p_score = 0
        ph_val = 0
        so_val = 0
    else:
        # Deep mode
        n_score = _npm_score(npm_results.total_count) if npm_results else 0
        p_score = _pypi_score(pypi_results.total_count) if pypi_results else 0

        weights = dict(_DEEP_WEIGHTS)

        if npm_results:
            sources_used.append("npm")
        if pypi_results:
            sources_used.append("pypi")

        # Product Hunt — redistribute weight if skipped/unavailable
        ph_available = ph_results is not None and not ph_results.skipped
        if ph_available:
            ph_val = _ph_score(ph_results.total_count)
            sources_used.append("producthunt")
        else:
            ph_val = 0
            # Redistribute PH weight proportionally to other deep sources
            ph_w = weights.pop("ph", 0.14)
            remaining_keys = list(weights.keys())
            total_remaining = sum(weights[k] for k in remaining_keys)
            if total_remaining > 0:
                for k in remaining_keys:
                    weights[k] += ph_w * (weights[k] / total_remaining)

        # Stack Overflow — redistribute weight if unavailable
        so_available = so_results is not None
        if so_available:
            so_val = _so_score(so_results.total_count)
            sources_used.append("stackoverflow")
        else:
            so_val = 0
            # Redistribute SO weight proportionally to other deep sources
            so_w = weights.pop("so", 0.10)
            remaining_keys = list(weights.keys())
            total_remaining = sum(weights[k] for k in remaining_keys)
            if total_remaining > 0:
                for k in remaining_keys:
                    weights[k] += so_w * (weights[k] / total_remaining)

        signal = int(
            g_repo * weights.get("github_repo", 0.22)
            + g_star * weights.get("github_star", 0.09)
            + h_score * weights.get("hn", 0.14)
            + n_score * weights.get("npm", 0.18)
            + p_score * weights.get("pypi", 0.13)
            + ph_val * weights.get("ph", 0)
            + so_val * weights.get("so", 0)
        )

    # --- Temporal boost — market momentum from recent activity ratios ---
    temporal_ratios: list[float] = []
    if github_results.total_repo_count > 0:
        temporal_ratios.append(github_results.recent_ratio)
    if hn_results.recent_mention_ratio is not None:
        temporal_ratios.append(hn_results.recent_mention_ratio)
    if ph_results is not None and not ph_results.skipped and ph_results.total_count > 0:
        temporal_ratios.append(ph_results.recent_launch_ratio)
    if so_results is not None and so_results.recent_question_ratio is not None:
        temporal_ratios.append(so_results.recent_question_ratio)

    if temporal_ratios:
        market_momentum = sum(temporal_ratios) / len(temporal_ratios)
    else:
        market_momentum = 0.5  # neutral when no temporal data

    temporal_boost = (market_momentum - 0.5) * 20  # range: -10 to +10
    signal = int(signal + temporal_boost)
    signal = max(0, min(100, signal))

    # Trend classification
    if market_momentum > 0.6:
        trend = "accelerating"
    elif market_momentum < 0.3:
        trend = "declining"
    else:
        trend = "stable"

    # Build evidence
    evidence = [
        {
            "source": "github",
            "type": "repo_count",
            "query": kw,
            "count": github_results.total_repo_count,
            "detail": f"{github_results.total_repo_count} repos found across queries",
        }
        for kw in keywords[:1]
    ]
    evidence.append({
        "source": "github",
        "type": "max_stars",
        "query": keywords[0],
        "count": github_results.max_stars,
        "detail": f"Top repo has {github_results.max_stars} stars",
    })
    evidence.extend(hn_results.evidence)

    if npm_results:
        evidence.extend(npm_results.evidence)
    if pypi_results:
        evidence.extend(pypi_results.evidence)
    if ph_results:
        evidence.extend(ph_results.evidence)
    if so_results:
        evidence.extend(so_results.evidence)

    # Temporal evidence
    if github_results.total_repo_count > 0:
        evidence.append({
            "source": "github",
            "type": "recent_ratio",
            "query": keywords[0],
            "count": github_results.recent_created_count,
            "detail": f"{github_results.recent_ratio:.0%} of repos created in last 6 months",
        })
    if hn_results.recent_mention_ratio is not None:
        evidence.append({
            "source": "hackernews",
            "type": "recent_mention_ratio",
            "query": keywords[0],
            "count": round(hn_results.recent_mention_ratio * 100),
            "detail": f"{hn_results.recent_mention_ratio:.0%} of mentions in last 3 months",
        })
    if ph_results is not None and not ph_results.skipped and ph_results.total_count > 0:
        evidence.append({
            "source": "producthunt",
            "type": "recent_launch_ratio",
            "query": keywords[0],
            "count": round(ph_results.recent_launch_ratio * 100),
            "detail": f"{ph_results.recent_launch_ratio:.0%} of launches in last 6 months",
        })
    if so_results is not None and so_results.recent_question_ratio is not None:
        evidence.append({
            "source": "stackoverflow",
            "type": "recent_question_ratio",
            "query": keywords[0],
            "count": round(so_results.recent_question_ratio * 100),
            "detail": f"{so_results.recent_question_ratio:.0%} of questions in last 3 months",
        })

    # Cap evidence to prevent response bloat (keep first + last for coverage)
    _MAX_EVIDENCE = 20
    if len(evidence) > _MAX_EVIDENCE:
        evidence = evidence[:_MAX_EVIDENCE]

    # Add queried_at timestamp to all evidence items for credibility
    _now = datetime.now(timezone.utc).isoformat()
    for ev in evidence:
        ev["queried_at"] = _now

    # Top similars: merge GitHub repos with npm/PyPI/PH entries
    top_similars = list(github_results.top_repos)
    if npm_results:
        for pkg in npm_results.top_packages[:3]:
            top_similars.append({
                "name": f"npm:{pkg['name']}",
                "url": pkg["url"],
                "stars": 0,
                "updated": "",
                "description": pkg["description"],
            })
    if pypi_results:
        for pkg in pypi_results.top_packages[:3]:
            top_similars.append({
                "name": f"pypi:{pkg['name']}",
                "url": pkg["url"],
                "stars": 0,
                "updated": "",
                "description": pkg["description"],
            })
    if ph_results and not ph_results.skipped:
        for prod in ph_results.top_products[:3]:
            top_similars.append({
                "name": f"ph:{prod['name']}",
                "url": prod["url"],
                "stars": prod.get("votes", 0),
                "updated": prod.get("created_at", ""),
                "description": prod.get("tagline", ""),
            })
    if so_results:
        for question in so_results.top_questions[:3]:
            top_similars.append({
                "name": f"so:{question['title'][:80]}",
                "url": question["link"],
                "stars": question.get("score", 0),
                "updated": "",
                "description": f"Stack Overflow — {question['answer_count']} answers, {'answered' if question['is_answered'] else 'unanswered'}",
            })

    # Filter similars for relevance — prevent broad keyword matches
    top_similars = _filter_relevant_similars(top_similars, idea_text, keywords)

    # Filter evidence by core concept if expansion provides one
    if expansion is not None and expansion.get("core_concept"):
        evidence = filter_by_core_concept(evidence, expansion["core_concept"])

    return {
        "reality_signal": signal,
        "duplicate_likelihood": _duplicate_likelihood(signal),
        "sub_scores": {
            "competition_density": g_repo,
            "market_maturity": g_star,
            "community_buzz": h_score,
            "ecosystem_depth_npm": n_score if depth != "quick" else None,
            "ecosystem_depth_pypi": p_score if depth != "quick" else None,
            "product_launches": ph_val if depth != "quick" else None,
            "developer_interest": so_val if depth != "quick" else None,
            "market_momentum": round(market_momentum * 100),
        },
        "trend": trend,
        "evidence": evidence,
        "top_similars": top_similars,
        "pivot_hints": _generate_pivot_hints(signal, github_results, hn_results, keywords, lang=lang),
        "meta": {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "sources_used": sources_used,
            "depth": depth,
            "version": "0.5.0",
        },
    }
