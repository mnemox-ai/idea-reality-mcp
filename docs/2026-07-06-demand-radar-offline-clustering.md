# Plan — Demand Radar：offline 需求聚類

> 作者：Sean + Claude｜2026-07-06｜狀態：規劃（待拍板才 build）
> 母計畫：`docs/2026-07-06-demand-sensing-accelerator-master-plan.md`（這份是其 §4 殺手鐧 + §2 crowd 加速的落地設計）
> 一句話：**把 10,150 筆 query log 的 embedding 離線聚成 ~100 個「需求主題」，存成一張小表；查詢時只比對 ~100 個中心點（<10ms、記憶體 <1MB）→ 同時解決「crowd 太慢」和「做出 Demand Radar 殺手鐧」。**

---

## 0. 為什麼是這個（不是 ANN 索引）

- ANN 向量索引在現有環境**建不起來**（Turso HTTP 60s 上限、libsql Windows hang、CLI 無 Windows）。
- 但 crowd 慢的本質是「查詢要跟 10k 筆逐一比」。**聚類把它變成「跟 ~100 個主題中心比」**——快 100 倍，且**不需要 Turso 向量索引、不需要對大表做任何危險操作**。
- 而且聚類**本來就是 Demand Radar 的資料底**（§4）：主題 = 「大家在想的需求空間」，可算熱度/趨勢/飽和度。一石二鳥。

---

## 1. 架構：離線重、線上輕

```
[ 離線 script（週期跑）]                          [ 線上 API（每次查詢）]
 讀 10k embedding + created_at (唯讀)              embed 查詢一次 (OpenAI ~0.5s)
        │                                                  │
 MiniBatchKMeans 聚 ~100 群 (sklearn, 幾秒)         比對 ~100 個中心 (numpy, <10ms)
        │                                                  │
 每群算: 中心/標籤/成員數/90d 熱度/趨勢              → 命中主題 → 回該主題預算好的熱度/趨勢
        │                                                  │
 寫 ~100 列到 demand_topics 表 (小、安全)          載入 ~100 中心進記憶體 (~0.6MB, TTL cache)
```

**關鍵**：所有重算在**離線**；線上只做「1 次 embed + 100 次點積」。記憶體 ~0.6MB（100×1536×4），**不是 60MB 全矩陣**——記取 OOM 教訓，這是 memory-safe 的。

---

## 2. 資料模型：一張小表 `demand_topics`

```sql
CREATE TABLE demand_topics (
  topic_id      INTEGER PRIMARY KEY,
  centroid      BLOB     NOT NULL,   -- packed float32 1536-d（同 embedding 格式）
  label         TEXT,                -- 人讀標籤（代表性 idea + 共同關鍵字）
  sample_ideas  TEXT,                -- JSON: 最接近中心的 3-5 個真 idea_text
  member_count  INTEGER,             -- 這主題累積多少筆搜尋
  searches_90d  INTEGER,             -- 近 90 天
  prev_90d      INTEGER,             -- 前一個 90 天（趨勢基準）
  trend         TEXT,                -- rising | steady | cooling
  updated_at    TEXT
);
```

- **~100 列、每列 ~6KB centroid ≈ 0.6MB 總量**。寫入是小操作，**不碰 score_history 那張 10k 大表**（安全）。
- **不需要** 在 score_history 上加 topic_id 欄或 backfill——離線 script 在記憶體裡完成「每筆指派到最近中心 + 依時間窗聚合」，只寫出聚合結果（見 §3）。這樣**完全不對大表做寫入/DDL**。

---

## 3. 離線 pipeline（`scripts/build_demand_topics.py`）

沿用既有 `scripts/backfill_embeddings_http.py` 的模式（Turso HTTP client、分塊讀）：

1. **讀**（唯讀、分塊，每塊<60s）：`SELECT idea_hash, idea_text, created_at, embedding FROM score_history WHERE embedding IS NOT NULL`（10k 筆 ~60MB，分塊拉）。
2. **正規化**：每個向量 L2 normalize（讓 euclidean k-means ≈ cosine）。
3. **聚類**：`MiniBatchKMeans(n_clusters=K)` — K 起手 **100**（可 elbow/silhouette 調）。10k×1536 幾秒內跑完。
4. **指派 + 聚合（在記憶體，不回寫大表）**：每筆算最近中心 → 依 `created_at` 分「近 90d / 前 90d」累計每主題計數 → 算 trend。
5. **標籤**：每群取最接近中心的 3-5 筆 `idea_text` 當 `sample_ideas` + 抽共同關鍵字當 `label`。
6. **寫**：`DELETE FROM demand_topics; INSERT ... (~100 列)`（小、安全、冪等；每次重跑整批換新）。

