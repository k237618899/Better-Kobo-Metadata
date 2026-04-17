# Better Kobo Metadata

[English](README.md) | 繁體中文

Better Kobo Metadata 是一個給 calibre 使用的 Kobo 詮釋資料來源插件，重點在於提升漫畫卷數匹配的穩定性，降低同名作品誤配機率。

## 主要功能
- 卷數感知匹配：避免選到錯誤卷數（例如 `1` 被誤配成 `19`/`20`）。
- 作者歧義處理：同名作品時優先匹配正確作者。
- 漫畫 / 輕小說同名衝突處理：減少批次下載時的錯誤結果。
- 強化欄位補抓：改善 `publisher`、`series`、`pubdate` 的 fallback 解析。
- 封面優化：統一高解析度封面 URL 與快取邏輯。

## 環境需求
- calibre 5.0+

## 專案結構
- `__init__.py`：插件入口與 calibre 設定選項
- `kobo_metadata.py`：搜尋、排序、解析與封面邏輯
- `plugin-import-name-kobo_metadata.txt`：calibre 插件匯入名稱檔
- `scripts/build.sh`：打包腳本
- `dist/`：打包輸出目錄
- `logs/`：本地測試 log（預設不提交）

## 打包
在專案根目錄執行：

```bash
bash scripts/build.sh
```

輸出檔案：
- `dist/BetterKoboMetadata.zip`

## 安裝

```bash
/opt/calibre/calibre-customize -a dist/BetterKoboMetadata.zip
```

或在 calibre 圖形介面：
- 偏好設定 -> 插件 -> 從檔案載入插件

## 使用建議
- 在驗證匹配品質時，建議先只啟用 Better Kobo Metadata。
- 若書籍已有錯誤的 `kobo:` identifier，請先清除再重新下載詮釋資料。

## 問題排查
- 若選到錯書，請附上 `logs/identify.log` 或 calibre identify log 對應段落。
- 回報時請提供：查詢書名、作者、identifiers、預期結果與實際結果。

## 開源依賴
- cloudscraper (MIT)
- requests (Apache-2.0)
- urllib3 (MIT)
- idna (BSD-3-Clause)

## 授權
請見 `LICENSE`。
