#!/usr/bin/env python3
"""
Comprehensive analysis of idea-reality Discord query data.
847 queries from product idea validation tool.
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA_PATH = Path(r"C:\Users\johns\projects\idea-reality-mcp\discord_all_queries.json")
OUTPUT_PATH = Path(r"C:\Users\johns\projects\idea-reality-mcp\query_analysis_report.md")

# --- Category classification keywords ---
CATEGORIES = {
    "AI/ML": [
        "ai ", "artificial intelligence", "machine learning", "ml ", "deep learning",
        "neural", "llm", "gpt", "chatbot", "nlp", "natural language", "transformer",
        "embedding", "rag ", "vector", "fine-tun", "model training", "computer vision",
        "image recognition", "speech recognition", "text generation", "ai agent",
        "copilot", "assistant", "autonomous agent", "generative", "diffusion",
        "prompt", "inference", "multimodal", "langchain", "openai", "anthropic",
        "claude", "gemini", "hugging face", "onnx", "tensorflow", "pytorch",
    ],
    "Developer Tools": [
        "developer", "dev tool", "code", "coding", "ide ", "editor", "api ",
        "sdk ", "cli ", "terminal", "debug", "testing", "ci/cd", "pipeline",
        "git ", "github", "gitlab", "docker", "kubernetes", "devops",
        "infrastructure", "monitoring", "logging", "deployment", "microservice",
        "linter", "formatter", "compiler", "boilerplate", "scaffold",
        "documentation", "docs ", "snippet", "package manager", "npm", "pypi",
        "mcp server", "mcp ", "plugin", "extension", "vscode", "cursor",
        "open source", "library", "framework",
    ],
    "Trading/Finance": [
        "trading", "trade ", "trader", "forex", "stock", "crypto", "bitcoin",
        "defi", "blockchain", "web3", "token", "nft", "wallet", "exchange",
        "portfolio", "investment", "financial", "fintech", "payment", "banking",
        "accounting", "invoice", "budget", "expense", "revenue", "profit",
        "market data", "candlestick", "backtest", "algorithmic trad", "quant",
        "hedge fund", "options", "futures", "yield", "staking", "dao ",
    ],
    "Consumer App": [
        "mobile app", "ios app", "android app", "social media", "dating",
        "fitness", "workout", "recipe", "food", "restaurant", "travel",
        "booking", "ride", "delivery", "shopping", "ecommerce", "e-commerce",
        "marketplace", "rental", "subscription", "streaming", "music",
        "video", "photo", "camera", "filter", "sticker", "emoji",
        "messenger", "chat app", "community", "forum", "social network",
        "content creator", "influencer", "youtube", "tiktok", "instagram",
    ],
    "SaaS/Business": [
        "saas", "b2b", "crm", "erp", "dashboard", "analytics", "reporting",
        "project management", "task management", "workflow", "automation",
        "no-code", "low-code", "drag and drop", "template", "form builder",
        "email marketing", "seo ", "marketing", "lead generation", "sales",
        "customer support", "helpdesk", "ticketing", "scheduling", "calendar",
        "meeting", "collaboration", "team", "workspace", "productivity",
        "human resources", "hr ", "recruitment", "hiring", "onboarding",
        "survey", "feedback", "review",
    ],
    "Education": [
        "education", "learning", "course", "tutorial", "quiz", "exam",
        "student", "teacher", "classroom", "school", "university", "academic",
        "research paper", "flashcard", "study", "tutor", "lesson",
        "curriculum", "e-learning", "edtech", "language learning",
        "certification", "training platform",
    ],
    "Gaming": [
        "game", "gaming", "player", "multiplayer", "rpg", "puzzle",
        "arcade", "esport", "steam", "unity", "unreal", "godot",
        "game engine", "leaderboard", "achievement", "quest",
        "virtual world", "metaverse", "game dev",
    ],
    "Health/Medical": [
        "health", "medical", "patient", "doctor", "hospital", "clinic",
        "diagnosis", "symptom", "therapy", "mental health", "meditation",
        "wellness", "nutrition", "diet", "sleep", "wearable", "biotech",
        "pharma", "drug", "telemedicine", "healthcare",
    ],
    "Security/Privacy": [
        "security", "cybersecurity", "privacy", "encryption", "auth",
        "vulnerability", "pentest", "threat", "malware", "firewall",
        "access control", "compliance", "gdpr", "soc ", "incident response",
        "password", "identity", "zero trust",
    ],
    "Data/Infrastructure": [
        "database", "data pipeline", "etl", "data warehouse", "data lake",
        "scraping", "crawler", "web scraper", "data extraction", "parsing",
        "search engine", "indexing", "caching", "queue", "message broker",
        "serverless", "cloud", "aws ", "azure", "gcp ",
    ],
    "IoT/Hardware": [
        "iot ", "sensor", "raspberry pi", "arduino", "embedded", "firmware",
        "smart home", "home automation", "robot", "drone", "3d print",
        "hardware", "device", "wearable device",
    ],
    "Content/Media": [
        "content", "blog", "newsletter", "writing", "copywriting",
        "podcast", "audio", "transcription", "subtitle", "translation",
        "localization", "cms", "headless cms", "publishing", "media",
        "news", "article", "summariz", "text-to-speech", "voice",
    ],
}


def parse_score(title: str) -> int | None:
    """Extract signal score from title like '🟡 Signal 71/100'."""
    m = re.search(r"Signal\s+(\d+)/100", title)
    return int(m.group(1)) if m else None


def parse_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp."""
    return datetime.fromisoformat(ts_str)


