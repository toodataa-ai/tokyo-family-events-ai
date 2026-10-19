# ためまっぷなかの：GitHub Actions HTTP 403 原因調査

- 調査実行: 2026-10-20 00:07頃 JST
- Run: https://github.com/toodataa-ai/tokyo-family-events-ai/actions/runs/39275175781
- リリースアプリ・本番データは変更していない（読み取り専用）。

## 結論

実際の403レスポンスの `server: cloudflare`、`cf-ray`、HTML `Just a moment...` と `https://challenges.cloudflare.com` を確認。GitHub ActionsからのリクエストがCloudflareブラウザー向けセキュリティチャレンジに遭遇している。収集プログラムのurllibはJavaScriptチャレンジを完了できない。何のルールでチャレンジされたかは外部から断定不可。

### 実測

| 対象 | HTTP | Server | Ray ID / 備考 |
|---|---|---|---|
| https://pc.tamemap.net/1311401 | 403 | cloudflare | a4d0b17b8ccf0d36-MEM |
| https://pc.tamemap.net/1311401/calendar/2026-10?locale=ja | 403 | cloudflare | a4d0b17c1edf3bdf-MEM |
| https://pc.tamemap.net/robots.txt | 403 | cloudflare | a4d0b17d1bd7ae89-JAX |
| https://www.city.tokyo-nakano.lg.jp/ | 200 | CloudFront経由 | GitHubのHTTP取得自体は動作 |

前回2026-10-19の14条件比較（座標変更・除去、月、User-Agentの相違）も全件403だった。ログイン/ブラウザ位置情報ダイアログとは独立している。

## 次の対応

1. ためま運営者へ正式なデータ連携/API/機械アクセス可否を問い合わせる。対象は東京・中野区イベントの公開情報（読み取りのみ）。
2. オーナー側で Cloudflare Security Events を該当 Ray ID・UTC 2026-10-19T15:07:35Z で確認してもらい、適切なら特定リクエストへの例外または正式なデータフィードを提供してもらう。広範囲のセキュリティ無効化は求めない。
3. それまで discovery_sources.json の tamemap_nakano を成功/0候補として偽装しない。取得失敗時はstatus=errorとして公開ゲートを止める。既存イベントを消さない。

資料：
- https://developers.cloudflare.com/cloudflare-challenges/reference/supported-browsers/
- https://developers.cloudflare.com/waf/custom-rules/skip/
- https://www.tamemap.net/qanda/
- https://www.tamemap.net/contact/

この調査記録は診断ブランチのみ。production・data-production・data-stagingには反映しない。
