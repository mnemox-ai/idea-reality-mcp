"""Curated synonym and intent-anchor dictionary for keyword extraction.

Hand-written; no LLM required. Covers MCP, agents, LLMOps, eval,
monitoring, RAG, and adjacent AI-tooling domains.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Intent anchors — signals "what type of thing is this?"
# Detected in Stage B of extract_keywords().
# Single words only (compound anchors are handled via COMPOUND_TERMS match).
# ---------------------------------------------------------------------------
INTENT_ANCHORS: frozenset[str] = frozenset({
    # LLM / AI ops
    "evaluation", "evals", "eval",
    "monitoring", "observability",
    "tracing", "telemetry", "metrics",
    "llmops", "inference", "serving",
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
    "sdk", "debugger", "debugging", "profiling", "linting",
    "refactoring",
    # Data
    "scraping", "crawler", "parsing",
    "analytics", "dashboard", "visualization",
    "benchmark", "benchmarking", "testing",
    # Communication / product
    "chatbot", "bot", "assistant",
    # Code-focused
    "review",
    # Infrastructure
    "deployment", "devops", "containerization",
    "database", "search",
    "authentication", "auth",
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
    "profiling":    ["performance", "benchmarking", "debugging", "tracing"],
    "linting":      ["static analysis", "code quality", "style checker", "formatter"],
    "refactoring":  ["code transformation", "codemod", "ast", "migration"],
    # Data / web
    "scraping":     ["crawler", "spider", "extraction", "parsing", "web scraping"],
    "crawler":      ["scraping", "spider", "web crawl", "extraction"],
    "parsing":      ["extraction", "scraping", "transform", "nlp"],
    "analytics":    ["dashboard", "metrics", "visualization", "reporting", "insights"],
    "dashboard":    ["analytics", "visualization", "monitoring", "reporting", "ui"],
    "benchmark":    ["evaluation", "evals", "performance test", "comparison", "leaderboard"],
    "testing":      ["test", "evaluation", "evals", "quality assurance", "validation"],
    # Communication / product
    "chatbot":      ["bot", "assistant", "conversation", "dialogue", "chat"],
    "bot":          ["chatbot", "assistant", "automation", "agent", "integration"],
    "assistant":    ["chatbot", "agent", "copilot", "helper"],
    # Code
    "review":       ["code review", "pr review", "static analysis", "linting"],
    # Infrastructure
    "deployment":   ["devops", "cicd", "hosting", "infrastructure", "cloud"],
    "devops":       ["ci/cd", "deployment", "infrastructure", "automation", "platform"],
    "database":     ["storage", "persistence", "orm", "query", "data layer"],
    "search":       ["retrieval", "indexing", "full text search", "semantic search"],
    "authentication": ["auth", "oauth", "sso", "identity", "jwt"],
    "auth":         ["authentication", "oauth", "authorization", "sso"],
}