def classify_query(description: str, keywords_field: str = "") -> list[str]:
    """Classify a query into categories based on description + keywords."""
    text = (description + " " + keywords_field).lower()
    matched = []
    for cat, kws in CATEGORIES.items():
        for kw in kws:
            if kw in text:
                matched.append(cat)
                break
    return matched if matched else ["Other/Uncategorized"]


def extract_competitor(top_comp: str) -> tuple[str, str, int]:
    """
    Parse competitor field like 'feder-cr/Jobs_Applier_AI_Agent_AIHawk (29411★)'
    or 'npm:wa-sticker-formatter'.
    Returns (source, name, stars).
    """
    if not top_comp or top_comp.strip() == "":
        return ("none", "", 0)

    # npm package
    if top_comp.startswith("npm:"):
        return ("npm", top_comp[4:].strip(), 0)

    # pypi package
    if top_comp.startswith("pypi:"):
        return ("pypi", top_comp[5:].strip(), 0)

    # GitHub repo with stars
    m = re.match(r"(.+?)\s*\((\d+)★\)", top_comp.strip())
    if m:
        return ("github", m.group(1).strip(), int(m.group(2)))

    return ("other", top_comp.strip(), 0)


def find_similar_descriptions(queries: list[dict], threshold: float = 0.7) -> list[list[int]]:
    """Find queries with very similar descriptions (potential repeats)."""
    from difflib import SequenceMatcher
    groups = []
    used = set()
    descs = [q["description"].lower().strip()[:200] for q in queries]

    for i in range(len(descs)):
        if i in used:
            continue
        group = [i]
        for j in range(i + 1, len(descs)):
            if j in used:
                continue
            ratio = SequenceMatcher(None, descs[i], descs[j]).ratio()
            if ratio >= threshold:
                group.append(j)
                used.add(j)
        if len(group) > 1:
            groups.append(group)
            used.add(i)
    return groups


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        queries = json.load(f)

    total = len(queries)
    report_lines = []

    def out(line=""):
        try:
            print(line)
        except UnicodeEncodeError:
            # Windows console can't handle some chars; sanitize for print only
            print(line.encode("ascii", errors="replace").decode("ascii"))
        report_lines.append(line)

    out("# Idea Reality MCP — Query Analysis Report")
    out(f"\n**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    out(f"**Total Queries**: {total}")
    out("")

    # ===== 1. DATE DISTRIBUTION =====
    out("---")
    out("## 1. Date Distribution")
    out("")

    timestamps = [parse_timestamp(q["timestamp"]) for q in queries]
    date_counts = Counter(ts.strftime("%Y-%m-%d") for ts in timestamps)
    sorted_dates = sorted(date_counts.items())

    first_date = sorted_dates[0][0]
    last_date = sorted_dates[-1][0]
    total_days = len(sorted_dates)
    avg_per_day = total / total_days

    out(f"- **Date range**: {first_date} to {last_date} ({total_days} active days)")
    out(f"- **Average queries/day**: {avg_per_day:.1f}")
    out("")

    # Top 10 busiest days
    top_days = sorted(date_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    out("### Top 10 Busiest Days")
    out("")
    out("| Date | Queries |")
    out("|------|---------|")
    for d, c in top_days:
        out(f"| {d} | {c} |")
    out("")

    # Weekly trend
    week_counts = Counter()
    for ts in timestamps:
        week_key = ts.strftime("%Y-W%U")
        week_counts[week_key] += 1
    sorted_weeks = sorted(week_counts.items())
    out("### Weekly Trend")
    out("")
    out("| Week | Queries |")
    out("|------|---------|")
    for w, c in sorted_weeks:
        out(f"| {w} | {c} |")
    out("")

    # Daily distribution over time
    out("### Daily Query Counts (all days)")
    out("")
    out("| Date | Queries |")
    out("|------|---------|")
    for d, c in sorted_dates:
        bar = "#" * min(c, 100)
        out(f"| {d} | {c} |")
    out("")

    # ===== 2. SCORE DISTRIBUTION =====
    out("---")
    out("## 2. Score Distribution")
    out("")

    scores = []
    for q in queries:
        s = parse_score(q["title"])
        if s is not None:
            scores.append(s)

    out(f"- **Parsed scores**: {len(scores)}/{total} ({len(scores)/total*100:.1f}%)")
    out(f"- **Mean score**: {sum(scores)/len(scores):.1f}")
    out(f"- **Median score**: {sorted(scores)[len(scores)//2]}")
    out(f"- **Min**: {min(scores)}, **Max**: {max(scores)}")
    out("")

    # Score ranges
    ranges = [(0, 20), (21, 40), (41, 60), (61, 80), (81, 100)]
    range_labels = {
        (0, 20): "0-20 (Blue Ocean)",
        (21, 40): "21-40 (Low Competition)",
        (41, 60): "41-60 (Moderate)",
        (61, 80): "61-80 (Crowded)",
        (81, 100): "81-100 (Red Ocean)",
    }
    out("### Score Histogram")
    out("")
    out("| Range | Count | % | Visual |")
    out("|-------|-------|---|--------|")
    for lo, hi in ranges:
        cnt = sum(1 for s in scores if lo <= s <= hi)
        pct = cnt / len(scores) * 100
        bar = "#" * int(pct / 2)
        out(f"| {range_labels[(lo, hi)]} | {cnt} | {pct:.1f}% | {bar} |")
    out("")

    # Signal color distribution
    color_counts = Counter()
    for q in queries:
        if "🟢" in q["title"]:
            color_counts["Green (0-49)"] += 1
        elif "🟡" in q["title"]:
            color_counts["Yellow (50-79)"] += 1
        elif "🔴" in q["title"]:
            color_counts["Red (80-100)"] += 1
        else:
            color_counts["Unknown"] += 1
    out("### Signal Color Distribution")
    out("")
    out("| Color | Count | % |")
    out("|-------|-------|---|")
    for color in ["Green (0-49)", "Yellow (50-79)", "Red (80-100)", "Unknown"]:
        cnt = color_counts.get(color, 0)
        out(f"| {color} | {cnt} | {cnt/total*100:.1f}% |")
    out("")

    # ===== 3. DEPTH DISTRIBUTION =====
    out("---")
    out("## 3. Depth Distribution (quick vs deep)")
    out("")

    depth_counts = Counter(q["fields"].get("Depth", "unknown") for q in queries)
    for d, c in depth_counts.most_common():
        out(f"- **{d}**: {c} ({c/total*100:.1f}%)")
    out("")
    quick_c = depth_counts.get("quick", 0)
    deep_c = depth_counts.get("deep", 0)
    if quick_c + deep_c > 0:
        out(f"- **Deep adoption rate**: {deep_c/(quick_c+deep_c)*100:.1f}% of queries use deep scan")
    out("")

    # ===== 4. LANGUAGE DISTRIBUTION =====
    out("---")
    out("## 4. Language Distribution")
    out("")

    lang_counts = Counter(q["fields"].get("Lang", "unknown") for q in queries)
    out("| Language | Count | % |")
    out("|----------|-------|---|")
    for lang, cnt in lang_counts.most_common():
        out(f"| {lang} | {cnt} | {cnt/total*100:.1f}% |")
    out("")

    # ===== 5. CATEGORY CLASSIFICATION =====
    out("---")
    out("## 5. Category Classification")
    out("")

    cat_counts = Counter()
    query_cats = []
    for q in queries:
        cats = classify_query(q["description"], q["fields"].get("Keywords", ""))
        query_cats.append(cats)
        for c in cats:
            cat_counts[c] += 1

    out("| Category | Queries | % of Total |")
    out("|----------|---------|------------|")
    for cat, cnt in cat_counts.most_common():
        out(f"| {cat} | {cnt} | {cnt/total*100:.1f}% |")
    out("")
    out(f"*Note: Queries can belong to multiple categories. {sum(cat_counts.values())} total category assignments for {total} queries.*")
    out("")

    # Multi-category queries
    multi_cat = sum(1 for cats in query_cats if len(cats) > 1)
    out(f"- **Multi-category queries**: {multi_cat} ({multi_cat/total*100:.1f}%)")
    out("")

    # ===== 6. TOP COMPETITORS =====
    out("---")
    out("## 6. Top Competitors Mentioned")
    out("")

    competitor_data = []
    for q in queries:
        tc = q["fields"].get("Top Competitor", "")
        if tc:
            source, name, stars = extract_competitor(tc)
            competitor_data.append((source, name, stars))

    # Source breakdown
    source_counts = Counter(s for s, n, st in competitor_data)
    out("### Competitor Source Breakdown")
    out("")
    out("| Source | Count | % |")
    out("|--------|-------|---|")
    for src, cnt in source_counts.most_common():
        out(f"| {src} | {cnt} | {cnt/total*100:.1f}% |")
    out("")

    # Top GitHub repos by frequency
    github_repos = Counter()
    github_stars = {}
    for s, n, st in competitor_data:
        if s == "github" and n:
            github_repos[n] += 1
            github_stars[n] = max(github_stars.get(n, 0), st)

    out("### Top 20 Most Cited GitHub Repos")
    out("")
    out("| Repo | Times Cited | Stars |")
    out("|------|-------------|-------|")
    for repo, cnt in github_repos.most_common(20):
        out(f"| {repo} | {cnt} | {github_stars[repo]:,} |")
    out("")

    # Top repos by stars
    out("### Top 20 Highest-Star Competitors")
    out("")
    out("| Repo | Stars | Times Cited |")
    out("|------|-------|-------------|")
    top_by_stars = sorted(github_stars.items(), key=lambda x: x[1], reverse=True)[:20]
    for repo, stars in top_by_stars:
        out(f"| {repo} | {stars:,} | {github_repos[repo]} |")
    out("")

    # Top npm packages
    npm_pkgs = Counter(n for s, n, st in competitor_data if s == "npm" and n)
    if npm_pkgs:
        out("### Top npm Packages Cited")
        out("")
        out("| Package | Times Cited |")
        out("|---------|-------------|")
        for pkg, cnt in npm_pkgs.most_common(15):
            out(f"| {pkg} | {cnt} |")
        out("")

    # Top pypi packages
    pypi_pkgs = Counter(n for s, n, st in competitor_data if s == "pypi" and n)
    if pypi_pkgs:
        out("### Top PyPI Packages Cited")
        out("")
        out("| Package | Times Cited |")
        out("|---------|-------------|")
        for pkg, cnt in pypi_pkgs.most_common(15):
            out(f"| {pkg} | {cnt} |")
        out("")

    # ===== 7. SCORE BY CATEGORY =====
    out("---")
    out("## 7. Score by Category")
    out("")

    cat_scores = defaultdict(list)
    for i, q in enumerate(queries):
        s = parse_score(q["title"])
        if s is not None:
            for c in query_cats[i]:
                cat_scores[c].append(s)

    out("| Category | Avg Score | Median | Min | Max | n |")
    out("|----------|-----------|--------|-----|-----|---|")
    cat_avgs = []
    for cat in cat_counts.keys():
        ss = cat_scores.get(cat, [])
        if ss:
            avg = sum(ss) / len(ss)
            med = sorted(ss)[len(ss) // 2]
            cat_avgs.append((cat, avg, med, min(ss), max(ss), len(ss)))

    # Sort by avg score descending
    cat_avgs.sort(key=lambda x: x[1], reverse=True)
    for cat, avg, med, mn, mx, n in cat_avgs:
        out(f"| {cat} | {avg:.1f} | {med} | {mn} | {mx} | {n} |")
    out("")
    out("*Higher score = more competition (red ocean). Lower score = less competition (blue ocean).*")
    out("")

    # ===== 8. USER BEHAVIOR / REPEAT QUERIES =====
    out("---")
    out("## 8. User Behavior & Repeat Queries")
    out("")

    # Find similar descriptions
    out("### Similar/Duplicate Queries (>70% text similarity)")
    out("")
    similar_groups = find_similar_descriptions(queries, threshold=0.7)

    out(f"- **Total similar groups found**: {len(similar_groups)}")
    total_dupes = sum(len(g) for g in similar_groups)
    out(f"- **Total queries in duplicate groups**: {total_dupes}")
    out("")

    if similar_groups:
        # Show top groups
        similar_groups.sort(key=lambda g: len(g), reverse=True)
        out("### Top 15 Duplicate Groups")
        out("")
        for gi, group in enumerate(similar_groups[:15], 1):
            out(f"**Group {gi}** ({len(group)} queries):")
            for idx in group[:5]:  # show max 5 per group
                q = queries[idx]
                ts = parse_timestamp(q["timestamp"]).strftime("%m/%d %H:%M")
                desc_short = q["description"][:100].replace("\n", " ")
                score = parse_score(q["title"]) or "?"
                out(f"  - [{ts}] Score={score}: {desc_short}...")
            if len(group) > 5:
                out(f"  - ... and {len(group) - 5} more")
            out("")

    # Burst detection: queries within short time windows
    out("### Burst Patterns (multiple queries within 5 minutes)")
    out("")
    bursts = []
    i = 0
    while i < len(timestamps):
        burst = [i]
        j = i + 1
        while j < len(timestamps) and abs((timestamps[i] - timestamps[j]).total_seconds()) < 300:
            burst.append(j)
            j += 1
        if len(burst) >= 3:
            bursts.append(burst)
        i = j if j > i + 1 else i + 1

    out(f"- **Bursts detected** (3+ queries in 5 min): {len(bursts)}")
    if bursts:
        # Sort by size
        bursts.sort(key=lambda b: len(b), reverse=True)
        out("")
        out("### Top 10 Largest Bursts")
        out("")
        for bi, burst in enumerate(bursts[:10], 1):
            ts_start = timestamps[burst[0]].strftime("%m/%d %H:%M")
            ts_end = timestamps[burst[-1]].strftime("%H:%M")
            duration = abs((timestamps[burst[0]] - timestamps[burst[-1]]).total_seconds())
            out(f"**Burst {bi}**: {len(burst)} queries at {ts_start}-{ts_end} ({duration:.0f}s span)")
            for idx in burst[:5]:
                q = queries[idx]
                desc_short = q["description"][:80].replace("\n", " ")
                score = parse_score(q["title"]) or "?"
                out(f"  - Score={score}: {desc_short}")
            if len(burst) > 5:
                out(f"  - ... and {len(burst) - 5} more")
            out("")

    # ===== 9. TEMPORAL PATTERNS =====
    out("---")
    out("## 9. Temporal Patterns")
    out("")

    # Hour of day distribution (UTC)
    hour_counts = Counter(ts.hour for ts in timestamps)
    out("### Queries by Hour (UTC)")
    out("")
    out("| Hour (UTC) | Queries | % | Visual |")
    out("|------------|---------|---|--------|")
    for h in range(24):
        cnt = hour_counts.get(h, 0)
        pct = cnt / total * 100
        bar = "#" * int(pct)
        out(f"| {h:02d}:00 | {cnt} | {pct:.1f}% | {bar} |")
    out("")

    # Day of week
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow_counts = Counter(ts.weekday() for ts in timestamps)
    out("### Queries by Day of Week (UTC)")
    out("")
    out("| Day | Queries | % |")
    out("|-----|---------|---|")
    for d in range(7):
        cnt = dow_counts.get(d, 0)
        pct = cnt / total * 100
        out(f"| {dow_names[d]} | {cnt} | {pct:.1f}% |")
    out("")

    # Peak hours
    peak_hours = hour_counts.most_common(5)
    out("### Peak Hours (UTC)")
    out("")
    for h, c in peak_hours:
        out(f"- **{h:02d}:00 UTC**: {c} queries ({c/total*100:.1f}%)")
    out("")

    # Timezone inference
    out("### Timezone Inference")
    out("")
    # If peak is around 14-16 UTC, that's evening in Asia (UTC+8 = 22-24)
    # If peak is around 8-12 UTC, that's morning in Europe / afternoon in Asia
    # If peak is around 14-20 UTC, that's afternoon in Americas / night in Asia
    peak_h = peak_hours[0][0]
    out(f"- Peak hour is **{peak_h:02d}:00 UTC**")
    out(f"  - = {(peak_h+8)%24:02d}:00 in UTC+8 (East Asia / Taiwan / China)")
    out(f"  - = {(peak_h+1)%24:02d}:00 in UTC+1 (Central Europe)")
    out(f"  - = {(peak_h-5)%24:02d}:00 in UTC-5 (US East)")
    out(f"  - = {(peak_h-8)%24:02d}:00 in UTC-8 (US West)")
    out("")

    # Activity by UTC hour ranges
    asia_morning = sum(hour_counts.get(h, 0) for h in [0, 1, 2, 3, 4, 5])  # UTC 0-5 = Asia 8-13
    europe_afternoon = sum(hour_counts.get(h, 0) for h in [8, 9, 10, 11, 12, 13])  # UTC 8-13
    us_afternoon = sum(hour_counts.get(h, 0) for h in [17, 18, 19, 20, 21, 22])  # UTC 17-22
    asia_evening = sum(hour_counts.get(h, 0) for h in [11, 12, 13, 14, 15, 16])  # UTC 11-16 = Asia 19-24

    out("### Regional Activity Estimate (by UTC hour mapping)")
    out("")
    out(f"- Asia working hours (UTC 0-5 = UTC+8 08-13): {asia_morning} queries ({asia_morning/total*100:.1f}%)")
    out(f"- Asia evening (UTC 11-16 = UTC+8 19-24): {asia_evening} queries ({asia_evening/total*100:.1f}%)")
    out(f"- Europe afternoon (UTC 8-13 = CET 9-14): {europe_afternoon} queries ({europe_afternoon/total*100:.1f}%)")
    out(f"- US afternoon (UTC 17-22 = EST 12-17): {us_afternoon} queries ({us_afternoon/total*100:.1f}%)")
    out("")

    # ===== 10. QUALITY ASSESSMENT =====
    out("---")
    out("## 10. Quality Assessment — Description Length")
    out("")

    desc_lengths = [len(q["description"]) for q in queries]
    avg_len = sum(desc_lengths) / len(desc_lengths)
    med_len = sorted(desc_lengths)[len(desc_lengths) // 2]

    out(f"- **Mean description length**: {avg_len:.0f} chars")
    out(f"- **Median**: {med_len} chars")
    out(f"- **Min**: {min(desc_lengths)} chars")
    out(f"- **Max**: {max(desc_lengths)} chars")
    out("")

    # Length buckets
    len_buckets = [
        (0, 20, "Very short (<20)"),
        (21, 50, "Short (21-50)"),
        (51, 100, "Medium (51-100)"),
        (101, 200, "Detailed (101-200)"),
        (201, 500, "Very detailed (201-500)"),
        (501, 99999, "Extensive (500+)"),
    ]
    out("### Description Length Distribution")
    out("")
    out("| Bucket | Count | % |")
    out("|--------|-------|---|")
    for lo, hi, label in len_buckets:
        cnt = sum(1 for l in desc_lengths if lo <= l <= hi)
        out(f"| {label} | {cnt} | {cnt/total*100:.1f}% |")
    out("")

    # Score vs description length correlation
    out("### Score vs Description Length")
    out("")
    short_scores = [parse_score(q["title"]) for q in queries if len(q["description"]) <= 50 and parse_score(q["title"]) is not None]
    medium_scores = [parse_score(q["title"]) for q in queries if 51 <= len(q["description"]) <= 150 and parse_score(q["title"]) is not None]
    long_scores = [parse_score(q["title"]) for q in queries if len(q["description"]) > 150 and parse_score(q["title"]) is not None]

    if short_scores:
        out(f"- Short descriptions (<=50 chars): avg score = {sum(short_scores)/len(short_scores):.1f} (n={len(short_scores)})")
    if medium_scores:
        out(f"- Medium descriptions (51-150 chars): avg score = {sum(medium_scores)/len(medium_scores):.1f} (n={len(medium_scores)})")
    if long_scores:
        out(f"- Long descriptions (>150 chars): avg score = {sum(long_scores)/len(long_scores):.1f} (n={len(long_scores)})")
    out("")

    # ===== 11. KW SOURCE DISTRIBUTION =====
    out("---")
    out("## 11. Keyword Source Distribution")
    out("")

    kw_source_counts = Counter(q["fields"].get("KW Source", "unknown") for q in queries)
    out("| KW Source | Count | % |")
    out("|-----------|-------|---|")
    for src, cnt in kw_source_counts.most_common():
        out(f"| {src} | {cnt} | {cnt/total*100:.1f}% |")
    out("")

    pivot_source_counts = Counter(q["fields"].get("Pivot Source", "unknown") for q in queries)
    out("| Pivot Source | Count | % |")
    out("|-------------|-------|---|")
    for src, cnt in pivot_source_counts.most_common():
        out(f"| {src} | {cnt} | {cnt/total*100:.1f}% |")
    out("")

    # ===== 12. INTERESTING QUERIES =====
    out("---")
    out("## 12. Notable Queries")
    out("")

    # Lowest scores (best blue ocean opportunities)
    out("### Top 10 Lowest Scores (Blue Ocean)")
    out("")
    scored_queries = [(parse_score(q["title"]), q) for q in queries if parse_score(q["title"]) is not None]
    scored_queries.sort(key=lambda x: x[0])

    out("| Score | Description (first 120 chars) | Date |")
    out("|-------|-------------------------------|------|")
    for s, q in scored_queries[:10]:
        desc = q["description"][:120].replace("\n", " ").replace("|", "/")
        dt = parse_timestamp(q["timestamp"]).strftime("%m/%d")
        out(f"| {s} | {desc} | {dt} |")
    out("")

    # Highest scores (most competitive)
    out("### Top 10 Highest Scores (Red Ocean)")
    out("")
    out("| Score | Description (first 120 chars) | Date |")
    out("|-------|-------------------------------|------|")
    for s, q in scored_queries[-10:]:
        desc = q["description"][:120].replace("\n", " ").replace("|", "/")
        dt = parse_timestamp(q["timestamp"]).strftime("%m/%d")
        out(f"| {s} | {desc} | {dt} |")
    out("")

    # ===== SUMMARY =====
    out("---")
    out("## Summary & Key Insights")
    out("")
    out(f"1. **{total} queries** over {total_days} days ({first_date} to {last_date}), averaging {avg_per_day:.1f}/day")

    # Growth trend
    if len(sorted_dates) >= 4:
        first_half = sorted_dates[:len(sorted_dates)//2]
        second_half = sorted_dates[len(sorted_dates)//2:]
        first_avg = sum(c for _, c in first_half) / len(first_half)
        second_avg = sum(c for _, c in second_half) / len(second_half)
        growth = ((second_avg - first_avg) / first_avg) * 100 if first_avg > 0 else 0
        out(f"2. **Growth trend**: First half avg {first_avg:.1f}/day, second half avg {second_avg:.1f}/day ({growth:+.0f}%)")

    avg_s = sum(scores) / len(scores) if scores else 0
    out(f"3. **Average signal score**: {avg_s:.1f}/100 — majority of ideas land in the moderate-to-crowded range")

    deep_pct = deep_c / (quick_c + deep_c) * 100 if (quick_c + deep_c) > 0 else 0
    out(f"4. **Deep scan adoption**: {deep_pct:.1f}% — {'high' if deep_pct > 50 else 'moderate' if deep_pct > 30 else 'low'} upgrade rate")

    top_lang = lang_counts.most_common(1)[0] if lang_counts else ("?", 0)
    out(f"5. **Dominant language**: {top_lang[0]} ({top_lang[1]/total*100:.1f}%)")

    top_cat = cat_counts.most_common(1)[0] if cat_counts else ("?", 0)
    out(f"6. **Most popular category**: {top_cat[0]} ({top_cat[1]} queries, {top_cat[1]/total*100:.1f}%)")

    out(f"7. **Duplicate/similar groups**: {len(similar_groups)} groups ({total_dupes} queries) — indicates repeat validation or power users")

    busiest_day = top_days[0]
    out(f"8. **Busiest day**: {busiest_day[0]} with {busiest_day[1]} queries")

    out(f"9. **Burst behavior**: {len(bursts)} bursts of 3+ queries within 5 minutes — users testing multiple ideas rapidly")

    out(f"10. **Description quality**: median {med_len} chars — {'good detail' if med_len > 80 else 'moderate detail' if med_len > 40 else 'sparse descriptions'}")
    out("")

    # Save to file
    report_text = "\n".join(report_lines)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n\n=== Report saved to {OUTPUT_PATH} ===")


if __name__ == "__main__":
    main()
