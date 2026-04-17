# Limbus Company 9.5.1 繁體中文補丁

Canto 9.5.1「交織之絲」(Fili Intrecciati) 的繁體中文補丁，給 LimbusLocalizationManager 使用。

## 內容

- 9.5.1 全 18 個故事檔（`E901B`–`E914B`、`S908A`）共 2100+ 條翻譯
- 9.5.1 UI / 章節標題 / 活動橫幅 / 抽卡名稱 47 條
- 完整繼承 LTM (Limbus Traditional Mandarin) 既有翻譯
- 英文源文來自 Italian Espresso Office 4/16 release
- AI subagent 翻譯，詞彙遵循 LTM 角色名稱慣例

## 安裝（朋友端）

### 前置

已安裝 [LimbusLocalizationManager](https://github.com/kimght/LimbusLocalizationManager/releases)。

### 步驟

1. 在 manager 裡點 **Settings → Open Config**（右下兩個圖示）會開啟 `config.toml` 所在資料夾。
   - 或手動開啟 `%APPDATA%\com.kimght.LimbusLocalizationManager\config.toml`
2. 用記事本打開 `config.toml`，在最底下新增：
   ```toml
   [sources.hant-951]
   name = "Canto 9.5.1 繁中補丁"
   url = "https://raw.githubusercontent.com/<OWNER>/<REPO>/main/localizations.json"
   ```
   （把 `<OWNER>/<REPO>` 換成實際 GitHub 帳號/儲存庫）
3. 關閉 manager → 重新打開
4. **Settings → Source** 下拉選單選「Canto 9.5.1 繁中補丁」
5. **Localizations** 頁會看到「Canto 9.5.1 繁中補丁 (auto-translate)」→ 按 **+** 安裝
6. 如果之前已經裝過 `hant-LTM`，兩個可以並存。進遊戲在語言選單切到需要的版本
7. **關掉遊戲→重開**（Unity 只在啟動時載入語言）

## 排錯

- 如果安裝失敗「取得本地化語言失敗」→ 檢查 URL 能不能用瀏覽器打開並看到 JSON
- 如果裝好了但遊戲還顯示英文 → 去 `D:\SteamLibrary\steamapps\common\Limbus Company\` 執行 `delete_local_cache.bat` 清 Unity 快取再開遊戲
- 如果章節切到 `hant-mypatch-951` 還是英文 → 確認 `Lang/config.json` 的 `lang` 欄位是 `hant-mypatch-951`

## License

本補丁衍生自：
- **LTM (LimbusTraditionalMandarin/storyline)** — 繁中翻譯主體（CC BY-NC-SA 4.0）
- **Italian Espresso Office (louzhee/LocalizeLimbusIT)** — 9.5.1 英文源文 (Release v1.0.2, 4/16)
- 其他新章節內容由 Claude Code subagent 翻譯

根據 CC BY-NC-SA 4.0：非商業使用，衍生作品需用相同授權，請保留所有歸屬。
