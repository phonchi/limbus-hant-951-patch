# Limbus Company 9.5.2 繁體中文補丁

Canto 9.5.2 新增內容的繁體中文補丁，給
[LimbusLocalizationManager](https://github.com/kimght/LimbusLocalizationManager/releases)
使用。

## 內容

- 基底使用官方 LTM `hant-LTM` 版本 `1780889854`
- 補上 9.5.2 新增故事、事件、戰鬥、UI 與語音文字
- 本次候選範圍：49 個檔案、2482 個 entries、3026 個欄位
- 來源：本機 9.5.2 `en/kr` 語系檔，並以 RCR 2026-06-12 release 交叉查漏
- QA：本次 overlay 範圍 Hangul / 長英文殘留檢查為 0

## 安裝

### 前置

已安裝 LimbusLocalizationManager。

### 使用此分支測試版

1. 在 manager 裡點 **Settings → Open Config** 開啟 `config.toml` 所在資料夾。
   - 或手動開啟 `%APPDATA%\com.kimght.LimbusLocalizationManager\config.toml`
2. 用記事本打開 `config.toml`，在最底下新增：
   ```toml
   [sources.hant-952]
   name = "Canto 9.5.2 繁中補丁"
   url = "https://raw.githubusercontent.com/phonchi/limbus-hant-951-patch/codex/952-patch/localizations.json"
   ```
3. 關閉 manager 後重新打開。
4. **Settings → Source** 下拉選單選「Canto 9.5.2 繁中補丁」。
5. 到 **Localizations** 頁安裝「Canto 9.5.2 繁中補丁 (auto-translate)」。
6. 完全關閉遊戲後重開。Unity 只在啟動時載入語言檔。

## 排錯

- 如果安裝失敗，請確認 `localizations.json` raw URL 能在瀏覽器開啟。
- 如果遊戲仍顯示英文，請完全退出遊戲後重開。
- 必要時在遊戲資料夾執行 `delete_local_cache.bat` 清 Unity 快取。

## 產出與驗證

詳見 `report.md`。建置工具位於 `tools/build_952_patch.py`，本次使用官方
`hant-LTM` 作基底，只 overlay 9.5.2 缺檔、缺 id、英文 placeholder 欄位，
不翻譯 asset/model/key 欄位。

## License

本補丁衍生自：

- **LTM (LimbusTraditionalMandarin/storyline)** — 繁中翻譯主體（CC BY-NC-SA 4.0）
- **ProjectMoon / Limbus Company** — 原始遊戲文字
- **RCR** — 2026-06-12 release 作為檔案覆蓋查漏參照
- 其他新增章節內容由 AI subagent 輔助翻譯

根據 CC BY-NC-SA 4.0：非商業使用，衍生作品需使用相同授權，請保留所有歸屬。
