"""Curated synonym and intent-anchor dictionary for keyword extraction.

Hand-written; no LLM required. Covers MCP, agents, LLMOps, eval,
monitoring, RAG, developer tooling, SaaS, and general software domains.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Intent anchors — signals "what type of thing is this?"
# Detected in Stage B of extract_keywords().
# Includes common morphological variants (parser/parsing, scheduler/scheduling).
# ---------------------------------------------------------------------------
INTENT_ANCHORS: frozenset[str] = frozenset({
    # LLM / AI ops
    "evaluation", "evals", "eval",
    "monitoring", "observability",
    "tracing", "telemetry", "metrics",
    "llmops", "inference", "serving",
    "guardrails", "safety", "moderation",
    "finetuning", "finetune", "fine tuning",
    "prompt",
    # Agent / workflow
    "agent", "agents", "agentic",
    "workflow", "orchestration", "pipeline", "automation",
    # MCP ecosystem
    "mcp", "model context protocol",
    # Retrieval / embedding
    "rag", "retrieval", "embedding", "embeddings", "reranking",
    "vector", "vectorstore",
    # Developer tooling
    "cli", "tui", "shell",
    "sdk", "debugger", "debugging", "profiling", "linting", "linter",
    "refactoring",
    "compiler", "transpiler",
    # Scheduling / jobs
    "scheduling", "scheduler", "cron",
    # Data
    "scraping", "scraper", "crawler", "crawling",
    "parsing", "parser",
    "analytics", "dashboard", "visualization",
    "benchmark", "benchmarking", "testing", "tester",
    "migration", "migrator",
    "caching", "cache",
    "queue", "messaging",
    "logging", "logger",
    "streaming",
    # Generation / synthesis
    "generation", "generator",
    "transcription", "transcriber",
    "translation", "translator",
    "summarization", "summarizer",
    "ocr",
    # Communication / product
    "chatbot", "bot", "assistant",
    "notification", "notifications", "alerting",
    # Code-focused
    "review", "reviewer",
    "formatter", "formatting",
    # Infrastructure
    "deployment", "devops", "containerization",
    "database", "search",
    "authentication", "auth",
    "proxy", "gateway",
    # SaaS / business
    "billing", "payment", "payments", "checkout",
    "subscription", "subscriptions",
    "marketplace",
    "feedback", "survey",
    "onboarding",
    "invoicing", "invoice",
    "booking", "reservation",
    "inventory",
    "crm",
    # Content / media
    "editor",
    "cms",
    "blogging",
})

# ---------------------------------------------------------------------------
# Synonym table — used in Stage C to expand anchor queries.
# Keys are anchor words (lowercase). Values are expansion terms
# ordered by relevance (most useful first).
# ---------------------------------------------------------------------------
SYNONYMS: dict[str, list[str]] = {
    # LLM / AI ops
    "monitoring":   ["observability", "tracing", "telemetry", "metrics", "alerting"],
    "observability": ["monitoring", "tracing", "telemetry", "metrics", "otel"],
    "tracing":      ["observability", "monitoring", "telemetry", "opentelemetry"],
    "telemetry":    ["tracing", "observability", "monitoring", "metrics"],
    "evaluation":   ["evals", "benchmark", "regression testing", "grading", "scoring"],
    "evals":        ["evaluation", "benchmark", "testing", "regression", "scoring"],
    "llmops":       ["mlops", "model deployment", "inference serving", "llm pipeline"],
    "inference":    ["serving", "deployment", "model serving", "runtime"],
    "guardrails":   ["safety", "moderation", "content filter", "output validation"],
    "safety":       ["guardrails", "moderation", "content filter", "alignment"],
    "moderation":   ["content filter", "safety", "guardrails", "toxicity"],
    "finetuning":   ["fine-tuning", "training", "model training", "adapter"],
    "finetune":     ["fine-tuning", "training", "lora", "qlora"],
    "fine tuning":  ["finetuning", "training", "model training", "lora", "adapter"],
    "prompt":       ["prompt engineering", "prompt management", "prompt template", "prompt chain"],
    # Agent / workflow
    "agent":        ["tool calling", "orchestration", "workflow", "agentic", "autonomous agent"],
    "agents":       ["multi-agent", "tool calling", "orchestration", "autonomous"],
    "workflow":     ["pipeline", "automation", "orchestration", "dag", "process"],
    "orchestration": ["workflow", "agent", "pipeline", "coordination"],
    "automation":   ["workflow", "pipeline", "no-code", "scripting", "bot"],
    "pipeline":     ["workflow", "automation", "dag", "etl", "orchestration"],
    # MCP
    "mcp":          ["model context protocol", "mcp server", "mcp tool", "mcp client"],
    # Retrieval / embedding
    "rag":          ["retrieval", "embedding", "rerank", "vector search", "semantic search"],
    "retrieval":    ["rag", "embedding", "vector search", "semantic search", "search"],
    "embedding":    ["vector", "semantic", "rag", "similarity", "vectorstore"],
    "embeddings":   ["vector embedding", "semantic", "rag", "retrieval"],
    "vector":       ["embedding", "similarity", "rag", "vectorstore", "retrieval"],
    # Developer tooling
    "cli":          ["command line", "terminal", "shell", "tui", "command-line interface"],
    "tui":          ["terminal ui", "cli", "command line", "curses"],
    "sdk":          ["library", "client", "wrapper", "integration", "package"],
    "debugging":    ["debugger", "profiling", "tracing", "inspection", "logging"],
    "debugger":     ["debugging", "inspector", "devtools", "breakpoint"],
    "profiling":    ["performance", "benchmarking", "debugging", "tracing"],
    "linting":      ["static analysis", "code quality", "style checker", "formatter"],
    "linter":       ["linting", "static analysis", "code quality", "eslint"],
    "refactoring":  ["code transformation", "codemod", "ast", "migration"],
    "compiler":     ["transpiler", "parser", "codegen", "build tool"],
    "transpiler":   ["compiler", "source-to-source", "babel", "transform"],
    # Scheduling / jobs
    "scheduling":   ["cron", "job queue", "task scheduler", "periodic", "timer"],
    "scheduler":    ["cron", "task queue", "job scheduler", "periodic", "scheduling"],
    "cron":         ["scheduler", "periodic", "job queue", "task scheduler"],
    # Data / web
    "scraping":     ["crawler", "spider", "extraction", "parsing", "web scraping"],
    "scraper":      ["crawler", "scraping", "spider", "extraction"],
    "crawler":      ["scraping", "spider", "web crawl", "extraction"],
    "crawling":     ["scraping", "crawler", "spider", "indexing"],
    "parsing":      ["parser", "extraction", "transform", "tokenizer"],
    "parser":       ["parsing", "lexer", "tokenizer", "ast"],
    "analytics":    ["dashboard", "metrics", "visualization", "reporting", "insights"],
    "dashboard":    ["analytics", "visualization", "monitoring", "reporting", "ui"],
    "visualization": ["dashboard", "chart", "graph", "plot", "data viz"],
    "benchmark":    ["evaluation", "evals", "performance test", "comparison", "leaderboard"],
    "benchmarking": ["benchmark", "evaluation", "performance test", "comparison"],
    "testing":      ["test", "evaluation", "evals", "quality assurance", "validation"],
    "tester":       ["testing", "test runner", "qa", "validation"],
    "migration":    ["migrator", "database migration", "schema migration", "upgrade"],
    "migrator":     ["migration", "database migration", "schema change"],
    "caching":      ["cache", "redis", "memcached", "cdn", "memoization"],
    "cache":        ["caching", "redis", "cdn", "memoization", "store"],
    "queue":        ["message queue", "job queue", "task queue", "pubsub", "broker"],
    "messaging":    ["message queue", "pubsub", "event bus", "notification", "realtime"],
    "logging":      ["logger", "log aggregation", "log management", "structured logging"],
    "logger":       ["logging", "log aggregation", "structured logging"],
    "streaming":    ["real-time", "event stream", "websocket", "sse", "pubsub"],
    # Generation / synthesis
    "generation":   ["generator", "synthesis", "text-to-image", "generative", "diffusion"],
    "generator":    ["generation", "builder", "synthesis", "creator"],
    "transcription": ["speech-to-text", "subtitle", "caption", "whisper", "asr"],
    "transcriber":  ["transcription", "speech-to-text", "subtitle", "caption"],
    "translation":  ["i18n", "localization", "multilingual", "translate"],
    "translator":   ["translation", "i18n", "localization", "multilingual"],
    "summarization": ["summarizer", "tldr", "digest", "abstract", "condensation"],
    "summarizer":   ["summarization", "tldr", "digest", "abstract"],
    "ocr":          ["document extraction", "text recognition", "pdf parsing", "receipt scanner"],
    # Communication / product
    "chatbot":      ["bot", "assistant", "conversation", "dialogue", "chat"],
    "bot":          ["chatbot", "assistant", "automation", "agent", "integration"],
    "assistant":    ["chatbot", "agent", "copilot", "helper"],
    "notification": ["alerting", "push notification", "reminder", "webhook", "email"],
    "notifications": ["alerting", "push notification", "reminder", "webhook"],
    "alerting":     ["notification", "monitoring", "pagerduty", "incident"],
    # Code
    "review":       ["code review", "pr review", "static analysis", "linting"],
    "reviewer":     ["code review", "pr review", "static analysis"],
    "formatter":    ["formatting", "prettier", "code style", "linting"],
    "formatting":   ["formatter", "prettier", "code style", "beautifier"],
    "editor":       ["ide", "code editor", "text editor", "visual studio code"],
    # Infrastructure
    "deployment":   ["devops", "cicd", "hosting", "infrastructure", "cloud"],
    "devops":       ["ci/cd", "deployment", "infrastructure", "automation", "sre"],
    "containerization": ["docker", "kubernetes", "container", "podman"],
    "database":     ["storage", "persistence", "orm", "query", "data layer"],
    "search":       ["retrieval", "indexing", "full text search", "semantic search"],
    "authentication": ["auth", "oauth", "sso", "identity", "jwt"],
    "auth":         ["authentication", "oauth", "authorization", "sso"],
    "proxy":        ["reverse proxy", "load balancer", "gateway", "nginx"],
    "gateway":      ["api gateway", "proxy", "routing", "load balancer"],
    # SaaS / business
    "billing":      ["payment", "subscription", "invoicing", "stripe", "checkout"],
    "payment":      ["billing", "checkout", "stripe", "payment gateway", "fintech"],
    "payments":     ["billing", "checkout", "stripe", "payment gateway"],
    "checkout":     ["payment", "cart", "purchase", "billing"],
    "subscription": ["recurring billing", "saas billing", "stripe", "plan management"],
    "subscriptions": ["recurring billing", "saas billing", "plan management"],
    "marketplace":  ["platform", "two-sided market", "listing", "storefront"],
    "feedback":     ["survey", "nps", "user feedback", "review", "rating"],
    "survey":       ["feedback", "questionnaire", "nps", "form", "poll"],
    "onboarding":   ["user onboarding", "tutorial", "walkthrough", "setup wizard"],
    "invoicing":    ["invoice", "billing", "receipt", "accounting"],
    "invoice":      ["invoicing", "billing", "receipt", "pdf invoice"],
    "booking":      ["reservation", "appointment", "scheduling", "calendar"],
    "reservation":  ["booking", "appointment", "scheduling", "calendar"],
    "inventory":    ["stock management", "warehouse", "product catalog", "sku"],
    "crm":          ["customer relationship", "contact management", "sales pipeline", "hubspot"],
    # Content / media
    "cms":          ["content management", "headless cms", "blog", "publishing"],
    "blogging":     ["blog", "cms", "publishing", "writing platform"],
}
