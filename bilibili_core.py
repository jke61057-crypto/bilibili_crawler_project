"""Bilibili metadata, subtitle, and UP-list operations for the MVP.

CORE INVARIANT / HIGHEST PRIORITY:
- ALWAYS prioritize reading subtitles directly from Bilibili APIs.
- NEVER request or download video or audio stream URLs from the internet.
- NEVER run speech-to-text / Whisper transcription models.
"""

import getpass
import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from curl_cffi import requests as browser_requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BVID_RE = re.compile(r"BV[0-9A-Za-z]{10}")
API = "https://api.bilibili.com"
DEFAULT_SESSDATA = ""


def _load_env():
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val


_load_env()


def parse_video(value):
    match = BVID_RE.search(value)
    if not match:
        raise ValueError("请输入有效的 BV 号或 bilibili.com/video/BV... 链接")
    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        if parsed.hostname not in {"www.bilibili.com", "bilibili.com", "m.bilibili.com"}:
            raise ValueError("只接受 bilibili.com 视频链接")
        part = int(parse_qs(parsed.query).get("p", ["1"])[0])
    else:
        part = 1
    if part < 1:
        raise ValueError("分 P 编号必须从 1 开始")
    return match.group(), part


def make_session(browser=None, prompt_sessdata=False):
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/",
    })
    cookie = os.environ.get("BILIBILI_SESSDATA") or DEFAULT_SESSDATA
    if prompt_sessdata:
        entered = getpass.getpass("粘贴 B 站 SESSDATA（输入不会显示）：").strip()
        if entered:
            cookie = entered
        elif not cookie:
            raise RuntimeError("未输入 SESSDATA")
    if browser:
        try:
            from yt_dlp.cookies import extract_cookies_from_browser
            cookies = extract_cookies_from_browser(browser)
            cookie = next((item.value for item in cookies
                           if item.name == "SESSDATA" and item.domain.endswith("bilibili.com")), None)
        except Exception as exc:
            raise RuntimeError(
                f"读取 {browser} 登录 Cookie 失败：{exc}。可关闭浏览器后重试，"
                "或用 --prompt-sessdata 手动输入，不会写入命令历史"
            ) from exc
        if not cookie:
            raise RuntimeError(f"{browser} 中没有找到 B 站登录 Cookie；请先在该浏览器登录")
    if cookie:
        session.cookies.set("SESSDATA", cookie, domain=".bilibili.com")
    return session


def get_json(session, url, *, params=None):
    response = session.get(url, params=params, timeout=(5, 20))
    response.raise_for_status()
    return response.json()


def api_data(session, path, params):
    result = get_json(session, API + path, params=params)
    if result.get("code") != 0 or not isinstance(result.get("data"), dict):
        raise RuntimeError(f"B 站接口 {path} 失败：{result.get('code')} {result.get('message')}")
    return result["data"]


def select_subtitle(subtitles):
    candidates = [item for item in subtitles if item.get("subtitle_url")]
    if not candidates:
        raise RuntimeError("此分 P 没有可用字幕；未下载音视频，也未进行语音转写")
    return min(candidates, key=lambda item: (
        0 if item.get("lan") == "zh-CN" else 1 if item.get("lan") == "ai-zh" else
        2 if "zh" in item.get("lan", "") else 3,
        item.get("lan", ""),
    ))


def fetch_video(session, bvid, part):
    view = api_data(session, "/x/web-interface/view", {"bvid": bvid})
    pages = view.get("pages") or []
    if part > len(pages):
        raise ValueError(f"该视频只有 {len(pages)} 个分 P，无法读取第 {part} P")
    page = pages[part - 1]
    cid = page["cid"]
    aid = view.get("aid")
    subtitles = []
    need_login = False
    try:
        player = api_data(session, "/x/player/wbi/v2", {"bvid": bvid, "cid": cid})
        if player.get("need_login_subtitle"):
            need_login = True
        else:
            subtitles = (player.get("subtitle") or {}).get("subtitles") or []
    except Exception:
        pass

    if not subtitles and aid:
        try:
            dm_view = get_json(session, API + "/x/v2/dm/view", params={"aid": aid, "oid": cid, "type": 1})
            subtitles = ((dm_view.get("data") or {}).get("subtitle") or {}).get("subtitles") or []
        except Exception:
            pass

    if not subtitles:
        if need_login:
            raise RuntimeError("B 站要求登录后获取字幕；请设置 BILIBILI_SESSDATA，或使用 --prompt-sessdata")
        raise RuntimeError("此分 P 没有可用字幕；未下载音视频，也未进行语音转写")

    subtitle = select_subtitle(subtitles)
    subtitle_url = subtitle["subtitle_url"]
    if subtitle_url.startswith("//"):
        subtitle_url = "https:" + subtitle_url
    elif subtitle_url.startswith("http://"):
        subtitle_url = "https://" + subtitle_url[len("http://"):]
    parsed = urlparse(subtitle_url)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".hdslb.com"):
        raise RuntimeError("字幕地址不在预期的 B 站 CDN 域名下，已停止请求")
    raw = get_json(session, subtitle_url)
    body = raw.get("body")
    if not isinstance(body, list) or not body:
        raise RuntimeError("字幕文件为空或格式异常")
    lines = []
    for item in body:
        start, end, content = item.get("from"), item.get("to"), item.get("content")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or not isinstance(content, str):
            raise RuntimeError("字幕包含缺少时间或正文的条目，已停止以免输出不完整结果")
        lines.append({"start": start, "end": end, "text": content})
    return {
        "bvid": bvid,
        "part": part,
        "cid": cid,
        "title": view.get("title", ""),
        "part_title": page.get("part", ""),
        "up_name": (view.get("owner") or {}).get("name", ""),
        "duration": page.get("duration"),
        "url": f"https://www.bilibili.com/video/{bvid}/?p={part}",
        "subtitle_language": subtitle.get("lan"),
        "subtitle_type": subtitle.get("lan_doc"),
        "lines": lines,
    }


