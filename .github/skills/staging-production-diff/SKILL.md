---
name: staging-production-diff
description: Classify main/staging versus production application differences, preserve published event data, and promote only explicitly approved changes.
---

# ステージング ↔ 本番 差分統制スキル

## 発動条件
- 「ステージングと本番は同期しているか」「残差分は何か」「本番リリース」「デグレ・データ削除がないか」「差分は意図したものか」の依頼時に読む。
- 正本: AGENTS.md、docs/RELEASE_PROCESS.md、docs/ENVIRONMENT_DIFF_POLICY.md、.github/staging-production-diff-baseline.json、tools/audit_environment_diff.py。
- これはGitHubリポジトリ内の永続運用手順。過去のチャット記憶より現在のブランチ・台帳・CIを優先する。

## まず現物から確認
1. GitHubで main、production、data-staging、data-production のHEAD、正式版台帳、実デプロイのGitHub Actions成功結果を読む。
2. main と production の追跡ファイルのblob SHAを再帰比較。コミット履歴の差だけで「未リリース」と判断しない。
3. 以下のコマンドで現状分類。正しい差分だけと断定する前は --strict の合格を必須とする。
    python3 tools/audit_environment_diff.py --fetch --ref HEAD --base origin/production --json
    python3 tools/audit_environment_diff.py --fetch --ref HEAD --base origin/production --strict
4. site/ または prompts/ の差分はアプリ未リリース候補として個別判断。main-onlyの例外登録がない限り「意図した差分」ではない。これらが同一でもデータ枝の同期を意味しない。
5. 動的データは独立正本 data-production。data-staging と data-production の各週イベントID・個票・件数・履歴について無承認削除を別途監査。

## v1.10（2026-10-17）監査断面
- production = f031d9ba357c31528307712479c559785d1734a3、正式版 release/2026-10-17-r4。
- data-production = b1282eb0f24ec6436b1ef8cf52d3df597b262c0b、6週間361延べレコード。この数値は以後のデータ公開時に更新される。
- 監査時点のmain = 624fc0dc6528bdc8d746efe989528d24ff17064f。
- 実ファイル差分26件。site/ と prompts/ は同一、本番反映漏れアプリ変更0件。公開トリガー/台帳・mainの検証Actions・調査証跡・開発ツール/テスト。個々の差分はJSON台帳に記録。
- この統制ファイルをmainへ追加すると管理専用の差分が増える。増分も台帳登録。件数だけを同一性の証拠としない。

## 継続運用ルール
- mainはステージング、productionは本番アプリ、data-productionは本番動的データ。4枝を一括同期しない。
- intentional_staging_only（台帳登録済み） / pending_release / unclassified / already_released / resolved を区別する。現在のJSON台帳に列挙されたものだけが例外承認済み。
- main-onlyの新規ファイルを例外承認するなら、用途、運用環境、継続要否、根拠を1ファイルずつ記録する。無条件のワイルドカード例外は禁止。
- ステージングCIは差分を報告する。開発中の未リリース機能が存在するだけではプレビュー公開を止めない。ただしそれを承認済みとは解釈しない。
- 本番公開時はユーザーが承認した変更だけを現在のproductionから派生した候補に限定移植する。main全体の無条件昇格は禁止。
- 本番アプリへの反映にはユーザー明示承認、候補差分監査、CI成功、production PR、Pages成功、release/*不変snapshot、production-releases.json登録を要する。
- data-staging → data-production は別経路。既存イベントの無承認削除・個票変更・履歴消失はtools/validate_protected_events.py等で拒否する。
- 本番公開が済んだらブランチ間の実ファイルを再比較し、台帳のresolved項目を整理し、本番SHA、正式版、意図した新差分の説明を更新する。
- 「同期済み」は範囲を限定して表現し、site/の一致とブランチ管理ファイルの不一致やイベントデータ枝の状態を混同しない。

## コマンド
    python3 tools/audit_environment_diff.py --fetch --ref HEAD --base origin/production --json
    python3 tools/audit_environment_diff.py --fetch --ref HEAD --base origin/production --strict
    python3 -m unittest discover -s tests -p 'test_environment_diff_policy.py'

unclassified、wrong_kind、resolved_allowlist、release_baseline_movedのいずれかが1件でもあるときは全差分が「あるべき差分」と断言しない。本スキルは本番デプロイの許可そのものではない。
