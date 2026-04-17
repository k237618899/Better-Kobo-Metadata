# 貢獻指南

[English](CONTRIBUTING.md) | 繁體中文

感謝你願意為 Better Kobo Metadata 貢獻。

## 開發流程
1. 修改 `kobo_metadata.py` 與/或 `__init__.py`。
2. 打包插件：
   - `bash scripts/build.sh`
3. 本機安裝測試：
   - `/opt/calibre/calibre-customize -a dist/BetterKoboMetadata.zip`
4. 用 calibre identify log 驗證結果。

## Bug 回報建議
請附上：
- 查詢書名 / 作者 / identifiers
- identify log 對應段落
- 預期結果與實際結果對照

## 備註
- 盡量保持匹配邏輯可解釋且可重現。
- 優先提交小而聚焦的修改。
- 非必要不要變更既有 calibre 設定選項名稱（避免相容性問題）。
