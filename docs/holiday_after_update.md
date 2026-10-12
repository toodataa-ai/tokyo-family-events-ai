# 休日明け6週間更新：日付可変計画（ステージング用）

本処理は **計画専用** であり、イベントの探索・再監査・本番更新・デプロイは実行しない。旧 tools/initial_v15_native_research.py は2026年10月の固定日付と古い判定ロジックを持つため、v1.15以降の正式な更新には使用しない。

最初に production ブランチの site/data/latest_prompt.json と prompt_history.json の整合を確認し、data-production の現行SHAを固定する。site/data のmanifestは data-production の実データを使用する。

実行例：

    python3 tools/rolling_horizon.py --as-of 2026-10-13 --base-data-production-sha <実際の40文字SHA> --output /tmp/holiday-plan.json

--as-of を省略すると日本時間の当日日付を採用。内閣府公式祝日CSV取得失敗・年度不足はBLOCKERとして失敗、休日明け以外は status=skipped。対象日なら status=eligible と42日間、6つの週末、祝日、検索URLを出力する。公式祝日は土日と別の平日祝日探索対象として扱う。

planは site/data には書き込めず、検索結果や「checked」「verified」は生成しない。計画を使い、正式プロンプトに基づく23区それぞれのAI探索、全required明示参照元、年間日程表の行単位監査、候補decision、公式照合、非退行、画像、祝日開催可否の実測を完了する。未完了なら公開不可。

変更候補は data-production の基準SHAに基づく data-staging 上のデータ許可ファイルに限定し、Strict検証後のみ既存の data専用デプロイ経路を利用する。production アプリコード・公開Versionは変更しない。

回帰テスト: npm test （Python単体は python3 -m unittest discover -s tests -p test_rolling_horizon.py）。

## 休日明け更新の履歴を必ず保存

実際の23区探索、全公式監査、画像、厳格バリデーションが終わり、未公開の data-staging 候補を作成したあと、data-production の現行SHAを基準に履歴を生成する。

    node tools/holiday_update_history.mjs --write --as-of 2026-10-13 --base-ref <data-production-SHA> --data-dir site/data

これにより既存の履歴を残したまま、更新日・6週間の対象期間・前後のユニークイベント数・追加・変更・掲載終了・対象期間外に出た数の1行が増える。イベント個票は公開アプリの eventIdentityKey と同じキー、verifications とサブファイルを読み込んで数える。実際の更新をしなかった場合は生成しない。

data-staging に上記JSONを含めてコミットする。operation=holiday-after-update のデータ本番反映時は、既存の CI で厳格監査したあと、さらに node staging-policy-src/tools/holiday_update_history.mjs --check ... を実行し、過去履歴の削除、未記録、件数差異や期間差異を検出したら公開を止める。**Pages反映成功後にのみ本番で履歴が見える**。アプリのリリースだけではデータ更新履歴に追加しない。
