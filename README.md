# 東京23区 子連れイベント AIガイド

チャッピーが東京23区を1区ずつ横断探索し、週末に子連れで参加できそうなイベントを編集・公開する独立サイトです。

## 方針

- 東京23区を毎回すべて確認し、区ごとの探索状況を可視化する
- 公式情報、東京都・区、子育て/イベント媒体、施設公式、Web横断検索を併用する
- 「子ども向け」と明記されていない祭り・鉄道・科学・防災・商店街等も子連れ適性をAI判定する
- 23区・キーワードで検索できる
- 既存 `tokyo-weekend-events` と完全分離し、既存サイトを壊さない
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

フォールバックも既存サイトと同じです。

- タイトル: `name || url`
- 場所: `venue || ward`
- 日時: `period` + 時刻があれば全角スペース + `time`
- 料金: `price || （料金情報は公式サイトでご確認ください）`
- 公式サイト: `official_url || url`
- 情報元サイト: `source || ''`
- 画像URL: `image` がある場合のみ追加

一覧画面とコピペ画面は同じ `filterEvents()` を使い、`date`, `ward`, `q` をURLパラメータで引き継ぎます。

## 公開ゲート

本番データは次をすべて満たさない限りGitHub Pagesへデプロイしません。

- 23区すべてに探索ステータスがある
- 23区すべてが `checked`
- イベントの `ward` が東京23区の正式区名
- 必須URLがHTTP(S)
- 重複イベントなし
- `coverage.published_count == events.length`
- `sample != true`
- コピペ契約の回帰テスト成功

検証コマンド:

```bash
python tools/validate_data.py --strict site/data
npm test
```

## 構成

- `site/index.html` : イベント一覧、23区フィルタ、キーワード検索、AI探索レポート
- `site/copy.html` : コピペ用リスト
- `site/app.js` : 共通フィルタ・日付・23区定義
- `site/copy-contract.js` : コピペ契約 v1
- `tools/validate_data.py` : 公開前データ検証
- `tests/copy_contract.test.mjs` : コピペ回帰テスト
- `docs/DESIGN.md` : 設計詳細
- `prompts/weekly_search.md` : 23区AI探索の週次ランブック
- `.github/workflows/deploy.yml` : 検証成功時のみGitHub Pagesへ公開
