# AGENTS.md — 東京子連れイベントサイトの安全運用

このリポジトリを扱うAI / 開発者は、**変更・本番公開・差分確認を始める前に**下記を必ず読む。

1. .github/skills/staging-production-diff/SKILL.md
2. docs/RELEASE_PROCESS.md
3. docs/ENVIRONMENT_DIFF_POLICY.md
4. .github/staging-production-diff-baseline.json（意図した差分の機械可読台帳）

## 環境と正本
- main = 開発・ステージングとGitHub Pages公開オーケストレータ。
- production = 承認後にリリースする本番アプリ・静的設定。
- data-staging = 動的イベントデータのリリース候補。
- data-production = 本番で公開される動的イベントデータの正本。
- release/* と data-release/* は成功した公開版だけの不変スナップショット。
- 本番のPagesは **productionのsite + data-productionの動的データ + mainの公開台帳** を合成する。

## 必須ルール
- 「mainとproductionのcommit履歴が違う」だけで未リリースと判断しない。追跡ファイルのblob SHAを比較する。
- 台帳に記載された差分だけが意図したステージング専用差分。未知の差分を勝手に正常扱いしない。
- mainをproductionへ丸ごと同期しない。ユーザーが明示承認したファイルだけをproductionベースのリリース候補に移植し、検証する。
- イベントレコードを無承認で削除しない。動的データ更新とアプリリリースは別ゲート。
- 単なるデータ更新で未承認のUIやルールを公開しない。
- 不明な差分は「要調査」と表示し、残してよい根拠のないものは公開しない。
- 初回の現状確認には python3 tools/audit_environment_diff.py --fetch --json を利用し、正常差分のみという結論には --strict 合格を要する。
- 新しいintentional staging-only差分は、理由と種類を記録し、台帳を更新。更新しないと将来のチェックでunclassifiedになる。
- 正常公開後は固定のレコード数やSHAを未来にも当てはめない。最新の実データを再取得し台帳を見直す。

## 2026-10-17 v1.10の参照断面
- 本番アプリ commit: f031d9ba357c31528307712479c559785d1734a3
- 本番動的データ commit: b1282eb0f24ec6436b1ef8cf52d3df597b262c0b（当時361延べ件）
- 当時、mainとproductionの実ファイル差分26件、site/とprompts/は差分なし。
- この方針自身をmainに追加するとその分だけ差分が増える。今後は実比較と台帳で判断する。

## 公開完了の定義
production PRがmergedでも完了ではない。mainのGitHub Actionsの本番Pagesデプロイ成功、本番枝の正本確認、data-productionの件数/ID確認、releaseスナップショット・正式版台帳の一致まで検証する。作業が途中なら「未完了」と明記する。

## 手動変更の確認運用（2026-11-15 ユーザー指定）

「ステージングのURLを私が確認した後に、本番へ反映」。手動のUI改修、今回の追加候補・評価訂正は、実表示できるステージングURLと差分を提示し、ユーザーの確認・明示承認を得てから本番へ反映する。調査依頼・継続依頼・CI合格は本番承認の代用にしない。未承認時はproduction、data-production、公開トリガー、不変release台帳を進めない。既存の休日明け定例自動更新は別経路であり、この手動変更を自動更新へ混ぜて承認を省略しない。
