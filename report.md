# 9.5.2 繁中補丁報告

- 基底：官方 `hant-LTM` `1780889854`
- 候選檔案：66
- 候選 entries：2606
- 候選欄位：3714
- 歷史覆蓋族群：1630
- Zip：`dist/my-patch.zip` (12680518 bytes, 2017 files)
- QA issues：0

## 策略

以官方 LTM 為基底，只 overlay 9.5.2 缺檔、缺 id、英文 placeholder 欄位；額外使用 LLC_zh-CN 的歷史覆蓋檔案族群確認漏檔，不翻譯 asset/model/key 欄位。
