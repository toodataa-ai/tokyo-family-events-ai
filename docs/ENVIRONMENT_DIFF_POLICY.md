# 環境差分台帳・判定基準

監査日: **2026-10-17**。リリース基準: **アプリv1.10（release/2026-10-17-r4）**。
**この文書は現時点の断面であり、将来の差分を自動承認するものではない。**

## 結論（2026-10-17）

production=f031d9ba357c31528307712479c559785d1734a3、main=624fc0dc6528bdc8d746efe989528d24ff17064f（統制ファイル追加前）。GitHub treeの**実blob**で比較すると差分は26ファイル。**site/ と prompts/ には差分なし**。本番アプリの反映漏れは見当たらず、残差分はステージング側に必要な統制・監査・証跡と分類した。

本番の動的データは別管理。data-production=b1282eb0f24ec6436b1ef8cf52d3df597b262c0b、当時の掲載レコード361件。data-stagingも同SHAであった。今後の更新後は必ず取り直す。

## 既存26件の内訳

| 区分 | 件数 | 詳細・残す理由 |
|---|---:|---|
| 公開トリガー / 台帳 | 3 | .github/release-trigger.txt、data-deploy-trigger.txt、production-releases.json。mainが公開の正本、productionは過去値のため同期しない |
| Pagesオーケストレータ | 1 | .github/workflows/deploy.yml。mainの安全ゲートとPages公開を維持 |
| 調査 / リリース監査ワークフロー | 10 | .github/workflows/audit-*.yml、holiday-readonly-audit、nerima-annual-live-smoke、probe-suginami、recheck-67。過去時点の監査証跡なのでproductionへ不要 |
| データ運用ドキュメント | 1 | docs/holiday_after_update.md。履歴更新のmain側の運用改善 |
| テスト定義 | 1 | package.json。main側で休日明け履歴テストを追加しているため |
| 調査証跡 | 4 | research/2026-10-13-*.json。実測や検証記録でproductionへの配信は不要 |
| ステージング専用テスト | 2 | tests/holiday_update_history.test.mjs、tests/non_regression_policy.test.mjs（後者は内容差分） |
| 内部監査ツール | 4 | tools/holiday_readonly_crawl.py、holiday_update_history.mjs、probe_suginami.py、recheck_67_mismatches.py |
| **合計** | **26** | すべてファイル単位の理由をJSON台帳に記録 |

このガバナンス追加により AGENTS.md、Skills、差分台帳、監査コード/テスト、この文書、RELEASE_PROCESS.md の合計 **7件** のmain側差分が増え、想定は **33件**。追加後は実際の比較結果で再検証する。

### 注意が必要な点

- 調査ワークフローには古い公開SHAや件数を検証条件に含むものがある。**今日のデータ更新の正本として再利用しない**。過去監査としてmainに保管する。
- site/が同一であっても、公開データやGitHub Pages配信が正常とは限らない。これらは独立に監査する。
- JSON台帳は現行の差分を「正当な理由で保留」と認定するもの。将来、新しいファイルや差異が発生したときの自動承認権ではない。
- research/ や調査ツールの存在は未完成機能を本番へ昇格する理由にならない。必要性を個別判断する。

## チェック方法

    python3 tools/audit_environment_diff.py --fetch --ref HEAD --base origin/production --json
    python3 tools/audit_environment_diff.py --fetch --ref HEAD --base origin/production --strict
    python3 -m unittest discover -s tests -p 'test_environment_diff_policy.py'

- 通常のmain→staging CIでは、**新しい差分を報告するだけ**。開発中の未承認変更が存在するだけではプレビューをブロックしない。
- 正常差分のみと報告・本番リリース準備するときは --strict に合格するか、新規差分を pending_release として明示し承認対象を切り出す。
- unclassified = 理由未記録。wrong_kind = 登録と差分形態が不一致。resolved_allowlist = 旧例外が解消し台帳が古い。release_baseline_moved = 正式版のSHAが変わった。**いずれも再審査が必要**。
- 本番リリース直前はmain全体ではなくproductionベースの隔離リリース候補を作成し、承認対象ファイルだけをレビューする。すべての差分を許可するワイルドカードを設けない。

## 変更後に守るチェックポイント

1. productionのHEADと最新の正式リリース台帳/不変スナップショットが一致する。
2. Pagesの本番デプロイが成功しており、操作した環境が何か正しく判別できる。
3. main/productionのtree比較と台帳の差異を記録する。差分0件も、差分N件も、実ファイルを確認する。
4. site/とprompts/の差分があれば未承認の保留なのか、次回のリリース対象なのかを分ける。
5. data-stagingとdata-productionは別に比較。前回の各週全イベントIDが維持されていることを無承認削除監査で確認。
6. 正式版の更新時、台帳のbaseline SHA・リリース名・例外一覧の見直しをする。

**運用正本:** AGENTS.md、.github/skills/staging-production-diff/SKILL.md、.github/staging-production-diff-baseline.json、docs/RELEASE_PROCESS.md。
