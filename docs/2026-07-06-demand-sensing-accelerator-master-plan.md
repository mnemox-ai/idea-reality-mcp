# Master Plan — idea-reality × AngelRun：需求感測加速器（YC-parallel）

> 作者：Sean + Claude｜日期：2026-07-06｜狀態：規劃（待 Sean/Kevin 拍板才進 build）
> 一句話：**把 idea-reality 從「暫停監測的驗證工具」升級成一顆「需求感測引擎」，讓官網 + MCP + AngelRun 三個入口同吃這顆引擎；引擎越用資料飛輪越強；最終 idea-reality（感測需求）+ AngelRun（媒合開團 + 比賽加速）＝ 一個以「需求」而非「人」為起點、與 YC 並行的加速器。**

---

## 0. 為什麼這條路能跟 YC 並行

YC 的本質：**發現有潛力的人/想法 → 給資源加速 → demo day 推到投資人面前**。它的起點是「**人**」，靠的是聲譽與人脈網。

我們的起點不一樣，而且是**別人做不出來的獨家**：

- idea-reality 手上有 **~8,300 個不重複真實想法 / 10,156 筆查詢 log**，而且每天還在長——這是「**全世界的人現在正在叫 AI 幫他們蓋什麼、還沒做出來的需求**」。
- GitHub / ProductHunt 是「**已經被做出來的東西**」＝落後指標；query log 是「**還沒做、正在想的需求**」＝**領先指標**。市面上所有「想法驗證」工具都只有落後指標，**沒有人有需求的領先訊號**。
- 所以我們的加速器可以是 **demand-first**：不是等人來 pitch，而是**先從資料看到「哪個需求在升溫、還沒人好好做」，再去媒合/催生做的人**。這是 YC 做不到的角度。

**組合拳**：idea-reality 感測需求 → AngelRun 開團媒合 + 比賽加速 + 站外對接天使 → 做出來的東西回頭變成新訊號。**這就是飛輪，也是「跟 YC 並行」的具體形狀。**

> ⚠️ 合規邊界沿用 AngelRun 既有結論（`angelrun/docs/superpowers/specs/2026-07-01-...competition-angel-accelerator-model.md`）：只用自己的錢、裁量非承諾、站外成交、廣告屬實。這份 plan **不改**那條線，只補「需求感測」這一段。

---

## 1. 一顆引擎，三個入口（架構統一）— 最優先

**現況問題**：引擎其實已經分裂，三個入口吃到的東西不一樣：

| 入口 | 走的路徑 | 吃到外部掃描 | 吃到 semantic 需求庫 |
|------|---------|:---:|:---:|
| 官網完整報告 / `/api/crowd-intel` | full report | deep 可 6 源 | ✅ 剛升級 |
| MCP（AI agent 觸發） | `idea_check` tool | 依 depth | 依路徑 |
| **AngelRun idea 框** | `/api/check` **quick** | **只 2 源** | **❌ 完全沒接** |

**→ 我們剛花力氣活化的 1 萬筆護城河，AngelRun 一點都沒吃到。** 這是 launch 前第一個要收的洞。

### 1.1 目標：定義「唯一引擎契約」，三入口同吃最新
- 把「一次 idea 查詢」的**完整輸出**收斂成一個 versioned response schema（`engine_version` 欄），內含：
  - `reality_signal`（分數）+ `score_breakdown`（可解釋）
  - `top_similars`（外部競品，來源標註）
  - `crowd_intelligence` + **`demand_heat`**（需求庫，semantic）
  - `pivot_hints`（導航）
- 三個入口都拿**同一份**，差別只在「顯示多少」（前端決定），不是「後端給不給」。
- **AngelRun 端**：ideaCheck proxy 從只 map `reality_signal/top_similars/pivot_hints` → **多接 `demand_heat`**，開團漏斗入口直接顯示「這題 90 天內 N 人也在問、升溫中、還沒人真做」＝把判決翻成導航。

### 1.2 交付
- idea-reality：`/api/check` 增加可選 `include=crowd,demand`（預設 lean 不變、避免破既有 client；AngelRun 帶旗標拿完整）。或新開 `/api/check2` versioned。**決策點見 §7-A。**
- AngelRun：`lib/contracts/server/ideaCheck.ts` map 擴充 + 前端漏斗顯示 demand_heat（前端 lane）。

---

## 2. 引擎真相：「搜尋幾個地方都要真正搜尋得到」

Sean 的要求＝**引擎宣稱掃哪些地方，就要真的掃得到、回真結果**，不能有源默默回 0 或塞垃圾。

### 2.1 已知歷史病灶（git log 佐證，部分已修）
- GitHub 曾 80% 查詢回 0（已加 retry/backoff）
- npm 曾灌水 500K+（已加相關性過濾）
- 關鍵字抽取 hyphen/synonym 正規化（已修）

