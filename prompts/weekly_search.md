# 東京23区 子連れイベント AI探索・週次更新プロンプト v1.2

対象週末の東京23区について、子連れで参加できそうなイベントを網羅的に探索し、新サイト用JSONを作成する。

## 最重要ルール

1. 23区を必ず1区ずつ処理する。まとめ検索だけで完了扱いにしない。
2. 各区の探索が終わるまで `coverage.wards[].status` を `checked` にしない。
3. 「子ども向け」と明記されたイベントだけに限定しない。祭り、鉄道、動物、科学、防災、消防、スポーツ、フード、商店街、スタンプラリー等も子連れ可能性を評価する。
4. 開催日・開催場所・年齢制限・予約要否を確認する。
5. 公式URLが見つかる場合は必ず `official_url` に入れる。媒体記事だけで確定しない。
6. 同一イベントの複数掲載は1件に統合する。
7. 推測で料金・時間・会場を埋めない。不明はnull/空欄とする。
8. コピペ互換フィールド `name, ward, period, time, venue, price, description, official_url, url, source, image` を壊さない。
9. 掲載判断に迷うイベントは落とすのではなく、子連れ適性Cとして注意点を `family_fit.reason` に書けるか検討する。
10. 全23区の探索が完了していなければ本番データとして提出しない。
11. サムネイル画像を必ず探索する。`image` を安易に `null` にしない。
12. 掲載候補確定後、全イベントを公式・主催者情報で再監査し、verification監査ファイルを作成する。
13. verificationが全件 `verified` でなければ本番公開しない。

## 区ごとの探索手順

各区について以下を順に確認する。

### A. 公式系
- 区公式イベントカレンダー
- 区観光協会
- 区の子育て/文化/公園ページ
- 区立文化施設、図書館、児童館等

### B. 東京都・都立施設
- 東京都公式イベント
- こども向け都施策
- 都立公園
- 博物館、美術館、科学館、動物園等

### C. 子育て・イベント媒体
- 子ども/親子向けイベント媒体
- 地域イベント媒体

### D. 施設・企業公式
- 商業施設
- 鉄道・交通
- スポーツ施設/クラブ
- 劇場・ホール
- 大学/専門施設

### E. Web横断検索
最低限、区名と対象日を入れ、以下の語を組み合わせて検索する。
- 子供 / 子ども / 親子
- イベント
- 祭り / お祭り / フェス
- ワークショップ / 体験
- 無料
- スタンプラリー
- 鉄道 / 電車
- 動物
- 科学
- 防災 / 消防

## サムネイル画像取得

イベント採用後、各イベントについてサムネイル画像を探索する。

優先順位:
1. 公式ページの `og:image`
2. 公式ページの `twitter:image`
3. 公式ページの `itemprop=image` / `image_src`
4. 情報元ページの `og:image` / `twitter:image`
5. JSON-LD等に明示されたイベント画像
6. 公式・情報元ページ本文のイベント画像

ルール:
- ロゴや汎用サイト画像よりイベント固有画像を優先する。
- 推測した画像URLは作らない。
- `data:` URLは使わない。
- `image` は `http://` または `https://` の実URLのみ。
- 画像が本当に見つからない場合のみ `null` とする。
- 公開処理でも `tools/enrich_images.py` を実行して補完する。
- 公開時のサムネイル取得率が70%未満ならデプロイしない。

## 公式情報の再監査（必須）

探索・重複排除・掲載判断が終わった後、掲載イベントを1件ずつ再度確認する。探索時に使った媒体記事だけで監査完了にしない。

優先する検証ソース:
1. 自治体・東京都・公的施設の公式ページ
2. イベント主催者・会場・施設の公式ページ
3. 公式観光協会
4. 主催者から提供された情報を明記する提携媒体

各イベントについて最低限、次を照合する。
- イベント名
- 開催日・開催期間
- 開催時間
- 会場
- 料金
- 予約要否・申込期限
- 対象年齢・参加条件
- 中止・延期・雨天条件
- 公式URL

### 判定ルール

