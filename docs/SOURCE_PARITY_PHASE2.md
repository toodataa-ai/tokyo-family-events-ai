# 第二弾：一覧・記事・ページ送り型の掲載漏れ監査

対象：`nakano_official_tourism`、`itabashi_times_event`、`nerimakanko`。
既存 `site/data/discovery_sources.json` の保護対象・サイト定義は一切変更しない。

## 新機能

1. 一覧ページを巡回し、実際に書かれた次ページのリンクだけを有限個たどる。板橋は /category/event と /page/2 の**両方**を必ず検査。練馬は6週間にまたがる**各月の月別検索**も取得する。
2. HTMLのイベント記事リンクからURLベースの安定候補IDを生成。タイトル・元一覧URL・記事URL・日付ヒント・記事取得成功可否を記録し、同じ記事が複数月や複数ページに載っても重複候補を作らない。
3. 板橋TIMESの「今週・今月のまとめ記事」は `collection_index` として管理し、本文から個別記事URLを `roundup_child_lead` に展開。親フェスと小企画を機械的に別々のカードへ掲載しない。
4. 日付の読み取りが曖昧な記事は `needs_date_review`、採否根拠がない記事は `unreviewed_candidate`。実際の本番掲載イベントと同じ記事URLを使っていても、主催者公式と採否が未確認なら `existing_link_needs_proof`。既存決定台帳と主催者出典まで確認できたものだけ `existing_publication`。
5. 一覧・ページ送り・個別記事の取得失敗／HTML変更／設定ページ上限超えは `source_error`。**0件の成功扱い禁止**。日付の確証や一次ソースがなければ自動公開しない。
6. 完全読取専用。旧イベント、回顧、画像、採否、公開アプリ、Canva、検索、A/B/C評価を変えない。サイトごとに取れた分は監査結果に残し、他サイトのエラーで安全な別件データ更新を妨げない。

## 検証方法

```bash
python3 -m unittest discover -s tests -p 'test_listing_source_evidence_v2.py'
# 本番データへの読取専用監査:
python3 tools/listing_source_evidence_v2.py --published-dir site/data --source all --output /tmp/phase2-discovery.json
python3 tools/audit_phase2_listing_parity.py --published-dir site/data --input /tmp/phase2-discovery.json --output /tmp/phase2-parity.json --strict
```

GitHub Actions「Phase 2 paginated listing and article-to-publication audit (read-only)」が PR 時にオフライン回帰、main 更新／手動時に現実のページを読取専用で収集・監査し、日本語 Summary と保存済み JSON を出力する。既存ステージングの `npm test` に同テストを追加。

## 運用上の限界・次の判断

- 一覧のページ数は上限付き。古い記事にも将来の開催日がある可能性があるため、クロール済みページが全サイトの完全網羅であるとは言わない。
- 板橋TIMES等は二次媒体。記事発見≠開催確定。区や主催者の一次ページを別に読んでから採否を決める。
- 単なるページタイトルの日付はヒントであって検証済み開催日ではない。まとめ記事内の個別イベントも別の一次情報を要する。
- 監査で発見した未検証候補は勝手に本番掲載しない。公式確認済みの新規イベントだけを、既存の非破壊データ更新ゲートに従い別途追加する。
- 現在の「候補」と「日付行」の件数を混同しない。取得不完全な場合は候補件数を掲載漏れ確定数として報告しない。

第一弾の地区祭・杉並全日カレンダーの掲載監査、森こどもフェスタ監査は変更しない。