### 2.2 這輪要補的（讓「真正搜尋得到」可驗收）
1. **來源健康度可觀測**：每個 source 每次查詢記「回幾筆 / 命中率 / 錯誤」→ 進 `/api/query-stats` 或新 `/api/source-health`。目標：任何一源長期 0 命中要**看得到**，不是默默壞。
2. **quick vs deep 取捨 → 決策：Skyscanner 式兩層漸進（Sean 2026-07-06 拍板）**：
   - **第一層（秒回）**：quick 3-4 源立刻回，帶 `partial:true` + `idea_hash`，使用者不等。
   - **第二層（背景補完）**：背景跑 deep 全源，前端**輪詢**（先做，`GET /api/history/{idea_hash}` 或新 `/api/check/{hash}`）或 **SSE**（之後）拿更完整版 → competitors 補進來、reality 分數/排序更新。
   - **真串流（每源即時跳出）＝之後再疊**（需 SSE/WebSocket，且分數要邊到邊重算）；MVP 先做兩階段拿 90% 體感。
   - 這是 **P2**（比 P1 重）；P1 先把兩邊同吃引擎做掉，漸進式接著上。
3. **冷啟動**：Render Starter 睡醒慢 → 已是付費 Starter 不睡，但首請求仍有 JIT 成本；漏斗入口加「暖機」ping 或改常駐。
4. **需求原生新來源（往獨家推）**：現有 6 源都是「別人的產出」。真正該加的是**需求原生源**——Reddit「someone should build」、AI agent 的匿名 query（我們自己的 log 就是）、HN Ask。這才餵飛輪。**這是殺手鐧的燃料，見 §4。**

---

## 3. 資料飛輪：讓它越滾越強

**護城河 = query log。每一次查詢都應該讓引擎變強一點。** 現在飛輪有漏氣：

1. **新查詢即時進語意索引**：目前新想法要等 `scripts/backfill_embeddings_http.py` 的 cron 才 embed。改成**查完當下 inline embed 寫入**（`save_score(embedding=)` 已支援）→ 新需求立刻可被下一個人的 semantic 搜到。
2. **去重與聚類**：同一想法重複查（same idea_hash）已知會灌數量 → crowd-intel 已 dedup，但**趨勢/熱度**的計算要用「不重複想法數」而非「原始查詢數」，才不高估需求。
3. **需求聚類 → 主題**：把 8,300 想法用 embedding 聚成「需求主題」（bill-splitting、AI summarizer、rental marketplace…）→ 每個主題可算「熱度、趨勢、飽和度、空白度」。這是 Demand Radar 的資料底。
4. **飛輪指標（要能看到在滾）**：每週不重複想法數、主題數、rising 主題數、覆蓋率（embedded %）、AngelRun 開團回填數。進一張 internal dashboard。

---

## 4. 殺手鐧：Demand Radar（需求雷達）— 打壞市場的那一下

**定位翻轉：從「打分數（判決）」→「需求導航（radar）」。** 市面驗證工具都在回答「你這想法幾分」；我們獨家回答「**這個需求現在多熱、往哪走、空白在哪、誰該去做**」。

### 4.1 產品面（每次查詢的體驗）
- 不只 `reality 72`，而是：「**這題過去 90 天 6 人也在問（↑ rising），最接近的 3 個已做出來的東西是 X/Y/Z，但都沒解決 [空白]。要不要去 AngelRun 開團／找正在做的人？**」
- `demand_heat` 已是雛形，往前推＝核心賣點。

### 4.2 成長面（公開的需求趨勢 feed）— SEO/GEO 磁鐵
- 公開「**本週升溫需求榜**」（`/api/pulse` + `/api/social-proof` 已有骨架）：「這週最多人想叫 AI 蓋的 20 件事、哪些在升溫、哪些已飽和」。
- 這種頁面**天生吸 SEO/GEO 流量**（idea-reality 本來 Google 就是第一來源），而且是**只有我們資料做得出的內容**＝競品抄不了。
- 每個榜單 item 直接掛 **AngelRun CTA**「去開這個團 / 看誰在做」＝ 導流 + 飛輪。

### 4.3 護城河取捨（真決策）
- 公開 Demand Radar＝把獨家資料當**成長引擎**（流量、品牌、飛輪），但也把訊號給了對手看。
- Gated（付費/會員才看深度）＝把它當**產品變現**，但犧牲成長。
- **建議：公開「主題級」趨勢（磁鐵），gated「想法級空白 + 競品深度 + 導航」（變現/導 AngelRun）。** 兩者兼得。**決策點見 §7-C。**

---

## 5. idea-reality 真正上線（從「暫停監測」→ 產品）

現在 `instructions.md` 寫「**暫停開發中，持續監測流量**」。要「真正上線」得補：

1. **定位一句話**：不是「idea validation」（紅海），是「**Demand Radar for what people want AI to build**」。README / 官網 / MCP description 統一改。
2. **變現模型**（骨架已在：lemon/checkout/unlock/claim，PayPal 已移除全免費）：
   - Free：quick 查詢 + 主題級趨勢（磁鐵）
   - Paid（$X/mo）：deep 全源 + 想法級 Demand Radar + watchlist（追蹤某需求主題的熱度變化）+ API 額度
   - 這也接回 `idea_reality_commercialization.md` 的 Watchlist/週報構想。**決策點見 §7-C（跟護城河同一題）。**
