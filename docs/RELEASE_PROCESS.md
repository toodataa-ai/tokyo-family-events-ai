# RELEASE PROCESS

このリポジトリは、**アプリ改修**と**定例データ更新**を別経路で公開する。

## 1. ブランチの役割

### アプリ／UI

- `main`: ステージング・開発。通常の改修はここで何回でも行う。
- `production`: ユーザー向け本番で使うアプリ／UIの正本。
- `release/*`: 実際に本番公開成功したアプリ版の不変スナップショット。
- `.github/production-releases.json`: 公開済みアプリ版の台帳。

### 定例イベントデータ

- `data-staging`: 休日明け自動更新が作るデータ候補。ユーザー公開には直接使わない。
- `data-production`: ユーザー向け本番で使うイベントデータの正本。
- `data-release/*`: 本番データ公開成功時だけ作る不変スナップショット。

現在の初期データ断面:

- `data-release/2026-10-08-baseline`

## 2. 公開URL

- 本番: `https://toodataa-ai.github.io/tokyo-family-events-ai/`
- ステージング: `https://toodataa-ai.github.io/tokyo-family-events-ai/staging/`

ステージングには CI が `noindex,nofollow` と視覚マーカーをデプロイ時だけ付与する。マーカーは production ソースには保存しない。

## 3. アプリ改修の流れ

1. HTML/CSS/JS、検索ロジック、収集ルール、プロンプト仕様、データスキーマ等の改修は `main` だけに入れる。
2. CI で検証し、`/staging/` で確認する。
3. 必要なら `main` 上で何回でも改修する。
4. ユーザーの明示承認後だけ `production` を承認済みコミットへ進める。
5. main の Pages ゲートから本番デプロイし、成功確認後だけ `release/*` と公開版台帳へ登録する。

ステージング途中コミットはアプリのロールバック候補にはしない。

## 4. 休日明けの定例データ更新

定例データ更新はアプリ改修と異なり、**検証合格後に自動で本番へ反映する**。

1. 自動タスクは、公開済み `production` の `site/data/latest_prompt.json` を正本として読む。
2. 現在の `data-production` SHA を取得する。
3. `data-staging` をその SHA へ同期して、前回の失敗候補を持ち越さない。
4. `data-staging` 上でイベントデータだけを更新する。
5. 更新可能範囲は以下に限定する。
   - `site/data/YYYY-MM-DD*.json`
   - `site/data/manifest.json`
   - `site/data/update_history.json`
6. HTML/CSS/JS、tools、prompts、latest_prompt、prompt_history、discovery_sources、評価ルーブリック等は定例データ更新では変更しない。変更が必要なら「改修」として main → staging の承認経路へ回す。
7. 全データ書き込み後の `data-staging` SHA と、開始時の `data-production` SHA を `main/.github/data-deploy-trigger.txt` に記録する。
8. main の唯一の Pages ワークフローが、公開済み production の検証ロジックでデータ候補を再検証する。
9. 合格時だけ `data-production` を候補 SHA へ進め、本番を **production のアプリ + data-production のデータ** で再構成して公開する。
10. Pages 成功時だけ `data-release/YYYY-MM-DD-rN` を作成する。
11. デプロイに失敗した場合は `data-production` を直前 SHA に戻し、既存公開データを維持する。

これにより、ステージングで未承認の UI/コードが存在していても、定例データだけは独立して安全に本番更新できる。

## 5. 本番の合成ルール

本番 Pages は次の2系統を合成する。

- アプリ／UI: `production/site`
- 動的イベントデータ: `data-production/site/data` のうち日付別JSON、`manifest.json`、`update_history.json`

静的な収集ポリシーやプロンプト設定は production 側を使用する。

ステージングは `main/site` に最新の `data-production` 動的データを重ねるため、改修確認時も本番相当の最新データで確認できる。

## 6. アプリのロールバック

1. `.github/production-releases.json` から公開実績のある `release/*` を選ぶ。
2. 台帳 SHA と release ブランチ SHA の一致を確認する。
3. `production` をその公開断面へ force-with-lease で戻す。
4. `.github/release-trigger.txt` を更新して main の Pages ゲートを実行する。
5. 本番成功を確認する。
6. `main` は変更しないため、新しい改修版は引き続き staging で診断できる。

任意の main コミットへ直接ロールバックしてはいけない。

## 7. データのロールバック

1. 正常公開済みの `data-release/*` から戻したいデータ断面を選ぶ。
2. `data-production` をその snapshot SHA へ force-with-lease で戻す。
3. main のデータデプロイトリガーを更新する。
4. production アプリ + 復元した data-production データで Pages を再公開する。
5. `main` と `production` のアプリ版は変更しない。

つまり、アプリの Version 1.xx を戻さずに「データだけ前回公開分へ戻す」ことができる。

## 8. 安全ルール

- production を通常改修の作業場所にしない。
- data-production を直接編集しない。
- 定例データ更新は必ず data-staging から始める。
- `release/*` と `data-release/*` は公開成功後にだけ作り、後から書き換えない。
- データ更新がコード／ルール／スキーマ変更を必要としたら自動公開せず、改修扱いに切り替える。
- GitHub Pages の実デプロイは main のワークフローだけを使う。
- アプリ版番号とデータ更新履歴は別管理する。
