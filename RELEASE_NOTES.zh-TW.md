# 發版紀錄

[English](RELEASE_NOTES.md) | 繁體中文

## v1.0.7 - 詮釋資料欄位擴充、評分修正、小數卷號處理與 mirror 清理

### 主要更新
- 新增擷取 Kobo 書籍詳細資料中的欄位，包含各地語系頁面上的語言與書籍識別碼（例如 `語言：`、`書籍ID：`）。
- 新增語言名稱轉 calibre 可接受的 ISO 語言代碼（例如 `中文` -> `zh`），避免語言欄位抓到卻無法正確寫入。
- 新增 EAN 支援：若 Kobo 的書籍 ID 不是合法 ISBN，會寫入 `ean`；若是合法 ISBN，則仍寫入 `isbn`。
- 強化多語系明細欄位解析，完整支援全形冒號（`：`）以及繁中 / 簡中標籤。
- 新增從 Kobo Open Graph 中擷取評分（`og:rating`、`og:rating_scale`、`og:rating_count`），並補上更清楚的診斷 log。
- 修正評分寫入為 calibre 實際使用的 0-5 分制（0.5 星步進），避免因 0-10 轉換導致顯示為滿星。
- 新增更清楚的評分診斷 log（`raw`、`normalized_5`、最終 display 值），方便追查來源與寫入結果。
- 修正小數卷號解析與比對（`13.5`、`Vol.13.5`、`第13.5卷`），避免 `series_index` 被截斷或誤覆寫。
- 改善從標題回推系列名稱時對小數卷號的處理，避免破壞基礎系列名。
- 移除 Kobo mirror 站（`kobo.com.tw`）支援，統一改用穩定的全球站（`kobo.com`）。
- 打包檔名加入版本號，例如：`dist/BetterKoboMetadata-v1.0.7.zip`。

---

## v1.0.6 - 標題正規化、結構化資料擷取與 CJK 支援強化

### 主要更新
- 新增 `_normalize_digits`：正規化 Unicode / 全形數字並去除數字前導零。
- 新增 `_normalize_title_for_match`：支援 CJK / 西文卷號格式差異的模糊標題匹配（第N卷、Vol.N 等）。
- 新增 `_extract_volume`：從標題擷取基礎書名與卷號，用於跨格式公平比對。
- 改善 `_volume_score`：基於擷取卷號與基礎書名相似度的更清晰評分邏輯。
- 新增 `_extract_series_index_from_text`：多語系系列號解析（CJK 與西文格式）。
- 新增 `_derive_series_from_title`：Kobo 未提供系列區塊時，從標題回推系列名稱。
- 新增 `_metadata_match_score`：使用已解析的詮釋資料（書名 + series_index）對候選結果重新排序，解決卷 1 / 10 / 11 誤配問題。
- 新增 `_normalize_person_name` / `_normalized_author_set`：健全的作者名稱正規化，支援多種分隔符（`,`、`、`、`/`、`&` 等）。
- 新增 `_author_match_bonus` / `_author_overlap_count`：強化作者重疊 tie-break，降低同名跨作者誤配。
- 新增 `_is_manga_candidate`：根據標籤、系列名、書名判斷漫畫候選，用於多作者歧義處理。
- 新增 `_candidate_volume`：統一從書名與 `series_index` 擷取卷號。
- 新增 `_extract_first_regex`：通用多模式 regex 擷取輔助函式。
- 新增 `_normalize_cjk_spacing`：移除擷取欄位中 CJK 字元之間的意外空格。
- 改善 `_extract_structured_fallback`：全面的 `ld+json` 及行內 JSON 擷取，涵蓋 `publisher`、`series`、`series_index`、`pubdate`。
- 封面搜尋現支援可設定候選數量（`cover_search_num_matches`），啟用卷數感知封面抓取。
- `identify` 重排管線在分數排序前先套用作者重疊保護，批量抓取結果更穩定。

---

## v1.0.5 - 穩定公開版（卷數安全匹配）

第一個穩定公開版本，重點是提升 Kobo 漫畫詮釋資料匹配正確率。

### 主要更新
- 新增「同卷號候選硬過濾」（查詢包含卷號時）。
- 改善同名作品的作者歧義處理。
- 在多作者歧義場景加入漫畫優先 tie-break。
- 強化 `publisher`、`series`、`pubdate` 的 fallback 解析。
- 改善高解析度封面 URL 正規化與快取邏輯。

### 為何做這版
此版本針對批量下載詮釋資料常見問題：
- 漫畫與輕小說同名混淆。
- 卷數誤配（例如 1 被挑成 19/20）。
- Kobo 頁面結構差異導致欄位遺失。

### 已知行為
- 若書籍已有錯誤 `kobo:` identifier，identifier 直查仍可能命中錯書。
- 建議先清除或修正 identifier 再重新抓取。

### 套件
- 插件壓縮檔：`dist/BetterKoboMetadata.zip`

### 預留位置
- 預計會補上「修正前後」截圖，展示批量匹配改善效果。

---

## 1.0.4
- 加入最強作者重疊保護，降低同名誤配。
- 先以作者重疊分組，再做分數排序。

## 1.0.3
- 修正 `source_relevance` 的語義，對齊 calibre 排序行為。

## 1.0.2
- 在多作者歧義情境加入漫畫偏好 tie-break。

## 1.0.1
- 加入從標題回推系列名稱的 fallback。

## 1.0.0
- 首次公開基線版本。
- 包含卷數感知匹配與 Kobo 解析強化。