**跑在哪**：先做成**手動/本機跑的一次性 script**（讀走 HTTP 分塊、sklearn 在本機、寫 ~100 列）。之後上 **Render cron**（週期重算，維持新鮮）。⚠️ sklearn 只在**離線 script**用，**不進 API**（API 只 numpy 點積，保持輕）。

---

## 4. 線上整合（`api/report.py`）

新增 `_topic_demand(query_embedding) -> dict | None`：
1. 載入 `demand_topics` 的 ~100 中心進**行程內 cache**（TTL，~0.6MB）。
2. query 向量 vs 100 中心 cosine（numpy，<10ms）→ 取最近主題（+ 距離門檻，太遠→None＝「這需求很獨特」）。
3. 回該主題的 `searches_90d / prev_90d / trend / label / sample_ideas`。

- **取代 `_demand_heat` 的 hot-path**：`demand_heat` 從「全掃 10k ~6s」→「~0.5s（embed）+ <10ms（比對）」。
- **per-idea 精確最近鄰**（去重/相似 idea 清單）仍可留在**背景/deep** 用現有全掃（延遲不重要）。
- **記憶體**：只載 100 中心，非 10k 全矩陣 → 安全，不會重演 OOM。

**解鎖**：demand 變快後 → **AngelRun 同步 ideaCheck 可重新帶 demand**（不再逼 timeout）+ **scan flash 首層也能帶 demand**（現在跳過的）。

---

## 5. Demand Radar 公開 feed（§4.2 成長引擎）

`demand_topics` 直接就是「本週需求趨勢榜」的資料源：
- 新 `GET /api/demand-radar`：回 `trend='rising'` 的主題 top-N（label/sample_ideas/searches_90d/trend）。
- 官網一頁「大家最近想叫 AI 蓋什麼、哪些在升溫」——**只有我們資料做得出、天生吸 SEO/GEO**（idea-reality Google 本來就第一來源）。
- 每個主題掛 **AngelRun CTA**「去開這個團 / 看誰在做」＝導流 + 飛輪。
- 既有 `/api/pulse`/`/api/social-proof` 骨架可複用/升級。

---

## 6. 分階段 + 粗估

| 階段 | 內容 | 檔案 | 粗估 | 風險 |
|------|------|------|------|------|
| **A. 離線聚類** | `build_demand_topics.py`（讀→kmeans→聚合→寫 demand_topics）+ 建 `demand_topics` 表 | scripts + 1 小 migration | ~0.5 天 | 低（唯讀大表 + 小寫入） |
| **B. 線上 topic 熱度** | `report._topic_demand` + cache；`demand_heat` hot-path 改走它；重新開 AngelRun/flash 的 demand | api/report.py | ~0.5 天 | 低（純 code + 小表讀） |
| **C. 公開 Demand Radar** | `/api/demand-radar` + 官網趨勢頁 + AngelRun CTA | api + 前端 | ~1-2 天 | 低-中（前端 lane） |
| **D. 刷新 cron** | Render cron 週期重跑 A | render.yaml | ~0.5 天 | 低 |

**建議順序**：A → B（先把 crowd 弄快 + 解鎖 demand）→ C（殺手鐧對外）→ D（自動新鮮）。A+B 半天多就能讓 demand 從 6s→0.5s 且安全。

---

## 7. 要拍板的決策（其餘我給預設）

- **K（主題數）**：起手 **100**（~8,300 distinct ideas，平均每主題 ~80 筆）。之後看標籤品質用 silhouette 調。→ 我用預設 100 先做。
- **刷新頻率**：**每週**重算（需求變化不快、省成本）。→ 預設每週。
- **跑在哪**：先**本機一次性**驗出效果，再上 **Render cron**。→ 預設這樣。
- **公開粒度**（承母計畫決策 C）：主題級趨勢公開（磁鐵）、想法級深度 gated。→ 已定。

---

## 8. 安全邊界（記取 2026-07-06 的 DB 教訓）

- **絕不對 `score_history`（10k）做同步大 DDL/大 UPDATE 走 HTTP**（會撞 Turso 60s 上限、churning 拖垮 live）。本計畫**只對大表唯讀分塊**。
- 寫入只碰 `demand_topics`（~100 列小表）。
- API 端只載 ~100 中心（<1MB），**不載 10k 全矩陣**（不重演 OOM）。
- sklearn 只在離線 script；API 保持輕（只 numpy）。
- 每步 idempotent、可重跑；離線 script 失敗不影響 live（線上有 `_topic_demand` 回 None → fallback 現有行為）。

---

## 附：與現況的銜接
- embedding 已全備（10,150 筆，raw float32 BLOB，`embedding` 欄）——聚類直接讀這個，**不需要** embedding_vec/ANN 那套（那條已放棄）。
- 殘留的 `embedding_vec` 欄 + orphan shadow 表無害，可日後清（非本計畫依賴）。
- `_demand_heat`（現有全掃版）保留當 fallback；`_topic_demand` 上線後成為 hot-path 主力。