各フィールドを以下で記録する。
- `pass`: 元データと公式情報が一致
- `corrected`: 公式情報に合わせて補正が必要
- `unknown`: 公式情報に明記がなく確認不能。推測しない
- `not_applicable`: 項目自体が該当しない

`name`・`date`・`venue` は公開時に必ず `pass` または `corrected` でなければならない。
料金や時間が公式ページに明記されていなければ `unknown` のまま許容し、推測値を作らない。

### verification監査ファイル

週データに次を追加する。

```json
"verification_file": "2026-10-10-verification.json"
```

監査ファイル例:

```json
{
  "schema_version": 1,
  "verified_on": "2026-10-06",
  "summary": {"total": 37, "verified": 37, "unverified": 0},
  "events": [
    {
      "id": "2026-10-10-nakano-example",
      "status": "verified",
      "source": "https://公式確認URL",
      "source_kind": "official",
      "fields": {
        "name": "pass",
        "date": "pass",
        "time": "corrected",
        "venue": "pass",
        "price": "unknown",
        "reservation": "pass"
      },
      "corrections": {
        "time": "10:00〜16:00"
      },
      "note": "公式プログラムで開催時間を補完"
    }
  ]
}
```

補正は元の探索データを破壊的に書き換えず `corrections` に残す。サイト読込時とValidatorで同じ補正を適用する。これにより「探索時の値」と「公式確認後の修正履歴」の両方を追跡できる。

## 子連れ適性

- A: 幼児・小学生向け要素が明確。親子参加を強く勧めやすい
- B: 子連れ参加しやすいが主目的は家族向けとは限らない
- C: 条件付き。年齢、混雑、時間帯、内容等に注意が必要

必ず短い `family_fit.reason` を付ける。

## 重複判定

次を併用する。
- official_urlの正規化
- nameの正規化
- date_start/date_end
- venue

媒体違いの同一イベントは統合し、公式情報を優先する。

## coverage

各区について最低限:

```json
{
  "ward": "中野区",
  "status": "checked",
  "queries": 12,
  "sources_checked": 8,
  "candidate_count": 14,
  "published_count": 9,
  "note": "区公式、観光、主要施設、媒体、横断検索まで確認"
}
```

週全体で:

```json
{
  "sources_checked": 123,
  "candidate_count": 240,
  "duplicate_removed": 55,
  "excluded_count": 62,
  "published_count": 123,
  "wards": []
}
```

`published_count` は実際のイベント件数と一致させる。

## event JSON

```json
{
  "id": "2026-10-10-nakano-example",
  "ward": "中野区",
  "name": "イベント名",
  "url": "https://...",
  "official_url": "https://...",
  "source": "https://...",
  "image": "https://.../event-image.jpg",
  "period": "10/10〜10/11",
  "date_start": "2026-10-10",
  "date_end": "2026-10-11",
  "time": "10:00〜16:00",
  "venue": "会場名",
  "price": "無料",
  "description": "子連れ利用者が内容を判断できる簡潔な説明",
  "categories": ["祭り","体験"],
  "family_fit": {"grade":"A","reason":"子ども向け体験と縁日あり","age":"幼児〜小学生"},
  "reservation": {"required": false, "note": ""},
  "indoor_outdoor": "outdoor",
  "ai": {"checked_at":"2026-10-06T07:00:00+09:00","confidence":"high","discovery_query":"中野区 10月10日 子ども イベント"}
}
```

## 最終監査

出力前に必ず確認する。

- [ ] 23/23区がchecked
- [ ] 対象週末外のイベントが混じっていない
- [ ] 23区外が混じっていない
- [ ] 同一イベント重複なし
- [ ] 必須URL確認済み
- [ ] published_count = 実イベント件数
- [ ] コピペ互換フィールドが存在
- [ ] サムネイル画像を各イベントで探索済み
- [ ] 全掲載イベントにverificationレコードが存在
- [ ] verification.statusが全件verified
- [ ] name/date/venueが全件passまたはcorrected
- [ ] corrected項目にはcorrections値と検証ソースが残っている
- [ ] 不明情報を推測で補完していない

その後、

```bash
python tools/enrich_images.py site/data
python tools/validate_data.py --strict --min-image-coverage 0.70 site/data
npm test
```

を通してから公開する。