3. **可靠性/SLA**：漏斗入口冷啟動、source health（§2）＝上線前 must-fix。
4. **MCP 面**：MCP 版也要吃到 demand_heat（AI agent 幫使用者查 idea 時，直接回需求導航）＝差異化「不是搜尋品質，是 agent 自動觸發 + 獨家需求訊號」。

---

## 6. YC-parallel 模型（兩邊合體怎麼運作）

| 環節 | YC | 我們（idea-reality × AngelRun） |
|------|----|------|
| 起點 | 人來 apply | **資料看到需求**（Demand Radar）+ 人來查 idea |
| 篩選 | 面試、聲譽 | 需求熱度 + reality 訊號 + 開團動能（裁量選拔） |
| 加速 | 3 個月 batch、錢、人脈 | AngelRun 開團媒合 + 比賽層里程碑 + 聚光燈 |
| 出場 | demo day → VC | 站外 demo day / 對接天使（錢走站外，legal-light） |
| 獨家 | 品牌、alumni 網 | **需求領先訊號 + 做東西的追劇飛輪** |

- **不是取代 YC，是並行的另一種「發現」邏輯**：YC 賭人，我們賭「被資料證明在升溫的需求 + 願意做的人」。
- 合規紅線、資本、律師 memo **全部沿用 AngelRun 既有結論**，這份 plan 不新增法律面（避免重複計時）。

---

## 7. 真正要 Sean/Kevin 拍板的決策（其餘我給預設自己決）

> 依「別把決策清單丟給 Sean 扛」原則，這裡只列**真的會改變 plan 形狀**的三題，各附我的建議。工程/方法題我直接用預設做。

- **A. 引擎契約怎麼給** → ✅ **決定：加 `include=` 旗標**（不破既有，AngelRun 帶旗標拿完整 + `engine_version`）。
- **B. quick 涵蓋 vs 速度** → ✅ **決定：Skyscanner 式兩層漸進**（quick 3-4 源秒回 `partial` → 背景 deep 補完，前端輪詢/SSE 補進 competitors 與分數/排序）。真串流之後疊。屬 P2。
- **C. Demand Radar 護城河/變現** → ✅ **決定：主題級趨勢公開當磁鐵、想法級深度 gated 導 AngelRun/變現**。牽動 idea-reality 重新收費 → 收費細節仍待跟 Kevin 對齊（P5）。

---

## 8. 分階段路線圖（建議順序）

> 原則：先讓「兩邊同吃最新引擎」跑起來（低風險、立即價值），再逐步把飛輪與殺手鐧疊上去。每階段可獨立出貨。

| 階段 | 內容 | repo | 粗估 | 依賴 |
|------|------|------|------|------|
| **P0 止血（DONE）** | semantic OOM 根治、Turso 原生向量 LIVE | idea-reality | ✅ 完成 | — |
| **P1 兩邊同吃引擎** | ✅ **DONE**：`/api/check include=` + `engine_version`（idea-reality `fad8414`，live 驗過）+ AngelRun ideaCheck 接 `demandHeat`（`47d5b1b`，tsc/build/tests 綠）。漏斗顯示＝AngelRun issue #40（前端 lane） | 兩邊 | — | ✅ |
| **P2 引擎真相** | source-health 觀測 + quick 涵蓋調整 + 冷啟動暖機 | idea-reality | ~2-3 天 | 決策 B |
| **P3 飛輪加固** | inline embedding 寫入 + 需求聚類（主題）+ 飛輪 dashboard | idea-reality | ~3-4 天 | — |
| **P4 Demand Radar** | 想法級需求導航（產品）+ 公開趨勢榜（成長）+ AngelRun CTA | 兩邊 | ~1 週 | 決策 C |
| **P5 真上線** | 定位/README/MCP desc 改寫 + 變現切分 + SLA | idea-reality | ~2-3 天 | 決策 C + Kevin |

**建議先跑 P1**：它同時是「#1 導流 CTA」和「讓剛升級被真正用到」的交集，半天到一天內兩邊都受益，且不需等任何外部拍板（決策 A 我可用預設先做）。

---

## 附錄：現況資產盤點（規劃基礎，已查證 2026-07-06）
- idea-reality：REST live（Render Starter，付費不睡）、10,156 筆 / 8,337 想法、10,150 embedded、semantic LIVE（`vector_distance_cos`）、358+ stars、Google SEO 第一來源、MCP + REST 雙面、全免費。
- 外部源：quick=GitHub+HN（2）、deep=+npm/PyPI/PH/SO（6）。
- 已有 API 骨架可複用：`/api/pulse`、`/api/social-proof`、`/api/funnel`、`/api/query-stats`、`/api/badge-data`、`/api/crowd-intel`、變現（lemon/checkout/unlock/claim）。
- AngelRun：追劇 MVP + 比賽層加速器 LIVE、ideaCheck 走 quick（未接 semantic）、競爭-天使-加速器定位已定（YC 式，legal-light）。
- 相關記憶/spec：`reference_idea_reality_render_ops`、`project_idea_reality_search_optimization`、`idea_reality_commercialization`、AngelRun northstar-v2 + competition-angel-accelerator spec。
