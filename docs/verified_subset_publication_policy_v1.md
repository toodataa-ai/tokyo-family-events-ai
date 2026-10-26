# 検証済みイベントの部分公開方針 v1（2026-10-26）

## 目的・承認
ユーザー指示（2026-10-26）：「1（取得できない必須サイト）は課題として残してよい。2（候補を個別確認）、3（検証と公開）を進め、検証を通って公開できるサイトだけでも少しでも多く公開する」。
全参照元の復旧・889候補リンクすべての採否確定を、**独立して公式確認できたイベントの公開の一律前提にしない**。ただし公開対象についての検証と既存掲載保護は絶対に省略しない。

## 運用上のルール
1. **サイト単位の取得状態とイベント単位の掲載状態を分離。** サイト状態は `checked` / `failed` / `deferred_with_evidence`、候補は `unreviewed` / `verified_and_publishable` / `excluded_with_reason` / `duplicate_of` / `blocked_pending_evidence` を区別。エラーを `checked` に偽装しない。
2. **掲載単位は公式根拠を確認できる個々の参加企画。** 日付（祝日を含む）・会場・対象年齢・料金・予約要否・サムネイルのイベント一致を監査し、不明なものは不明と明記。会場やURLが共通でも、上映・体験・講座等の独立参加単位は機械的に重複扱いしない。
3. **掲載可能なものは小さなバッチで順次公開。** 先行バッチの厳格なテストと公開の完了を待って次のバッチを作る。取得失敗サイトは未確認として再試行し、既存掲載イベントは取得失敗だけでは削除しない。イベントの公開可否に無関係なサイト失敗が他のイベントを道連れにしないよう、検証ゲートの改善を検討する。
4. **従来の保護ルールは不変。** 新規レコードの出典/日時/会場/重複/family-fit/画像/通知/祝日を検証。既存IDと重要フィールドは非退行、過去ファイル保持。データ更新とアプリ改修、ステージングと本番を分離。アプリコードと公開Versionをデータ公開のついでに改変しない。
5. **証跡と数字を偽らない。** 取得失敗は失敗、未検証リンクは未検証。23区すべての探索状況を示し、掲載候補の個別採否理由と公式ページを保存する。旧ログで当日の検索成功を代替しない。公開履歴、Git SHA、Actions、Pages、公開件数を突合する。
6. **現行CIに適合しない場合はフェイルクローズ。** この運用方針は検証スクリプトの強制チェックを無効化する承認ではない。部分公開を阻害する「全必須URL一律成功」や「11/03だけの歴史ギャップ例外」などは、安全性を維持する限定的な新しいdata-only運用モードと回帰テストをステージングで実装・検証し、必要な承認と公開手続きを別に経るまで本番に適用しない。未検証データを直接 `data-production` へ書かない。

## 現時点の障害・案件（2026-10-26）
- 調査証跡: https://github.com/toodataa-ai/tokyo-family-events-ai/actions/runs/40239302863 （attempt 2、artifact `12621285469`）。
- 663リクエスト中658成功、未検証候補889リンク。取得失敗: `tamemap_nakano` 403×3、`itabashi_tourism_festival` 503×1、`iterrace` timeout×1。
- 最新の `data-production` / `data-staging` 基準SHA: `605f7144b99944201663055105e076e3b1237ebd`。両方のSHAを同一更新の都度再確認する。
- 先行バッチ候補: 11/23 子ども未来館3企画（https://www.city.edogawa.tokyo.jp/event/2611puranaria.html , https://www.city.edogawa.tokyo.jp/event/2611keyholder.html , https://www.city.edogawa.tokyo.jp/event/2611kosaku.html）、くまのこDAY（https://www.city.toshima.lg.jp/129/bunka/bunka/shiryokan/2602150927.html）。11/23をmanifestの公式祝日に登録する必要あり。
- 新しい12/05週候補: 12/05第一地区祭（豊玉小学校） https://www.city.nerima.tokyo.jp/kankomoyoshi/annai/omatsuri/chikusai/20260616103208700.html 、中野×杉並×豊島アニメ・マンガフェス https://www.city.tokyo-nakano.lg.jp/kanko/city-promotion/animemangafest2026.html 。個別参加単位の切り分けと公式日時・会場の確認が必要。

## リリースの最低限の手順
1. 最新の公式取得ログ・前回公開記録・immutable `data-production` SHAを固定し、独立した確認済みイベントだけに採否とverificationを付与する。
2. `data-staging` に対象データのみで候補を作成し、historyに追加件数・保留件数・非退行・変更ファイルと証拠を記録する。
3. `validate_data --strict`、`validate_decisions --strict`、`validate_rereview --strict`、公式スケジュール/祝日監査、画像同一性、`validate_non_regression`、`validate_protected_events`、`npm test` および限定的な例外条件の回帰テストを全PASS。
4. 基準SHA不変を再確認し、正規のdata-only GitHub Actionsで昇格。Actions成功に加えPages実体、履歴、公開件数、snapshotと戻し手順を照合する。
5. エラーサイトや未確認候補はIssueに継続記録し、公開済みイベントがあることをもって未確認を「0件」「確認済み」と表示しない。

追跡: https://github.com/toodataa-ai/tokyo-family-events-ai/issues/41
