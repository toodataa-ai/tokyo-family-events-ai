# 東京23区 子連れイベント AIガイド

チャッピーが東京23区を1区ずつ横断探索し、週末に子連れで参加できそうなイベントを編集・公開する独立サイトです。v1.4からは、直近だけでなく**6週間先までローリングで先取り**します。

## 最重要: GitHub正本プロンプト方式

競馬予想 `keiba-notes` と同じ考え方で運用します。

イベント更新を始めるときは、**ファイル名から最新版を推測してはいけません**。必ず最初に:

1. `site/data/latest_prompt.json` を読む
2. `version` と `path` を解決する
3. `path` が指す完全版プロンプトを取得する
4. そのプロンプトに書かれた順序で探索 → 候補固定 → 画像取得 → 公式再監査 → 補正 → 機械検証 → 公開を行う

プロンプト改訂時は旧版を削除せず、`site/data/prompt_history.json` に変更内容と理由を追記します。`latest_prompt.json` と履歴が矛盾するとCIが失敗します。

## v1.4: 6週間ローリング探索

毎週、基準日から先の土日を6週分確認します。

| horizon | publication_tier | 扱い |
|---|---|---|
| 1〜2 | `full` | 今週〜2週間先。全掲載イベントを公式確認済みにする |
| 3〜4 | `preview` | 3〜4週間先。公式開催発表済みを先取りする |
| 5〜6 | `announcement` | 5〜6週間先。日付・会場まで公式確認できた予定を早期掲載する |

検証ステータスは2段階です。

- `verified`: 掲載に必要な主要情報を公式・主催者情報で確認済み
- `announced`: 開催自体、イベント名、日付、会場は公式確認済みだが、時間・料金・申込等の詳細が未発表

`announced` は「未確認」ではありません。**開催発表の公式根拠がある先取り情報**として扱います。不明項目は推測せず `unknown` とし、詳細公開後の次回runで再監査します。

週が近づくたびに、`announcement → preview → full`、イベントは条件が揃えば `announced → verified` に昇格します。

## 週ごとの実行証跡

各週データは `run_file` を持ちます。run manifestには以下を保存します。

- 使用したプロンプトversion/path
- `latest_prompt.json` を解決した証跡
- `horizon_index`
- `publication_tier`
- 23区探索
- 重複排除
- 掲載候補固定
- サムネイル取得
- 公式再監査
- 補正適用
- strict validator
- コピペ契約テスト
- 共通検索テスト
- deploy

これにより「この週のデータが、どのプロンプト版のどの手順・確度で作られたか」を追跡できます。

## 参照元

各区について以下を順に探索します。

1. 区公式イベント、観光、子育て、文化、公園、図書館、児童館
2. 東京都、都立施設、公園、博物館、美術館、科学館、動物園等
3. 子育て・イベント媒体
4. 商業施設、鉄道、交通、スポーツ、劇場、大学等の公式
5. Web横断検索

候補発見後の公式再監査は、自治体・東京都・公的施設 → 主催者・会場・施設公式 → 公式観光協会 → 主催者提供情報を明記する提携媒体、の順を優先します。

`preview` / `announcement` の `announced` イベントは、原則として自治体・公的施設・主催者・会場・公式観光協会等の公式ソースを必須にします。

## 方針

- 東京23区を毎回すべて確認し、区ごとの探索状況を可視化する
- 「子ども向け」と明記されていない祭り・鉄道・科学・防災・商店街等も子連れ適性をAI判定する
- 近い週は全件を公式・主催者情報で再監査する
- 遠い週は開催発表済み情報を先取りし、未発表項目を推測しない
- 23区・キーワード・6週間の週切替で検索できる
- 既存 `tokyo-weekend-events` と完全分離する
- コピペ用リストを最重要互換機能として保護する

## コピペ契約 v1

出力順を固定します。

1. タイトル
2. 場所
3. 日時
4. 料金
5. 説明
6. 公式サイト
7. 情報元サイト
8. サムネイル画像URL（画像がある場合のみ）

フォールバック:
- タイトル: `name || url`
- 場所: `venue || ward`
- 日時: `period` + 時刻があれば全角スペース + `time`
- 料金: `price || （料金情報は公式サイトでご確認ください）`
- 公式サイト: `official_url || url`
- 情報元サイト: `source || ''`
- 画像URL: `image` がある場合のみ追加

公式確認情報、確定度、prompt/run情報はコピー本文へ混ぜません。

## 公開ゲート

全週共通:

- canonical prompt pointer/history整合
- 各週run manifestが最新版prompt version/pathを参照
- run manifestの公開前工程が全てPASS
- 23区すべて `checked`
- 対象週末・正式区名・必須URLの整合
- 重複なし
- `coverage.published_count == events.length`
- 全掲載イベントにverificationレコードあり
- name/date/venueが全件 `pass` または `corrected`
- コピペ契約・共通検索の回帰テスト成功

`full` 追加条件:
- verification全件 `verified`
- サムネイル取得率70%以上

`preview` / `announcement` 追加条件:
- verification全件 `verified` または `announced`
- `announced` は公式ソース必須
- 未確定項目をnoteに明記
- 画像不足だけでは公開停止しない

検証コマンド:

```bash
node .github/scripts/validate-prompt-history.mjs
python tools/enrich_images.py site/data
python tools/validate_data.py --strict --min-image-coverage 0.70 site/data
npm test
```

## 構成

- `site/data/latest_prompt.json` : 最新版プロンプトの唯一のポインタ
- `site/data/prompt_history.json` : 追記型プロンプト履歴
- `prompts/tokyo_family_events_complete_prompt_v*.txt` : 完全版プロンプト
- `site/data/manifest.json` : 6週間ローリング設定と公開済み週一覧
- `site/data/*-run.json` : 週ごとの実行証跡
- `site/data/*-verification.json` : 公式再監査・補正証跡
- `site/index.html` : 6週間ナビ、イベント一覧、23区検索、探索/検証/使用prompt可視化
- `site/copy.html` : コピペ用リスト
- `site/copy-contract.js` : コピペ契約 v1
- `.github/scripts/validate-prompt-history.mjs` : prompt pointer/history/run整合検証
- `tools/validate_data.py` : tier別イベント・verification公開前検証
- `.github/workflows/deploy.yml` : 全ゲート成功時のみGitHub Pagesへ公開

旧版プロンプトは履歴として保持し、最新版判定には必ず `site/data/latest_prompt.json` を使用します。
