import os
import json
import requests

SESSDATA = ""
MID = "3706972811561025"
SUB_DIR = "bilibili_subtitles"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Cookie': f'SESSDATA={SESSDATA}'
}

def clean_and_check():
    # 1. 扫描本地已被确认正确的字幕文件及其 BV 号
    existing_files = [f for f in os.listdir(SUB_DIR) if f.endswith('.txt')]
    valid_local_bvids = set()
    
    print(f"--- [第一阶段] 扫描并清理本地字幕 ---")
    for fname in existing_files:
        fpath = os.path.join(SUB_DIR, fname)
        size = os.path.getsize(fpath)
        # 如果文件太小（小于 500 字节，通常是无字幕、只有一两句话或报错内容），判定为不符合要求并删除
        if size < 500:
            print(f"[-] 删除垃圾/无效字幕文件 ({size} bytes): {fname}")
            os.remove(fpath)
            continue
            
        # 提取 BV 号
        bvid = fname.split('_')[-1].replace('.txt', '')
        if bvid.startswith('BV'):
            valid_local_bvids.add(bvid)

    print(f"\n[+] 本地当前保留的【有效且正确】字幕文件数: {len(valid_local_bvids)} 个\n")

    # 2. 搜索获取 UP 主的所有视频清单
    print(f"--- [第二阶段] 获取 UP 主全部视频清单并对比 ---")
    all_videos = []
    seen = set()
    
    # 尝试使用搜索 API 获取
    for page in range(1, 10):
        url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=%E5%9C%9F%E8%B1%86%E7%9C%8B%E8%B4%A2%E6%8A%A5&page={page}"
        try:
            res = requests.get(url, headers=headers, timeout=10).json()
            if res.get('code') == 0 and res.get('data', {}).get('result'):
                items = res['data']['result']
                for item in items:
                    if str(item.get('mid')) == MID:
                        bvid = item['bvid']
                        if bvid not in seen:
                            seen.add(bvid)
                            # 清理 HTML 标签
                            title = item['title'].replace('<em class="keyword">', '').replace('</em>', '').replace('&quot;', '"')
                            all_videos.append({'bvid': bvid, 'title': title})
        except Exception as e:
            pass

    print(f"[+] 通过 API 检索到 UP 主的视频总数: {len(all_videos)} 个")

    # 3. 计算缺失清单
    missing_videos = []
    for v in all_videos:
        if v['bvid'] not in valid_local_bvids:
            missing_videos.append(v)

    print(f"\n================ 最终统计结果 ================")
    print(f"【已被正确保存的有效字幕数量】: {len(valid_local_bvids)} 个")
    print(f"【最新的缺失视频数量】: {len(missing_videos)} 个\n")

    if missing_videos:
        print("以下是【最新缺失视频清单】：")
        for i, mv in enumerate(missing_videos, 1):
            print(f"{i}. [{mv['bvid']}] {mv['title']}")
            
    # 输出到 json 文件方便查看
    with open("missing_videos.json", "w", encoding="utf-8") as f:
        json.dump(missing_videos, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    clean_and_check()