def markdown(data):
    lines = data["lines"]
    result = [
        f"# {data['title']}", "",
        f"分 P：{data['part']} · {data['part_title']}",
        f"字幕语言：{data['subtitle_language']}（{data['subtitle_type']}）", "",
        "## 完整字幕", ""
    ]
    for line in lines:
        text = line.get("text", "").strip()
        if text:
            result.append(text)
    return "\n".join(result) + "\n"


def save_video(output, data):
    output.mkdir(parents=True, exist_ok=True)
    stem = f"{data['bvid']}_p{data['part']}"
    (output / f"{stem}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = output / f"{stem}.md"
    md_path.write_text(markdown(data), encoding="utf-8")
    return md_path


SPACE_RE = re.compile(r"^https?://space\.bilibili\.com/(\d+)(?:/|$)")
MIXIN_TABLE = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]


def get_with_retry(browser, url, **kwargs):
    for attempt in range(3):
        response = browser.get(url, **kwargs)
        if response.status_code in (412, 429) and attempt < 2:
            time.sleep(2 * (attempt + 1))
            continue
        response.raise_for_status()
        return response


def resolve_mid(session, value):
    if value.isdigit():
        return value
    match = SPACE_RE.match(value)
    if match:
        return match.group(1)
    bvid, _ = parse_video(value)
    view = api_data(session, "/x/web-interface/view", {"bvid": bvid})
    mid = (view.get("owner") or {}).get("mid")
    if not mid:
        raise RuntimeError("视频信息中没有 UP 主 MID")
    return str(mid)


def latest_bvids(session, mid, count=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36",
        "Referer": f"https://space.bilibili.com/{mid}/video",
    }
    cookie = session.cookies.get("SESSDATA", domain=".bilibili.com")
    if cookie:
        headers["Cookie"] = f"SESSDATA={cookie}"
    no_proxy = {"http": None, "https": None}
    with browser_requests.Session(impersonate="chrome110") as browser:
        nav = get_with_retry(browser, "https://api.bilibili.com/x/web-interface/nav",
                             headers=headers, proxies=no_proxy, timeout=15)
        nav_data = nav.json().get("data") or {}
        wbi_img = nav_data.get("wbi_img") or {}
        if not wbi_img.get("img_url") or not wbi_img.get("sub_url"):
            raise RuntimeError("未取得 B 站 WBI 签名参数")
        lookup = "".join(url.rsplit("/", 1)[-1].split(".")[0]
                         for url in (wbi_img["img_url"], wbi_img["sub_url"]))
        key = "".join(lookup[i] for i in MIXIN_TABLE)[:32]
        params = {"mid": mid, "pn": 1, "ps": 30, "index": 1, "jsonp": "jsonp", "order": "pubdate", "wts": round(time.time())}
        query = urlencode(sorted(params.items()))
        params["w_rid"] = hashlib.md5((query + key).encode()).hexdigest()
        response = get_with_retry(browser, "https://api.bilibili.com/x/space/wbi/arc/search",
                                  params=params, headers=headers, proxies=no_proxy, timeout=15)
        result = response.json()
    if result.get("code") != 0:
        raise RuntimeError(f"B 站视频列表接口失败：{result.get('code')} {result.get('message')}")
    entries = ((result.get("data") or {}).get("list") or {}).get("vlist") or []
    bvids = []
    for entry in entries:
        candidate = entry.get("bvid", "")
        try:
            bvid, _ = parse_video(candidate)
        except ValueError:
            continue
        if bvid not in bvids:
            bvids.append(bvid)
        if len(bvids) == count:
            break
    if not bvids:
        raise RuntimeError("未取得该 UP 的视频列表；请检查 MID、登录状态或稍后重试")
    return bvids

