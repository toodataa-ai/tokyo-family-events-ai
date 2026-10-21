# Canva投稿ドラフト連携 — staging implementation (2026-10-22)

## 使用テンプレート（固定）

ユーザー指定の最終仕上げ版: https://canva.link/8zgsm5y1cwwgd5e
- Canva design ID: `DAHYo7noxKY`
- 1080×1350 px / 7ページ
- 表紙1ページ、イベント2件×5ページ、締め1ページの10件構成
- タイトルは基本72px、長文のみ64～68px目安。文字がはみ出ないことを各ページ目視確認する
- **元テンプレートを更新しない**。ドラフト生成ごとにコピーして編集する

## 現在実装したフロー

1. `search.html` の各カードで「Canvaに追加」をチェック（最大10件）。
2. 選択トレイから `canva.html` へ。順序の上下入れ替え、除外、表紙タイトル修正を行う。
3. 選択IDのみブラウザの localStorage に保持。イベント本体は公開済みのアプリの `loadWeekend`・`mergeEventsAcrossWeeks` で毎回読み取り、保存イベントのスナップショットによる古いデータを使わない。
4. `canva-draft-contract.js` が1～10件の構造化JSON、CSV（1行=1つの7ページデザイン）、Canvaを利用できるChatGPTへ渡す完全な日本語指示を生成。
5. ChatGPT内のCanva連携で元テンプレートをコピーし、選択イベントを配置。**全ページプレビューと保存承認**を経てCanvaドラフトとして確定する。

これは「ChatGPT経由の安全な半自動連携」。現在はサイトからCanva APIを直接実行しない。手動のコピー＆ペーストをなくす「サイトからCanvaへ1クリックで新規ドラフト生成」は未接続であり、接続済みと偽装しない。

## 将来の直接連携（要OAuthサーバー設定）

Canva Connect API の `create_from_design` autofill を採用する。Canva公式資料: https://www.canva.dev/docs/apps/rest-apis/autofill-guide/

**要事前設定**
- Canva Developer Portalでアプリ作成、ユーザーが認証・承認するOAuth 2.0とPKCEを構成。
- 対象プランのAutofill機能利用可否をCanva側で確認。
- Canvaの**元デザインの作業用コピー**に、`COVER_TITLE`、`COVER_DATE`、`EVENT_01_TITLE`…`EVENT_10_SOURCE` 等のラベルを付与。元テンプレートは編集しない。
- `get_design_dataset` で全ラベルが存在すること、型がtextであることを検証した後に `POST /rest/v1/autofills` を `create_from_design` 指定で実行。ジョブの成功を確認後、新規デザインのURLをサイトへ返す。
- OAuthトークン、Client Secret、refresh tokenはGitHub Pages上の公開JSやリポジトリへ置かず、独立した認証サーバー/secret managerにのみ保存。
- Canvaへの呼び出しはサーバーで行い、利用者認証、origin制御、CSRF、リプレイ防止、レート制限を要する。
- エラー時は既存テンプレートと公開イベントデータを維持し、「ドラフト作成失敗」と明示する。

**画像について**: イベントの `image` URLは著作権上の転載許可を意味しない。現在のJSONでは `image_reference_url` に参照情報として残し、autofill画像フィールドへ渡さない。許諾済み画像だけ、別途Canva Asset APIへ安全にアップロードした asset_id を紐づける。

## ステージングと本番への安全配慮

- `main`/staging のアプリ変更として扱い、`production` へ自動昇格しない。
- `site/data/` のイベントJSON、`data-staging`、`data-production`、`policy/approved_event_removals.json` は**一切変更しない**。
- 公開前に `node --test tests/canva_draft_contract.test.mjs` と既存 `npm test`、環境差分監査、ステージングでの操作確認を実施。
- 本番公開はユーザー承認後のみ。詳細: `AGENTS.md`、`docs/RELEASE_PROCESS.md`、`docs/ENVIRONMENT_DIFF_POLICY.md`。
- 新ファイルと `site/search.html` の差分は新規アプリ改修（**pending_release**）として扱う。未承認の `intentional_staging_only` 例外へ勝手に分類しない。

## 差し込みデータスキーマ

`autofill_fields` は `COVER_TITLE`、`COVER_DATE` と、選択番号 NN=01～10 に対して下記の5つを持つ。

- `EVENT_NN_TITLE` – 公式タイトル（無断短縮しない）
- `EVENT_NN_DATE` – 掲載期間と時間
- `EVENT_NN_VENUE` – 会場と区
- `EVENT_NN_DESCRIPTION` – 掲載説明と料金
- `EVENT_NN_SOURCE` – 公式URL

個票には `id`、`verification_status`、`verification_source`、`image_reference_url` を保持してトレースする。10件未満なら古いテンプレート内容が残るのを防ぐため、手動仕上げが必要。独立したCanvas画像を生成したり勝手に架空のイベントで埋めたりはしない。
