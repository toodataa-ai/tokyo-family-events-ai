"""Regression for actual 2026-11-09 404/403/Cloudflare and safe index fallback."""
import io
from collections import defaultdict
from email.message import Message
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from http_source_diagnostics import (
    diagnostic_for_http_error, suggested_official_index, official_index_fallback_proof
)
from holiday_after_collect import fetch_url
import followup_unresolved_617_urls_20261109 as followup

def http_error(url, status, server, raw):
    headers=Message()
    headers["Server"]=server
    headers["Content-Type"]="text/html; charset=UTF-8"
    if server.lower()=="cloudflare":
        headers["CF-Ray"]="mock-test"
    return HTTPError(url,status,"test HTTP error",headers,io.BytesIO(raw))

class HTTPErrorEvidenceTests(unittest.TestCase):
    def test_suginami_official_404_exposes_bounded_metadata_and_preserves_error(self):
        url="https://www.city.suginami.tokyo.jp/s019/event/23456.html"
        err=http_error(url,404,"openresty",b"<html><title>" +
                       "ページが見つかりません｜杉並区公式ホームページ".encode() +
                       b"</title><body>Not found</body></html>")
        result=diagnostic_for_http_error(err)
        self.assertEqual(result["http_status"],404)
        self.assertEqual(result["error_kind"],"official_page_not_found")
        self.assertEqual(result["response_server"],"openresty")
        self.assertIn("ページが見つかりません",result["response_title"])
        self.assertEqual(len(result["error_body_sha256"]),64)
        self.assertNotIn("body",result)
        self.assertFalse(result["challenge_detected"])

    def test_tamemap_cloudflare_security_challenge_never_upgrades_source(self):
        url="https://pc.tamemap.net/1311401/calendar/2026-11"
        err=http_error(url,403,"cloudflare",
            b"<html><title>Just a moment...</title><body>challenge-platform</body></html>")
        with patch("holiday_after_collect.time.sleep"):
            evidence=fetch_url(url,fetcher=lambda _:(_ for _ in ()).throw(err), attempts=1)
        self.assertEqual(evidence["status"],"error")
        self.assertEqual(evidence["http_status"],403)
        self.assertEqual(evidence["error_kind"],"security_challenge")
        self.assertTrue(evidence["challenge_detected"])
        self.assertEqual(evidence["response_title"],"Just a moment...")
        self.assertNotIn("body",evidence)

    def test_same_retry_can_succeed_without_leaking_prior_error_metadata(self):
        url="https://www.city.nerima.tokyo.jp/kankomoyoshi/event/example.html"
        count=[0]
        def transport(_):
            count[0]+=1
            if count[0]==1:
                raise http_error(url,404,"AmazonS3",b"<html>Not found</html>")
            return 200,b"<html>OK</html>",url,"text/html"
        with patch("holiday_after_collect.time.sleep"):
            evidence=fetch_url(url,fetcher=transport,attempts=2)
        self.assertEqual(evidence["status"],"checked")
        self.assertNotIn("error_kind",evidence)
        self.assertNotIn("error_body_sha256",evidence)
        self.assertNotIn("error",evidence)

    def test_ambiguous_cross_city_404_keeps_uncertainty(self):
        url="https://www.city.tokyo-nakano.lg.jp/event/page.html"
        evidence=diagnostic_for_http_error(http_error(url,404,"AmazonS3",b"generic not found"))
        self.assertEqual(evidence["error_kind"],"ambiguous_http_404")
        self.assertNotIn("official_page_not_found",evidence.values())

    def test_fallback_city_index_is_not_official_event_detail(self):
        old="https://www.city.suginami.tokyo.jp/s019/event/23456.html"
        index=suggested_official_index(old,404)
        self.assertEqual(index,"https://www.city.suginami.tokyo.jp/event/index.html")
        called=[]
        proof=official_index_fallback_proof(old,404,lambda u:(
            called.append(u) or {"status":"checked_body_not_individually_verified","http_status":200}))
        self.assertEqual(called,[index])
        self.assertTrue(proof["fallback_index_reachable"])
        self.assertTrue(proof["original_source_still_failed"])
        self.assertFalse(proof["event_detail_verified"])
        self.assertEqual(proof["decision_reconciliation"],"pending")
        self.assertIsNone(suggested_official_index(old,403))
        self.assertIsNone(suggested_official_index("https://pc.tamemap.net/1311401/calendar/2026-11",403))
        self.assertIsNone(suggested_official_index("https://x.com/someone",404))
        self.assertIsNone(suggested_official_index("https://www.city.suginami.tokyo.jp/../",404))

    def test_followup_detail_capture_contains_real_404_signature_not_success(self):
        url="https://www.city.suginami.tokyo.jp/s019/event/23456.html"
        def fail(_request,timeout=9):
            raise http_error(url,404,"openresty",b"<title>" +
                             "ページが見つかりません".encode()+b"</title>")
        with patch.object(followup,"urlopen",side_effect=fail):
            result=followup.fetch(url,defaultdict(lambda:threading.BoundedSemaphore(2)))
        self.assertEqual(result["status"],"http_error")
        self.assertEqual(result["http_status"],404)
        self.assertEqual(result["error_kind"],"official_page_not_found")
        self.assertFalse(result.get("individually_verified",False))

if __name__=="__main__":
    unittest.main()
