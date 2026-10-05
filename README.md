# 東京23区 子連れイベント AIガイド

チャッピーが東京23区を1区ずつ横断探索し、週末に子連れで参加できそうなイベントを編集・公開する独立サイトです。

## 最重要: GitHub正本プロンプト方式

競馬予想 `keiba-notes` と同じ考え方で運用します。

イベント更新を始めるときは、**ファイル名から最新版を推測してはいけません**。必ず最初に:

1. `site/data/latest_prompt.json` を読む
2. `version` と `path` を解決する
3. `path` が指す完全版プロンプトを取得する
4. そのプロンプトに書かれた順序で探索 → 候補固定 → 画像取得 → 公式再監査 → 補正 → 機械検証 → 公開を行う

現在の正本は `latest_prompt.json` が指す版です。

プロンプト改訂時は旧版を削除せず、`site/data/prompt_history.json` に変更内容と理由を追記します。`latest_prompt.json` と履歴が矛盾するとCIが失敗します。

## 週ごとの実行証跡

各週データは `run_file` を持ちます。run manifestには以下を保存します。

- 使用したプロンプトversion/path
- `latest_prompt.json` を解決した証跡
- 23区探索
- 重複排除
- 掲載候補固定
- サムネイル取得
- 公式全件再監査
- 補正適用
- strict validator
- コピペ契約テスト
- 共通検索テスト
- deploy

これにより「この週のデータが、どのプロンプト版のどの手順で作られたか」を追跡できます。

## 方針

- 東京23区を毎回すべて確認し、区ごとの探索状況を可視化する
- 公式情報、東京都・区、子育て/イベント媒体、施設公式、Web横断検索を併用する
- 「子ども向け」と明記されていない祭り・鉄道・科学・防災・商店街等も子連れ適性をAI判定する
- 掲載候補確定後、**全件を公式・主催者情報で再監査**する
- 23区・キーワードで検索できる
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

公式確認情報やprompt/run情報はコピー本文へ混ぜません。

## 公開ゲート

本番データは次をすべて満たさない限りGitHub Pagesへデプロイしません。

- canonical prompt pointer/history整合
- 各週run manifestが最新版prompt version/pathを参照
- run manifestの公開前工程が全てPASS
- 23区すべて `checked`
- 対象週末・正式区名・必須URLの整合
- 重複なし
- `coverage.published_count == events.length`
- 全掲載イベントにverificationレコードあり
- verification全件 `verified`
- name/date/venueが全件 `pass` または `corrected`
- サムネイル取得率70%以上
- コピペ契約・共通検索の回帰テスト成功

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
- `site/data/*-run.json` : 週ごとの実行証跡
- `site/data/*-verification.json` : 公式再監査・補正証跡
- `site/index.html` : イベント一覧、23区検索、探索/検証/使用prompt可視化
- `site/copy.html` : コピペ用リスト
- `site/copy-contract.js` : コピペ契約 v1
- `.github/scripts/validate-prompt-history.mjs` : prompt pointer/history/run整合検証
- `tools/validate_data.py` : イベント・verification公開前検証
- `.github/workflows/deploy.yml` : 全ゲート成功時のみGitHub Pagesへ公開

旧 `prompts/weekly_search.md` はv1.2の履歴として保持し、今後の最新版判定には使用しません。
