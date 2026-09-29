"""Lightweight index generator for downloaded Bilibili videos.

Indexes:
1. Video Title (视频标题)
2. BV ID (BV 号)
3. UP Name (UP 主名称)
4. Relevant Tags (相关标签)

Outputs:
- INDEX.md: Human-readable Markdown index table
- index.json: Machine-readable JSON index
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import time

from bilibili_core import get_json, make_session


def load_cache(cache_file: Path) -> dict:
    if cache_file.is_file():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache_file: Path, cache: dict):
    cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_video_meta(session, bvid: str, cache: dict, offline: bool = False) -> dict:
    """Resolve up_name and tags for a given BVID, with caching."""
    if bvid in cache and cache[bvid].get("up_name") and cache[bvid].get("tags"):
        return cache[bvid]

    cached = cache.get(bvid, {})
    meta = {
        "up_name": cached.get("up_name", ""),
        "tags": cached.get("tags", []),
        "title": cached.get("title", "")
    }
    if offline or not session:
        return meta

    try:
        # Fetch view info (UP name and title) if missing
        if not meta["up_name"]:
            res_view = get_json(session, "https://api.bilibili.com/x/web-interface/view", params={"bvid": bvid})
            data = res_view.get("data") or {}
            if isinstance(data, dict):
                meta["up_name"] = (data.get("owner") or {}).get("name", "")
                if not meta["title"]:
                    meta["title"] = data.get("title", "")

        # Fetch tags if missing
        if not meta["tags"]:
            res_tags = get_json(session, "https://api.bilibili.com/x/tag/archive/tags", params={"bvid": bvid})
            tag_list = res_tags.get("data") or []
            if isinstance(tag_list, list):
                meta["tags"] = [t.get("tag_name") for t in tag_list if isinstance(t, dict) and t.get("tag_name")]

        cache[bvid] = meta
        time.sleep(0.15)
    except Exception as exc:
        print(f"  [-] 查询 {bvid} 元数据提示: {exc}")

    return meta


def build_index(dir_path: Path, output_md: Path, output_json: Path, offline: bool = False):
    dir_path = Path(dir_path)
    cache_file = dir_path / ".index_cache.json"
    cache = load_cache(cache_file)
    session = make_session() if not offline else None

    # Also pre-populate known UPs from batch manifest files (e.g. up_2137589551_latest30.json)
    known_mid_names = {
        "2137589551": "李大霄",
        "11473291": "笨笨的韭菜",
        "1140672573": "小王Albert",
    }
    for manifest_file in dir_path.glob("up_*_latest*.json"):
        mid = manifest_file.stem.split("_")[1]
        up_name = known_mid_names.get(mid, "")
        try:
            for item in json.loads(manifest_file.read_text(encoding="utf-8")):
                bvid = item.get("bvid")
                if bvid and bvid not in cache:
                    cache[bvid] = {"up_name": up_name, "tags": [], "title": item.get("title", "")}
                elif bvid and not cache[bvid].get("up_name"):
                    cache[bvid]["up_name"] = up_name
        except Exception:
            pass

    json_files = sorted(dir_path.glob("BV*_p*.json"))
    records = []
    seen_bvids = set()

    print(f"正在扫描 {dir_path} 中的视频文件...")
    for jf in json_files:
        try:
            item = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue

        bvid = item.get("bvid")
        if not bvid or bvid in seen_bvids:
            continue
        seen_bvids.add(bvid)

        title = item.get("title", "")
        up_name = item.get("up_name", "")
        tags = item.get("tags") or []

        # Check cache
        cached = cache.get(bvid, {})
        if not up_name and cached.get("up_name"):
            up_name = cached["up_name"]
        if not tags and cached.get("tags"):
            tags = cached["tags"]

        # If still missing, query API
        if not up_name or not tags:
            meta = resolve_video_meta(session, bvid, cache, offline=offline)
            if not up_name:
                up_name = meta.get("up_name", "")
            if not tags:
                tags = meta.get("tags", [])

        stem = f"{bvid}_p{item.get('part', 1)}"
        md_file = dir_path / f"{stem}.md"
        rel_md = md_file.as_posix() if md_file.is_file() else ""

        records.append({
            "bvid": bvid,
            "title": title,
            "up_name": up_name or "未知UP主",
            "tags": tags,
            "subtitle_path": rel_md,
            "lines_count": len(item.get("lines", []))
        })

    # Save cache
    save_cache(cache_file, cache)

    # Sort records by UP Name, then Title
    records.sort(key=lambda r: (r["up_name"], r["title"]))

    # Output JSON index
    output_json.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成结构化索引: {output_json} (共 {len(records)} 条)")

    # Output Markdown index
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    md_lines = [
        "# 视频内容索引 (Video Index)",
        "",
        f"> **收录总数**：{len(records)} 个视频 | **更新时间**：{now_str}",
        "",
        "| 序号 | 视频标题 | BV 号 | UP 主 | 相关标签 | 字幕文件 |",
        "| :---: | :--- | :---: | :--- | :--- | :---: |"
    ]

    for idx, r in enumerate(records, 1):
        tag_str = " ".join([f"`{t}`" for t in r["tags"][:5]]) if r["tags"] else "-"
        sub_link = f"[查看字幕]({r['subtitle_path']})" if r["subtitle_path"] else "-"
        title_esc = r["title"].replace("|", "\\|")
        md_lines.append(f"| {idx} | {title_esc} | `{r['bvid']}` | {r['up_name']} | {tag_str} | {sub_link} |")

    md_lines.append("")
    output_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"已生成 Markdown 索引看板: {output_md}")
    return records


def main():
    parser = argparse.ArgumentParser(description="生成视频标题、BV号、UP主名称及标签的轻量化索引")
    parser.add_argument("--dir", default=Path("previews"), type=Path, help="待扫描的字幕输出目录（默认 previews）")
    parser.add_argument("--output-md", default=Path("INDEX.md"), type=Path, help="生成的 Markdown 索引文件路径")
    parser.add_argument("--output-json", default=Path("index.json"), type=Path, help="生成的 JSON 索引文件路径")
    parser.add_argument("--offline", action="store_true", help="完全离线模式（仅使用本地已有缓存）")
    args = parser.parse_args()

    build_index(args.dir, args.output_md, args.output_json, offline=args.offline)


if __name__ == "__main__":
    main()
