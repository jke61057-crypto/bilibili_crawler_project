import unittest
from unittest.mock import patch

from bilibili_core import fetch_video, make_session, markdown, parse_video


class FakeSession:
    def __init__(self, with_subtitles=True, login_required=False):
        self.urls = []
        self.with_subtitles = with_subtitles
        self.login_required = login_required

    def get(self, url, params=None, timeout=None):
        self.urls.append(url)
        if url.endswith("/x/web-interface/view"):
            data = {"code": 0, "data": {"title": "测试视频", "pages": [
                {"cid": 11, "part": "上", "duration": 100},
                {"cid": 22, "part": "下", "duration": 100},
            ]}}
        elif url.endswith("/x/player/wbi/v2"):
            self.player_params = params
            subtitles = [{"lan": "en", "subtitle_url": "//aisubtitle.hdslb.com/en.json"},
                         {"lan": "zh-CN", "lan_doc": "中文", "subtitle_url": "//aisubtitle.hdslb.com/zh.json"}]
            data = {"code": 0, "data": {"need_login_subtitle": self.login_required,
                                        "subtitle": {"subtitles": subtitles if self.with_subtitles else []}}}
        elif url == "https://aisubtitle.hdslb.com/zh.json":
            data = {"body": [{"from": 0.5, "to": 2.0, "content": "第一句"},
                             {"from": 182.0, "to": 185.0, "content": "第二句"}]}
        else:
            raise AssertionError(f"意外请求：{url}")
        return FakeResponse(data)


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class PreviewVideoTests(unittest.TestCase):
    def test_extract_full_timed_subtitles_without_media_requests(self):
        session = FakeSession()
        data = fetch_video(session, "BV1tMtm6nEzo", 2)
        self.assertEqual(session.player_params["cid"], 22)
        self.assertEqual([line["text"] for line in data["lines"]], ["第一句", "第二句"])
        output = markdown(data)
        self.assertIn("第一句", output)
        self.assertIn("第二句", output)
        self.assertEqual(len(session.urls), 3)

    def test_no_subtitles_is_explicit(self):
        with self.assertRaisesRegex(RuntimeError, "没有可用字幕"):
            fetch_video(FakeSession(with_subtitles=False), "BV1tMtm6nEzo", 1)

    def test_login_required_is_not_reported_as_no_subtitles(self):
        with self.assertRaisesRegex(RuntimeError, "要求登录"):
            fetch_video(FakeSession(with_subtitles=False, login_required=True), "BV1tMtm6nEzo", 1)

    def test_link_part(self):
        self.assertEqual(parse_video("https://www.bilibili.com/video/BV1tMtm6nEzo/?p=2"),
                         ("BV1tMtm6nEzo", 2))

    def test_prompt_cookie_is_used_without_browser_database(self):
        with patch.dict("os.environ", {}, clear=True), patch("getpass.getpass", return_value="test-cookie"):
            session = make_session(prompt_sessdata=True)
        self.assertEqual(session.cookies.get("SESSDATA", domain=".bilibili.com"), "test-cookie")

    def test_no_cookie_is_embedded_in_source(self):
        with patch.dict("os.environ", {}, clear=True):
            session = make_session()
        self.assertIsNone(session.cookies.get("SESSDATA", domain=".bilibili.com"))


if __name__ == "__main__":
    unittest.main()
