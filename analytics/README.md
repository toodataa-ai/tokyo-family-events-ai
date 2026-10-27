# サイト利用状況（匿名集計）

## 目的・表示

サイト下部に目立たない1行で以下を累計表示する。実測できない場合は数字を捏造せず「計測準備中」またはエラー表示にする。

- `page_home` / `page_search` / `page_copy`: 各ページ表示（PV）の合計。
- `nav_search` / `nav_copy`: イベント検索・コピペ用リストへのリンク／ボタン操作回数。ページ表示とは別集計。
- `copy_field_click` / `copy_all_click`: 個別・一括のコピーボタンを押した回数（失敗も含む）。
- `copy_field` / `copy_all`: クリップボード書き込みが成功した個別・一括コピーの回数。失敗は加算しない。
- `session_start`: タブ単位・日本時間の日付単位のセッション目安。ユーザー人数、UU、純訪問者とは呼ばない。

検索語、コピー本文、個々のイベント名、IP、UA、参照元、ユーザーID、Cookieは保存しない。サーバーDBには「日本日付×イベント種別×件数」のみを保存する。ブラウザ側では当日セッション重複の軽減に `sessionStorage` のみ利用（タブを閉じると消える）。ステージングや開発環境は測定しない。広告ブロッカー・ネットワーク・Bot等により回数は概数である。

## 導入手順（Cloudflareの接続が必要）

1. Cloudflareのアカウントを用意する（Worker/D1は一般に無料枠から利用可能。無料上限超過時は機能制限が発生するためCloudflareの現在の料金/上限を確認する）。
2. `analytics/` 内で `npx wrangler login` を実行する。`npx wrangler d1 create tokyo-family-events-metrics` でD1データベースを作る。
3. `wrangler.example.toml` を `wrangler.toml` にコピーし、Cloudflareから表示された `database_id` を設定する。このファイルの実値はコミットしない。
4. `npx wrangler d1 execute tokyo-family-events-metrics --remote --file=schema.sql` でテーブルを作成する。
5. `npx wrangler deploy` で `worker.mjs` を公開する。表示された `https://...workers.dev` を控える。
6. 接続テスト：`https://...workers.dev/stats` が `schema_version:1` のJSONを返すことを確認し、Cloudflareのログ/DBで正常動作を検証する。
7. **main のステージング検証・承認後に** `site/metrics-config.json` の `enabled` を `true`、`endpoint` をWorkerのURLに設定し、通常のリリース手順で本番反映する。ステージング画面は常に未計測。
8. 本番でトップ・検索・コピー成功の各動作を行い、`/stats` の数値変化とトップ下部表示を照合する。導入前の利用回数は復元できない。

## 障害時・注意点

- 設定がない間はUIに計測準備中と表示し、計測POSTは送信しない。集計先障害でも検索・コピペは継続する。
- ブラウザから送るデータは固定のイベント名のみで、個人情報やURLクエリパラメーターを送信しない。
- Workerは`https://toodataa-ai.github.io`以外のOriginからの書き込みを拒否。ただしOriginは強い認証ではなく、手動リクエスト等による水増しを完全には防げない。必要に応じてCloudflareでレート制限/ボット対策を追加する。
- 不正操作や自動アクセスにより回数が増える場合があり、表示値は正確な利用人数とは異なる。
- WorkerのAPIドメインを変更した場合、接続先だけ改修。データの正本（`data-production`）には追記しない。既存のデータ自動更新から独立させる。
- 既存の production/release ブランチは承認なしに変更しない。Workerと接続先の設定は独立した承認対象とする。

## ファイル

- `site/usage-metrics.js`: 匿名イベント送信、成功数の表示、ステージング除外。
- `site/metrics-config.json`: 接続先スイッチ（初期状態OFF）。
- `analytics/worker.mjs`: `/collect` と `/stats` API。
- `analytics/schema.sql`: 集計DBのスキーマ。
- `analytics/wrangler.example.toml`: Workerデプロイ用の雛形。
- `tests/usage_metrics.test.mjs`: 簡易API・サイト接続・プライバシー監査。

## 2026-10-28 ステージング案：今日＋日別履歴＋端末内の任意利用メモ

- 既存の /stats は以前から JSTの今日と累計を返している。トップ画面に両方表示する。表示はPV、セッションは同一タブ・同一日本日付の概数であり、人数ではない。
- Workerに新しい /history?days=7|30|90|365 を追加。元のD1 event_counts の既存集計を読取専用で日付別に取得。DBスキーマ変更なし、個人識別なし、記録のない日を0件で補間しない。
- 新設 site/usage-history.html で日別PV、ページ移動、コピー成功、セッション目安を一覧・バーで表示。API未配信時は明確に未取得と表示し、今日と累計は引き続き表示できる。
- site/self-usage.js は訪問者が明示的にオンにした場合だけ、このブラウザのlocalStorageへ日別イベント数を保存する。端末ID、ユーザーIDやCookieをサーバーへ送らない。保存停止・消去が可能。記録開始前のデータは復元できず、ほかの端末とは合算しない。共有端末では本人の厳密な区別ができない。
- 他人の利用人数や個々の利用者は現在の匿名集計では判別不能。サイト全体と自分のブラウザの数の差を正確な他者人数として表示しない。
- 従来の匿名計測イベント名・POST契約・セッション重複抑止は維持する。
- 本番公開に必要な作業：GitHub Pagesの改修とは独立して Cloudflare 側で analytics/worker.mjs をデプロイし、実際の /history?days=7 が返ることを検証する。Workerをデプロイせずに日別履歴が利用可能だと主張しない。
