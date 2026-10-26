import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.audit_nerima_forest_publication import reconcile
from tools.nerima_forest_schedule import SOURCE_URL


PROGRAMMES = (
    ("2026-11-08", "中ノ宮竹林こどもまつり", "中ノ宮竹林公園"),
    ("2026-11-21", "落ち葉と森の素材あそび", "南高松の森緑地"),
    ("2026-11-29", "モルックであそぼう", "きたっぱら憩いの森"),
)


def schedule_html():
    rows = []
    for day, name, venue in PROGRAMMES:
        yyyy, month, dd = day.split("-")
        cells = [f"令和8年{int(month)}月{int(dd)}日（日曜）午前10時から",
                 name + "（遊び）", venue + "（東京都練馬区）", "区民団体"]
        rows.append("<tr>" + "".join("<td>" + c + "</td>" for c in cells) + "</tr>")
    return ("<h1>ねりまの森こどもフェスタ2026</h1><table>"
            "<tr><th>日程</th><th>イベント内容</th><th>場所</th><th>区民団体名</th></tr>"
            + "".join(rows) + "</table>")


def events():
    return [
        {"id": f"new-{i}", "name": "ねりまの森こどもフェスタ「" + name + "」",
         "venue": venue + "（東京都練馬区）", "date_start": day,
         "date_end": day, "official_url": SOURCE_URL}
        for i, (day, name, venue) in enumerate(PROGRAMMES)
    ]


def write_dataset(root, rows):
    manifest = {"weekends": [
        {"sat": "2026-11-07", "sun": "2026-11-08", "file": "2026-11-07.json"},
        {"sat": "2026-11-21", "sun": "2026-11-22", "file": "2026-11-21.json"},
        {"sat": "2026-11-28", "sun": "2026-11-29", "file": "2026-11-28.json"}
    ]}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for week in manifest["weekends"]:
        sat, sun = week["sat"], week["sun"]
        subset = [ev for ev in rows if sat <= ev["date_start"] <= sun]
        (root / (sat + "-events.json")).write_text(
            json.dumps(subset, ensure_ascii=False), encoding="utf-8")
        (root / (sat + ".json")).write_text(
            json.dumps({"event_files": [sat + "-events.json"],
                        "coverage": {"published_count": len(subset)}}),
            encoding="utf-8")


class PublishedNerimaForestTests(unittest.TestCase):
    def evaluate(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_dataset(root, rows)
            existing = {p.name: p.read_bytes() for p in root.iterdir()}
            report = reconcile(schedule_html(), root)
            self.assertEqual(existing, {p.name: p.read_bytes() for p in root.iterdir()},
                             "Read-only audit must never edit dataset")
            return report

    def test_all_three_official_rows_have_distinct_publications(self):
        result = self.evaluate(events())
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["published_rows"], 3)
        self.assertEqual(result["unreconciled_rows"], 0)

    def test_missing_middle_week_is_detected_even_when_other_weeks_exist(self):
        result = self.evaluate([x for x in events() if x["date_start"] != "2026-11-21"])
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["unreconciled_rows"], 1)
        self.assertEqual(result["rows"][1]["date"], "2026-11-21")
        self.assertEqual(result["rows"][1]["status"], "missing")

    def test_parent_festival_article_is_not_one_event_per_official_row(self):
        parent = {"id": "parent", "name": "ねりまの森こどもフェスタ",
                  "venue": "練馬区内各所", "date_start": "2026-11-07",
                  "date_end": "2026-11-29", "official_url": SOURCE_URL}
        result = self.evaluate([parent])
        self.assertEqual(result["unreconciled_rows"], 3)

    def test_wrong_place_and_wrong_source_are_not_matched(self):
        wrong = events()
        wrong[1]["venue"] = "全く別の会場"
        wrong[2]["official_url"] = "https://not-official.example.test/"
        report = self.evaluate(wrong)
        self.assertEqual(report["unreconciled_rows"], 2)

    def test_two_matching_ids_are_an_ambiguity_not_success(self):
        rows = events()
        duplicate = copy.deepcopy(rows[0])
        duplicate["id"] = "different-id"
        result = self.evaluate(rows + [duplicate])
        self.assertEqual(result["rows"][0]["status"], "ambiguous")
        self.assertEqual(result["unreconciled_rows"], 1)


    def test_tuesday_public_holiday_belongs_to_previous_weekend_shard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_dataset(root, events())
            m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            m["weekends"].insert(0, {"sat": "2026-10-31", "sun": "2026-11-01",
                                      "file": "2026-10-31.json"})
            m["holidays"] = [{"date": "2026-11-03", "name": "文化の日"}]
            (root / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
            special = {"id": "nov3-forest", "name": "ねりまの森こどもフェスタ 秋のフェア",
                       "venue": "大関山の森緑地（練馬区）",
                       "date_start": "2026-11-03", "date_end": "2026-11-03",
                       "official_url": SOURCE_URL}
            (root / "2026-10-31-events.json").write_text(
                json.dumps([special], ensure_ascii=False), encoding="utf-8")
            (root / "2026-10-31.json").write_text(
                json.dumps({"event_files": ["2026-10-31-events.json"],
                            "coverage": {"published_count": 1}}), encoding="utf-8")
            row = ("<tr><td>令和8年11月3日（火曜・祝日）午前9時から</td>"
                   "<td>秋のフェア（公式体験）</td><td>大関山の森緑地（関町北）</td>"
                   "<td>区民団体</td></tr>")
            html = schedule_html().replace("</table>", row + "</table>", 1)
            report = reconcile(html, root)
            self.assertEqual(report["in_horizon_official_rows"], 4)
            self.assertEqual(report["published_rows"], 4)
            self.assertEqual(report["unreconciled_rows"], 0)

    def test_official_event_in_wrong_week_shard_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_dataset(root, events())
            middle = root / "2026-11-21-events.json"
            late = root / "2026-11-28-events.json"
            missing = json.loads(middle.read_text(encoding="utf-8"))[0]
            middle.write_text("[]", encoding="utf-8")
            original = json.loads(late.read_text(encoding="utf-8"))
            late.write_text(json.dumps(original + [missing], ensure_ascii=False),
                            encoding="utf-8")
            for week, count in (("2026-11-21", 0), ("2026-11-28", 2)):
                p = root / (week + ".json")
                document = json.loads(p.read_text(encoding="utf-8"))
                document["coverage"]["published_count"] = count
                p.write_text(json.dumps(document), encoding="utf-8")
            report = reconcile(schedule_html(), root)
            self.assertEqual(report["rows"][1]["status"], "missing")


if __name__ == "__main__":
    unittest.main()
