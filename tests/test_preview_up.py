import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bilibili_core import get_with_retry, latest_bvids, resolve_mid
from preview_up import process_batch


class FakeBrowser:
    last = None

    def __init__(self, impersonate):
        assert impersonate == "chrome110"
        self.urls = []
        FakeBrowser.last = self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def get(self, url, **kwargs):
        self.urls.append(url)
        if url.endswith("/nav"):
            return FakeResponse({"data": {"wbi_img": {
                "img_url": "https://example.com/" + "a" * 32 + ".png",
                "sub_url": "https://example.com/" + "b" * 32 + ".png",
            }}})
        if url.endswith("/arc/search"):
            assert kwargs["params"]["mid"] == "123"
            return FakeResponse({"code": 0, "data": {"list": {"vlist": [
                {"bvid": "BV1tMtm6nEzo"},
                {"bvid": "BV1tMtm6nEzo"},
                {"bvid": "BV1i3RYBxEZJ"},
                {"bvid": "BV1dF526fE5x"},
                {"bvid": "BV1LeVm6aEeG"},
            ]}}})
        raise AssertionError(url)


class FakeResponse:
    def __init__(self, data):
        self.data = data
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeSession:
    class Cookies:
        def get(self, *_args, **_kwargs):
            return None
    cookies = Cookies()


class PreviewUpTests(unittest.TestCase):
    def test_retries_temporary_412(self):
        class Browser:
            calls = 0

            def get(self, *_args, **_kwargs):
                self.calls += 1
                response = FakeResponse({})
                response.status_code = 412 if self.calls == 1 else 200
                return response

        browser = Browser()
        with patch("bilibili_core.time.sleep"):
            get_with_retry(browser, "https://api.bilibili.com/test")
        self.assertEqual(browser.calls, 2)

    def test_latest_three_unique_videos_without_media_download(self):
        with patch("bilibili_core.browser_requests.Session", FakeBrowser):
            result = latest_bvids(FakeSession(), "123")
        self.assertEqual(result, ["BV1tMtm6nEzo", "BV1i3RYBxEZJ", "BV1dF526fE5x"])
        self.assertEqual(len(FakeBrowser.last.urls), 2)

    def test_accepts_space_url_and_mid(self):
        self.assertEqual(resolve_mid(FakeSession(), "https://space.bilibili.com/123/video"), "123")
        self.assertEqual(resolve_mid(FakeSession(), "123"), "123")

    def test_resolves_up_from_video(self):
        with patch("bilibili_core.api_data", return_value={"owner": {"mid": 123}}):
            self.assertEqual(resolve_mid(FakeSession(), "BV1tMtm6nEzo"), "123")

    def test_retry_failed_skips_successful_items_and_retries_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            manifest = out_dir / "up_123_latest2.json"
            # Pre-populate manifest with 1 ok and 1 error
            manifest.write_text(json.dumps([
                {"bvid": "BV1ok", "status": "ok", "title": "成功视频", "lines": 10},
                {"bvid": "BV1err", "status": "error", "reason": "之前网络超时"}
            ], ensure_ascii=False), encoding="utf-8")
            # Create existing files for BV1ok
            (out_dir / "BV1ok_p1.json").write_text("{}", encoding="utf-8")
            (out_dir / "BV1ok_p1.md").write_text("# 成功视频", encoding="utf-8")

            fake_data = {"bvid": "BV1err", "part": 1, "part_title": "P1",
                         "title": "重试成功的视频", "lines": [{"text": "你好"}],
                         "subtitle_language": "zh-CN", "subtitle_type": "中文",
                         "duration": 100, "url": "https://www.bilibili.com/video/BV1err/?p=1"}
            with patch("preview_up.resolve_mid", return_value="123"), \
                 patch("preview_up.fetch_video", return_value=fake_data) as mock_fetch:
                results = process_batch(FakeSession(), "123", count=2, output=out_dir, retry_failed=True)

            # fetch_video should only be called for BV1err, not BV1ok
            self.assertEqual(mock_fetch.call_count, 1)
            self.assertEqual(mock_fetch.call_args[0][1], "BV1err")
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["bvid"], "BV1ok")
            self.assertEqual(results[0]["status"], "ok")
            self.assertEqual(results[1]["bvid"], "BV1err")
            self.assertEqual(results[1]["status"], "ok")

            # Check that manifest file is updated
            saved = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(saved[1]["status"], "ok")

    def test_resume_directly_from_json_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            manifest = out_dir / "up_999_latest1.json"
            manifest.write_text(json.dumps([
                {"bvid": "BV1err", "status": "error", "reason": "失败"}
            ]), encoding="utf-8")

            fake_data = {"bvid": "BV1err", "part": 1, "part_title": "P1",
                         "title": "恢复成功", "lines": [{"text": "内容"}],
                         "subtitle_language": "zh-CN", "subtitle_type": "中文",
                         "duration": 100, "url": "https://www.bilibili.com/video/BV1err/?p=1"}
            with patch("preview_up.fetch_video", return_value=fake_data) as mock_fetch:
                results = process_batch(FakeSession(), str(manifest))

            self.assertEqual(mock_fetch.call_count, 1)
            self.assertEqual(results[0]["status"], "ok")

    def test_batch_without_retry_reprocesses_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            manifest = out_dir / "up_123_latest1.json"
            manifest.write_text(json.dumps([
                {"bvid": "BV1already_ok", "status": "ok", "title": "旧标题", "lines": 5}
            ]), encoding="utf-8")
            (out_dir / "BV1already_ok_p1.json").write_text("{}", encoding="utf-8")
            (out_dir / "BV1already_ok_p1.md").write_text("# 旧标题", encoding="utf-8")

            fake_data = {"bvid": "BV1already_ok", "part": 1, "part_title": "P1",
                         "title": "新标题", "lines": [{"text": "新内容"}],
                         "subtitle_language": "zh-CN", "subtitle_type": "中文",
                         "duration": 100, "url": "https://www.bilibili.com/video/BV1already_ok/?p=1"}
            with patch("preview_up.resolve_mid", return_value="123"), \
                 patch("preview_up.latest_bvids", return_value=["BV1already_ok"]), \
                 patch("preview_up.fetch_video", return_value=fake_data) as mock_fetch:
                results = process_batch(FakeSession(), "123", count=1, output=out_dir, retry_failed=False)

            self.assertEqual(mock_fetch.call_count, 1)
            self.assertEqual(results[0]["title"], "新标题")


if __name__ == "__main__":
    unittest.main()
