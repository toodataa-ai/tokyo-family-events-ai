# 定期更新手順書（休日明けの更新・追加公開）

最終更新: 2026-11-18（Claude）。**利用者のフィードバックは、受けたその場でこの手順書の「フィードバック台帳」と該当手順に反映する。** 反映していない指摘は未対応とみなす。

## 1. 定期実行の流れ（毎回）
1. `AGENTS.md`・本書・直近の `docs/CLAUDE_HANDOVER_*.md` を読み、`data-production` / `data-staging` の先頭SHAが一致していることを確認する。
2. 公式ページ取得は **読み取り専用ワークフロー**（`fetch-*.yml` を main に push → `research/*` ブランチへ生の取得結果をコミット）で行う。シェルから直接取れない。失敗(404/403)は `error` のまま、成功扱いにしない。
3. 候補を仕分ける: 既公開(同一公式URL/名称)・対象外(居住者限定/申込終了/成人向け/管理告知)・掲載可。掲載可は **公式本文の引用(12文字以上、連続一致)** を根拠にする。
4. 追加は **新しい固定(pin)の追加専用オペレーション** で公開: 生成ツール `tools/<name>_addition_*.py` と検証 `tools/validate_<name>_*.py`（生成物を再導出し完全一致を要求）。既存データの削除・変更は禁止。
5. 配線: `deploy.yml` に3か所（検証・preview・promote）、`.github/staging-production-diff-baseline.json` に新規main専用ファイルを分類、`tools/audit_environment_diff.py --strict` で unclassified=0。
6. ローカルで共通ゲートを全て通す（validate_data / decisions / rereview / non_regression / protected_events / family_fit_quality / audit_event_image_identity）。`indoor_outdoor` は 屋内/屋外/屋内・屋外 のみ。
7. 候補を data-staging に push → `.github/data-deploy-trigger.txt` のみを変更するコミットを main に push → gate/validate_data/promote_data/preview/snapshot の成功を確認。
8. 公開後確認: data-production の manifest 件数、`data-release/*` スナップショット、Pages デプロイ。
9. 利用者への報告は日本語。登録件数・除外理由・残課題（ためまっぷ403等、25ソース全照合の未完）を必ず書く。

## 2. 禁止事項
主催者への問い合わせ禁止。失敗URLの成功への書き換え禁止。既存イベントの物理削除禁止。本番アプリ(production)の変更は承認なしに行わない。

## 3. フィードバック台帳（利用者の指摘 → 反映先）
| 日付 | 指摘 | 反映した手順 |
|---|---|---|
| 2026-11-18 | 「やれば実施可能」な保留分（練馬404再確認・821件の仕分け・祝日候補・年次行事）を省略せず実施する | 1-3の仕分けを毎回実施し、結果を `research/<date>-leads-triage/` に記録 |
| 2026-11-18 | 3件も残りも進める／定期実行を登録する | 追加公開(4-8)まで止めずに完遂。定期タスクを登録 |
| 2026-11-18 | フィードバックは常に手順書に反映する | 本表に追記し、該当手順を同じコミットで更新（このルール自体が第一行） |
| 運用上 | 承認・報告はチャットで／日本語／失敗通知は不要で会話開始時に状況確認 | 9、および会話開始時に前回の未完・失敗を報告 |

## 4. 既知の未完（毎回再確認）
- ためまっぷ 403（3 URL）は取得不能。依存する保留分（工作・花教室系2件、12/19 森のファミリー合唱団の矛盾）は据え置き。
- 全23区×25ソースの完全照合は未完。`global_source_audit_complete` は常に false。
- 11/23祝日候補は全30件仕分け済み（公開済み/対象外/追加済み）。
