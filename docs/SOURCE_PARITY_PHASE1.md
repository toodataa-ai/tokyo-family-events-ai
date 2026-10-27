# 掲載漏れ防止・第一弾（2026-10-27）

対象は練馬区「地区祭開催日程」と杉並区公式イベントカレンダー（全ジャンル）。
公式サイトがHTTP 200だっただけでは、全件確認済みとしない。

## 方針
- 既存抽出器を温存。練馬区は tools/official_schedule_discovery.py、
  杉並区は tools/suginami_full_calendar_evidence.py を再利用する。
- 練馬区の地区祭は公式ID・該当日・会場・公式URLで、杉並区はイベント固有の
  公式詳細URLと日付で、公開イベントと照合する。
- 対象となる土日・独立祝日（直前週のshard）を確認し、現行data-productionの
  掲載イベントと同一週の採否台帳を両方照合する。
- 判定: published / excluded / duplicate / unreviewed / inconsistent /
  ambiguous / needs_date_review。取得不能時はsource_error、候補件数はnull。
- 採否の除外・重複には理由と公式根拠が必要。対象日の候補について
  date_mismatch で除外していた場合は不整合として報告する。
- 杉並区は対象日の全ページ、全月別一覧、候補の全公式詳細を取得。
  1ページでも失敗したら0件とは扱わず取得障害として保持。
  月別で発見したが日付不明のイベントは needs_date_review。
- データは完全読取専用。既存イベント・採否原本・検索・Canva・星・画像・表示カード・
  公開本番アプリを変えない。抽出したというだけで追加・削除しない。

## 運用とゲート
- 共通検証: tools/source_coverage_reconcile.py
- 公式証拠アダプター: tools/audit_phase1_source_coverage.py
- 回帰: tests/test_source_coverage_reconcile.py （既存 npm test に追加）
- GitHub Actions: Phase 1 official candidate-to-publication parity (read-only)
- PRではネットワーク不要の決定的テスト。Actions手動実行（workflow_dispatch）時だけ
  公式現況を取得し、本番6週間に対する候補別結果をJSONとJob Summaryに出力する。
- 未照合・取得不能は strict モードで失敗として表示する。
  ただし既存サイトの未確認候補を理由に、証拠のある他イベントの安全なデータ公開まで
  一括停止しない。データ公開は引き続き既存のデータ用厳格ゲートに従う。

本フェーズは監査の追加であって、新規候補を自動採用するものではない。
