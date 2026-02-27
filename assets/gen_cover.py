"""Generate Dev.to cover image (1000x420) and demo result screenshot."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from PIL import Image, ImageDraw, ImageFont

# --- Cover Image ---
W, H = 1000, 420
img = Image.new("RGB", (W, H), "#0d1117")
draw = ImageDraw.Draw(img)

# Divider
draw.rectangle([0, 0, W // 2, H], fill="#161b22")
draw.line([(W // 2, 0), (W // 2, H)], fill="#30363d", width=2)

# Try to load fonts
try:
    font_bold = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 28)
    font_big = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 32)
    font_label = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 14)
    font_sub = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 15)
    font_stats = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 20)
    font_tag = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 13)
except:
    font_bold = ImageFont.load_default()
    font_big = font_bold
    font_label = font_bold
    font_sub = font_bold
    font_stats = font_bold
    font_tag = font_bold

# Left side - ChatGPT
draw.text((50, 80), "CHATGPT", fill="#f85149", font=font_label)
draw.text((50, 120), '"Great idea!', fill="#e6edf3", font=font_big)
draw.text((50, 160), 'Let me help you', fill="#e6edf3", font=font_big)
draw.text((50, 200), 'build it"', fill="#e6edf3", font=font_big)
draw.text((50, 260), "Based on: training data opinions", fill="#8b949e", font=font_sub)
draw.text((50, 285), "Sources searched: 0", fill="#8b949e", font=font_sub)

# Right side - idea-reality-mcp
draw.text((540, 80), "IDEA-REALITY-MCP", fill="#3fb950", font=font_label)
draw.text((540, 120), "reality_signal: 90", fill="#e6edf3", font=font_big)
draw.text((540, 185), "847 repos", fill="#58a6ff", font=font_stats)
draw.text((540, 215), "9,094 stars", fill="#58a6ff", font=font_stats)
draw.text((540, 245), "254 HN mentions", fill="#58a6ff", font=font_stats)
draw.text((540, 295), "Based on: live API data from 5 sources", fill="#8b949e", font=font_sub)

# Bottom tagline
draw.text((260, 380), "WE SEARCH. THEY GUESS.  github.com/mnemox-ai/idea-reality-mcp", fill="#484f58", font=font_tag)

# Border
draw.rectangle([0, 0, W-1, H-1], outline="#30363d", width=1)

img.save("assets/devto-cover.png", "PNG")
print("cover saved: assets/devto-cover.png")

# --- Demo Result Image ---
W2, H2 = 800, 500
img2 = Image.new("RGB", (W2, H2), "#0f172a")
d2 = ImageDraw.Draw(img2)

try:
    f_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 22)
    f_body = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 18)
    f_mono = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 16)
    f_big_num = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 64)
    f_label_sm = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 14)
    f_small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 14)
except:
    f_title = ImageFont.load_default()
    f_body = f_title
    f_mono = f_title
    f_big_num = f_title
    f_label_sm = f_title
    f_small = f_title

# Header
d2.rectangle([0, 0, W2, 50], fill="#1e293b")
d2.text((20, 12), "mnemox.ai/check", fill="#94a3b8", font=f_body)
d2.text((W2 - 180, 12), "idea-reality-mcp", fill="#3fb950", font=f_body)

# Search query
d2.rectangle([30, 70, W2 - 30, 110], fill="#1e293b", outline="#334155")
d2.text((45, 80), '"AI code review tool"', fill="#e2e8f0", font=f_body)

# Signal gauge area
d2.text((60, 140), "REALITY SIGNAL", fill="#64748b", font=f_label_sm)

# Big number
d2.text((60, 165), "90", fill="#f85149", font=f_big_num)
d2.text((170, 200), "/ 100", fill="#64748b", font=f_title)

# Verdict
d2.rectangle([60, 250, 350, 280], fill="#7f1d1d")
d2.text((70, 254), "EXTREMELY HIGH COMPETITION", fill="#fca5a5", font=f_small)

# Stats
d2.text((400, 140), "SOURCES", fill="#64748b", font=f_label_sm)
d2.text((400, 170), "GitHub repos", fill="#94a3b8", font=f_body)
d2.text((620, 170), "847", fill="#58a6ff", font=f_body)
d2.text((400, 200), "Top project", fill="#94a3b8", font=f_body)
d2.text((620, 200), "reviewdog", fill="#58a6ff", font=f_body)
d2.text((400, 230), "Max stars", fill="#94a3b8", font=f_body)
d2.text((620, 230), "9,094", fill="#58a6ff", font=f_body)
d2.text((400, 260), "HN mentions", fill="#94a3b8", font=f_body)
d2.text((620, 260), "254", fill="#58a6ff", font=f_body)

# Similar projects
d2.text((60, 310), "TOP SIMILAR PROJECTS", fill="#64748b", font=f_label_sm)
projects = [
    ("reviewdog/reviewdog", "9,094 stars", "Automated code review tool"),
    ("danger/danger", "5,312 stars", "Automate code review chores"),
    ("prontolabs/pronto", "2,847 stars", "Quick automated code review"),
]
y = 340
for name, stars, desc in projects:
    d2.text((60, y), name, fill="#58a6ff", font=f_mono)
    d2.text((380, y), stars, fill="#e5c07b", font=f_small)
    d2.text((490, y), desc, fill="#94a3b8", font=f_small)
    y += 30

# Pivot suggestion
d2.rectangle([30, 440, W2 - 30, 480], fill="#1e293b", outline="#334155")
d2.text((45, 448), "Pivot hint:", fill="#64748b", font=f_small)
d2.text((130, 448), "Consider focusing on a niche language or framework not well covered", fill="#94a3b8", font=f_small)

# Border
d2.rectangle([0, 0, W2-1, H2-1], outline="#334155", width=1)

img2.save("assets/demo-result.png", "PNG")
print("demo saved: assets/demo-result.png")
