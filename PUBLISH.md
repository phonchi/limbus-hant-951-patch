# 發佈到 GitHub 流程（你端）

## 一次性設定

1. **建 GitHub repo**：進 https://github.com/new
   - Repository name: 例如 `limbus-hant-951-patch`
   - Public（不然朋友下載需登入）
   - 不要初始化 README（我們有自己的）

2. **上傳 3 個檔案到 repo 主分支**：
   - `localizations.json`
   - `README.md`
   - `PUBLISH.md`（可選）

   最簡單：repo 頁 → Add file → Upload files → 拖曳 dist/share/ 裡的檔案 → Commit

3. **建 Release 放 zip**：
   - repo 頁右側「Releases」→「Create a new release」
   - Tag: `v1` (或日期 `2026-04-17`)
   - Title: `Canto 9.5.1 繁中補丁 v1`
   - 拖曳 `my-patch.zip` 到「Attach binaries」區
   - Publish release

4. **修改 `localizations.json` 的 URL**：
   - 目前 URL 裡有 placeholder `<YOUR_USERNAME>/<YOUR_REPO>`
   - 改成實際 GitHub Release 的 zip 下載 URL
     ```
     https://github.com/<你的帳號>/limbus-hant-951-patch/releases/download/v1/my-patch.zip
     ```
   - 在 GitHub 網頁上 Edit `localizations.json` → 改完 Commit

5. **取得給朋友的 raw URL**：
   - 點 repo 裡的 `localizations.json` → 右上角「Raw」按鈕
   - 複製那個 URL（格式通常是 `https://raw.githubusercontent.com/<OWNER>/<REPO>/main/localizations.json`）
   - 把這個 URL 給朋友

## 之後要更新

1. 重新跑自動翻譯產出新 `my-patch.zip`（在你 WSL 跑 `uv run translate finalize`）
2. Bump `localizations.json` 裡的 `version` 字串（隨便加後綴，如 `-v2`）
3. 上傳新 `my-patch.zip` 為新 Release（或 Edit release 替換）
4. 把 `localizations.json` 的 `url` 改成新 Release URL、`size` 改成新 zip 大小
5. 朋友端的 manager 會偵測到 version 變更並提示 **Update**

## Pro tip

如果你怕朋友不會手動編 config.toml，可以把 raw URL 做成 QR code 或用 Discord 固定訊息分享。

## 使用 `gh` CLI 自動化（可選）

如果你想自動化整個流程：

```bash
# 在 WSL 安裝 gh (sudo)
sudo apt install gh && gh auth login

# 在 dist/share/ 執行
cd scripts/auto_translate/dist/share
gh repo create limbus-hant-951-patch --public --source=. --push
gh release create v1 my-patch.zip --title "Canto 9.5.1 繁中補丁 v1" --notes "Initial release"
```
