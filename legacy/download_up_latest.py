"""Download the latest N videos' subtitles for a specified Bilibili UP.

Usage:
    python download_up_latest.py <UID_or_Space_URL> [--count N]

Example:
    python download_up_latest.py 3706972811561025 --count 3
    python download_up_latest.py "https://space.bilibili.com/3706972811561025"
"""

import argparse
import hashlib
import json
import os
import re
import time
import urllib.parse
from pathlib import Path
from curl_cffi import requests

from preview_video import DEFAULT_SESSDATA, fetch_video, make_session, markdown

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]


def parse_mid(value: str) -> str:
    """Extract numeric UID from string or URL."""
    value = value.strip()
    match = re.search(r"space\.bilibili\.com/(\d+)", value)
    if match:
        return match.group(1)
    if value.isdigit():
        return value
    raise ValueError(f"无法识别 UP 主 UID：{value}，请输入纯数字 UID 或主页链接")


def get_mixin_key(orig: str) -> str:
    return "".join([orig[i] for i in MIXIN_KEY_ENC_TAB])[:32]


def enc_wbi(params: dict, img_key: str, sub_key: str) -> dict:
    mixin_key = get_mixin_key(img_key + sub_key)
    curr_time = round(time.time())
    params["wts"] = curr_time
    params = dict(sorted(params.items()))
    query = urllib.parse.urlencode(params)
    params["w_rid"] = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return params


def get_latest_videos(mid: str, count: int = 3, sessdata: str = DEFAULT_SESSDATA) -> list:
    session = requests.Session(impersonate="chrome110")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Referer": f"https://space.bilibili.com/{mid}/video",
        "Cookie": f"SESSDATA={sessdata}",
    }

    last_exc = None
    for attempt in range(3):
        try:
            # 1. 获取 WBI keys
            nav_res = session.get("https://api.bilibili.com/x/web-interface/nav", headers=headers, timeout=10).json()
            if nav_res.get("code") != 0 and nav_res.get("code") != -101:
                raise RuntimeError(f"获取导航信息失败：{nav_res}")

            img_url = nav_res["data"]["wbi_img"]["img_url"]
            sub_url = nav_res["data"]["wbi_img"]["sub_url"]
            img_key = img_url.rsplit("/", 1)[1].split(".")[0]
            sub_key = sub_url.rsplit("/", 1)[1].split(".")[0]

            # 2. 查询最新视频
            params = {
                "mid": mid,
                "ps": min(count, 30),
                "pn": 1,
                "order": "pubdate",
            }
            signed_params = enc_wbi(params, img_key, sub_key)

            res = session.get(
                "https://api.bilibili.com/x/space/wbi/arc/search",
                params=signed_params,
                headers=headers,
                timeout=10
            ).json()

            if res.get("code") != 0:
                raise RuntimeError(f"获取 UP 主空间视频失败：{res.get('message')}")

            vlist = res.get("data", {}).get("list", {}).get("vlist", [])
            return vlist[:count]
        except Exception as exc:
            last_exc = exc
            time.sleep(1)

    raise RuntimeError(f"获取视频列表重试失败：{last_exc}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="UP 主 UID 或空间链接 (例如 3706972811561025 或 https://space.bilibili.com/3706972811561025)")
    parser.add_argument("--count", "-n", type=int, default=3, help="下载最新视频数量 (默认: 3)")
    parser.add_argument("--output", "-o", type=Path, default=Path("previews"), help="字幕保存目录 (默认: previews)")
    args = parser.parse_args()

    mid = parse_mid(args.target)
    print(f"[*] 正在获取 UID={mid} 最新的 {args.count} 个视频...")

    try:
        videos = get_latest_videos(mid, count=args.count)
    except Exception as e:
        print(f"[-] 获取视频列表失败：{e}")
        return

    if not videos:
        print("[-] 未找到该 UP 主的任何视频。")
        return

    args.output.mkdir(parents=True, exist_ok=True)
    session = make_session()

    print(f"\n共找到 {len(videos)} 个最新视频，开始逐一提取字幕：\n")

    success_count = 0
    for idx, v in enumerate(videos, 1):
        bvid = v["bvid"]
        title = v["title"]
        print(f"[{idx}/{len(videos)}] 正在处理: {title} ({bvid})")

        try:
            data = fetch_video(session, bvid, part=1)
            stem = f"{bvid}_p1"
            md_path = args.output / f"{stem}.md"
            md_path.write_text(markdown(data), encoding="utf-8")
            print(f"    [+] 字幕已保存: {md_path}")
            success_count += 1
        except Exception as e:
            print(f"    [-] 提取字幕失败: {e}")

        time.sleep(1)

    print(f"\n==========================================")
    print(f"任务完成！成功下载 {success_count}/{len(videos)} 个视频的字幕")
    print(f"保存目录: {args.output.resolve()}")
    print(f"==========================================")


if __name__ == "__main__":
    main()
