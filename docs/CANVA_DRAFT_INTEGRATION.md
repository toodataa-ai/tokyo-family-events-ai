# Canva投稿ドラフト連携 — staging implementation (2026-10-22)

## 2026-10-24: 最大30イベント／最大17ページへの拡張（今回改修・承認待ち）
- 検索選択、順序入替、ブラウザ内選択保持、共有リンク、プロンプト、JSON、CSVは最大30件。選択順を保持。
- 10件以下は承認済み7ページのまま。11〜30件はGolden Masterの新規作業用コピーに紹介ページを必要数だけ追加する。30件＝表紙1・紹介15（1ページ2件）・締め1＝17ページ。Instagramの1投稿20枚上限以内。
- 旧Golden Masterを変更せず、追加ページは紹介ページ2〜6の同じ見た目をコピーし、元のイベント要素を全て置換。締めは最終ページに移動。偶数でない件数は最終下段を完全非表示。
- ステージング候補であり、production・data-production、Canva原本/旧コピーは変更しない。Canva内での17ページ現物制作・配置・保存は別途実依頼時に検証が必要。


## 2026-10-23：ユーザー確定版のレイアウト再現（本番公開前のステージング候補）

- **今後の制作基準**は保存済みCanva `DAHY1F7Rv_k`（[完成版](https://www.canva.com/d/Yr0CiLUWgATkd1R)）。元版 `DAHYo7noxKY` と以前の保存済みデザインは変更しない。最新完成版から毎回別IDのコピーを作り、イベントの画像・日時・文章・出典だけ差し替える。
- レイアウト正本は `docs/canva_golden_layout_contract_v1.md`。表紙の「東京23区」「N選」「日付」「週末 子連れイベント」を**固定座標・固定書式**にし、紹介文に合わせて拡大しない。日時は通常54px、3行52px、本文は50〜54px優先。写真フレームなどはGolden Masterから継承。
- 新しい `site/canva.html` は表紙の投稿対象週末を入力可能。日付が未指定の場合は「未指定・要確認」を指示に残し、古い10/24〜25を流用しない。サイト指示テンプレートとミラーは同一バイト保持。
- 重大NG防止：旧イベント名/画像残存、表紙「区」「選」や締め文の枠はみ出し、一時プレビューを保存成功と誤認することを禁止。全7ページ実画像チェック→commit→`get_design`/`get_design_content`/`get_design_pages`再読込の順。
- Canva連携でフォントファミリーの取得・変更ができない場合は同一書体を断定しない。ChatGPTへ送るプロンプトは**再現指示**であって、画像の転載許可やCanvaのピクセル完全自動保証ではない。
- **リリース境界**：現時点では開発ブランチでのUI/プロンプト変更。productionとdata-productionには反映しない。既存データを変更しない。main/stagingへの導入にも検証が必要、productionには別途明示承認が必要。

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

## 2026-10-22 非公開ドラフト用の公式サムネイル候補と文字拡大

- `image_reference_url` は参照情報。公式イベント固有のURLと判別できる場合に `event_image_candidate` を付与。Canva下書きに取り込む候補とし、権利を取得済みだとは主張しない。
- 共通OGP、汎用SNSロゴ、複数イベントで重複する画像、ドメインが異なる参照画像は区別する。`generic_site_image`、`shared_or_duplicate`、`external_image_requires_review` は自動転用しない。
- イベントの実在・画像との一致・文字が読める構図を確認して非公開の作業用コピーだけに配置。掲載・SNS投稿・配布は別途許諾が確認できた画像だけに限定する。
- 初期サイズは一行80〜82px、二行70〜74px。必ず文字の実際のbounding boxを比較し、見出し・会場・日時・写真の重なりを解消する。以前の文書の72px/64〜68pxは旧値。
- 10件未満なら空き枠は枠ごと隠し、古いイベント本文・写真を残さない。表紙の『N選』は選択件数と一致させる。
- 画像判定はブラウザ側の**候補ラベル**にすぎず、WebサイトのURLをもとにCanvaへ直接アップロードするOAuth/Connect APIは未実装。Canva連携で送る指示文を使い、ChatGPT側で画像と権利を確認してからドラフトへ反映する。
- この更新はステージングのアプリ差分だけ。既存データ、`production`、`data-production`のレコード削除・変更は一切しない。

### 今回のCanva保存済み検証例

- 元テンプレート `DAHYo7noxKY` と前回確定版 `DAHYr_sNh7I` を変更せず、修正版コピー `DAHYt_NTgxA` に8件の文字拡大を保存。
- イベント専用の告知画像を特定できたもののみ2件配置（「東京自然いきもの展」「秋のキッズフェスタ2026」）。その他6件は汎用OGP・著作権未確認・別年画像のため「画像準備中」を維持。
- SNS投稿と本番サイト公開は未実施。

## 2026-10-23: 投稿クオリティ安定化（ステージング候補）

- 元Canvaテンプレートは `DAHYo7noxKY` のまま。新規テンプレート採用・元ファイル変更・Canva保存版の自動更新は行わない。
- 参考Instagram `https://www.instagram.com/p/Dev8XdMHRvr/` の画像自体は取得できなかったため、デザインの具体的特徴を想像でコピーしない。実際に取得できた場合にのみ視覚比較する。
- `docs/canva_visual_quality_contract_v1.md` を品質判定の正本として追加。元テンプレートの実測値（本文枠約540px、上段下段）を手がかりに、ロール別フォント・本文の大きさ・画像・出典・プレビュー・G01〜G08のゲートを明文化。
- `site/canva-prompt-template-v2.txt` をサイトの実際のコピー指示正本として更新し、`docs/canva_prompt_template_v2.txt` は同一バイト保持。サイトのテンプレートURLのクエリを更新しキャッシュ汚染を回避。
- Canva接続の `format_text` では書体ファミリーを直接指定できない。確認不可能なら「フォント種類未検証」と報告し、合格済みと偽らない。編集可能な文字を画像化しない。
- この改修で新しいCanvaデザインを自動保存したわけではない。ユーザー承認まではステージング側のプロンプト改善のみ。productionとdata-productionは別管理。
