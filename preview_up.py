"""Extract complete subtitles for an UP account's newest videos without media."""

import argparse
import json
from pathlib import Path

import requests
from curl_cffi import requests as browser_requests

from bilibili_core import fetch_video, latest_bvids, make_session, resolve_mid, save_video


def process_batch(session, up_target, count=3, output=Path("previews"), retry_failed=False):
    up_path = Path(up_target)
    is_json_input = up_path.is_file() and up_path.suffix.lower() == ".json"
    retry_mode = retry_failed or is_json_input

    output = Path(output)
    if is_json_input:
        manifest_path = up_path
        if output == Path("previews"):
            output = manifest_path.parent
        previous_results = json.loads(manifest_path.read_text(encoding="utf-8"))
        bvids = [item["bvid"] for item in previous_results if isinstance(item, dict) and "bvid" in item]
        if not bvids:
            raise ValueError(f"文件 {up_target} 中没有有效的视频记录")
    else:
        mid = resolve_mid(session, up_target)
        manifest_path = output / f"up_{mid}_latest{count}.json"
        if retry_mode and manifest_path.is_file():
            previous_results = json.loads(manifest_path.read_text(encoding="utf-8"))
            bvids = [item["bvid"] for item in previous_results if isinstance(item, dict) and "bvid" in item]
            if not bvids:
                bvids = latest_bvids(session, mid, count)
        else:
            previous_results = []
            bvids = latest_bvids(session, mid, count)

    output.mkdir(parents=True, exist_ok=True)
    previous_by_bvid = {
        item["bvid"]: item
        for item in previous_results
        if isinstance(item, dict) and "bvid" in item
    }
    results = []
    for bvid in bvids:
        prev = previous_by_bvid.get(bvid)
        if retry_mode and prev and prev.get("status") == "ok":
            stem = f"{bvid}_p1"
            if (output / f"{stem}.json").is_file() and (output / f"{stem}.md").is_file():
                results.append(prev)
                print(f"已跳过（已成功）：{bvid} · {prev.get('lines', 0)} 条字幕")
                continue

        try:
            data = fetch_video(session, bvid, 1)
            save_video(output, data)
            results.append({"bvid": bvid, "status": "ok", "title": data["title"], "lines": len(data["lines"])})
            print(f"已保存：{bvid} · {len(data['lines'])} 条字幕")
        except (ValueError, RuntimeError, requests.RequestException) as exc:
            results.append({"bvid": bvid, "status": "error", "reason": str(exc)})
            print(f"提取失败：{bvid} · {exc}")

    manifest_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("up", help="UP 空间链接、MID、该 UP 的任意 BV 链接，或历史批量结果 JSON 路径")
    parser.add_argument("--count", "-n", type=int, default=3, help="提取最新投稿数量，1–30（默认 3）")
    parser.add_argument("--output", type=Path, default=Path("previews"), help="输出目录")
    parser.add_argument("--retry-failed", "--resume", action="store_true",
                        help="仅重试失败项：从已有结果 JSON 中恢复，跳过已成功的项")
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument("--cookies-from-browser", choices=["edge", "chrome"])
    auth.add_argument("--prompt-sessdata", action="store_true")
    args = parser.parse_args()
    try:
        if not 1 <= args.count <= 30:
            raise ValueError("--count 必须在 1 到 30 之间")
        session = make_session(args.cookies_from_browser, args.prompt_sessdata)
        results = process_batch(session, args.up, count=args.count, output=args.output,
                                retry_failed=args.retry_failed)
        if not any(item["status"] == "ok" for item in results):
            parser.exit(1, "所选视频均未成功提取字幕；详情见批量结果 JSON\n")
    except (ValueError, RuntimeError, requests.RequestException, browser_requests.RequestsError) as exc:
        parser.exit(1, f"获取 UP 视频列表失败：{exc}\n")


if __name__ == "__main__":
    main()
