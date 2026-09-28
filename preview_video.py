"""Extract one Bilibili video's complete subtitles without downloading media."""

import argparse
from pathlib import Path

import requests

from bilibili_core import fetch_video, make_session, parse_video, save_video


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", help="BV 号或 B 站视频链接，可带 ?p=分P编号")
    parser.add_argument("--output", type=Path, default=Path("previews"), help="输出目录")
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument("--cookies-from-browser", choices=["edge", "chrome"],
                      help="从已登录浏览器读取 B 站 Cookie")
    auth.add_argument("--prompt-sessdata", action="store_true",
                      help="在终端输入 SESSDATA；不回显，也不写入命令历史")
    args = parser.parse_args()
    try:
        bvid, part = parse_video(args.video)
        data = fetch_video(make_session(args.cookies_from_browser, args.prompt_sessdata), bvid, part)
        md_path = save_video(args.output, data)
        print(f"已保存 {len(data['lines'])} 条完整字幕：{md_path}")
    except (ValueError, RuntimeError, requests.RequestException) as exc:
        parser.exit(1, f"提取失败：{exc}\n")


if __name__ == "__main__":
    main()
