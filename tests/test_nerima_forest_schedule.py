import datetime as dt
import unittest

from tools.nerima_forest_schedule import parse_schedule, SOURCE_ID, SOURCE_URL


def table_html(rows):
    head = "<tr><th>日程</th><th>イベント内容</th><th>場所</th><th>区民団体名</th></tr>"
    body = "".join("<tr>" + "".join("<td>" + str(x) + "</td>" for x in row) + "</tr>" for row in rows)
    # Bingo venue listing is intentionally a separate table and never produces
    # a standalone event (these venues are NOT festival dates).
    return ("<h1>ねりまの森こどもフェスタ2026</h1>"
            "<table>" + head + body + "</table>"
            "<h2>ビンゴ開催場所</h2><table><tr><th>場所</th><th>住所</th></tr>"
            "<tr><td>中ノ宮竹林公園</td><td>春日町</td></tr></table>")


DATES = [
    ("9月26日", "草引っこ抜き競争", "西本村憩いの森"),
    ("10月4日", "ランタンづくり", "千坪憩いの森"),
    ("11月3日", "秋のフェア", "大関山の森緑地"),
    ("11月3日", "落ち葉あそび", "竹の子憩いの森"),
    ("11月8日", "中ノ宮竹林こどもまつり", "中ノ宮竹林公園"),
    ("11月21日", "落ち葉と森の素材あそび", "南高松の森緑地"),
    ("11月29日", "モルックであそぼう", "きたっぱら憩いの森"),
    ("12月5日", "落ち葉祭り", "石庭の森緑地"),
    ("12月5日", "森のおしごと体験", "南高松の森緑地"),
    ("12月5日", "森のおしごと体験", "大関山の森緑地"),
    ("12月26日", "森のおしごと体験", "西本村憩いの森"),
]
ROWS = [
    ("令和8年" + date + "（日曜） 午前10時から午後3時まで",
     title + "（公式体験）", venue + "（練馬区内）", "区民団体")
    for date, title, venue in DATES
]


class NerimaForestScheduleTests(unittest.TestCase):
    def test_whole_table_and_current_horizon_parity(self):
        result = parse_schedule(table_html(ROWS), dt.date(2026, 10, 31),
                                dt.date(2026, 12, 6))
        self.assertEqual(result["source_id"], SOURCE_ID)
        self.assertEqual(result["official_row_count"], 11)
        self.assertEqual(result["candidate_count"], 8)
        self.assertEqual(result["outside_target_count"], 3)
        selected = result["candidates"]
        self.assertEqual(
            [x["date_start"] for x in selected],
            ["2026-11-03", "2026-11-03", "2026-11-08",
             "2026-11-21", "2026-11-29", "2026-12-05",
             "2026-12-05", "2026-12-05"])
        self.assertEqual(len(set(result["candidate_ids"])), 8)
        self.assertEqual({x["official_url"] for x in selected}, {SOURCE_URL})
        self.assertEqual({x["venue"].split("（")[0] for x in selected
                          if x["date_start"] == "2026-12-05"},
                         {"石庭の森緑地", "南高松の森緑地", "大関山の森緑地"})

    def test_one_week_does_not_pretend_others_were_checked(self):
        result = parse_schedule(table_html(ROWS), dt.date(2026, 11, 7),
                                dt.date(2026, 11, 8))
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["official_row_count"], 11)
        self.assertEqual(result["candidates"][0]["name"], "中ノ宮竹林こどもまつり")

    def test_bad_or_duplicate_source_rows_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_schedule(table_html(ROWS + [ROWS[4]]),
                           dt.date(2026, 10, 31), dt.date(2026, 12, 6))
        broken = list(ROWS)
        broken[4] = ("不明の日付", *broken[4][1:])
        with self.assertRaisesRegex(ValueError, "unparseable"):
            parse_schedule(table_html(broken),
                           dt.date(2026, 10, 31), dt.date(2026, 12, 6))
        with self.assertRaisesRegex(ValueError, "missing event schedule"):
            parse_schedule("<h1>ねりまの森こどもフェスタ2026</h1><p>予定</p>",
                           dt.date(2026, 10, 31), dt.date(2026, 12, 6))


if __name__ == "__main__":
    unittest.main()
