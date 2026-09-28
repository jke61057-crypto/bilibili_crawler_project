import os
import re
import requests
import json

SESSDATA = ""

SUB_DIR = "bilibili_subtitles"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Cookie': f'SESSDATA={SESSDATA}'
}

def validate_and_fix_subtitles():
    if not os.path.exists(SUB_DIR):
        print(f"目录 {SUB_DIR} 不存在！")
        return

    files = [f for f in os.listdir(SUB_DIR) if f.endswith('.txt')]
    print(f"正在扫描并校验 {len(files)} 个本地字幕文件...\n")
    
    deleted_count = 0
    fixed_count = 0
    valid_bvids = set()

    for filename in files:
        filepath = os.path.join(SUB_DIR, filename)
        
        # 匹配文件名中的 BV 号
        match = re.search(r'_(BV[a-zA-Z0-9]+)\.txt$', filename)
        if not match:
            print(f"[!] 无法识别文件名中的 BV 号，删除异常文件: {filename}")
            os.remove(filepath)
            deleted_count += 1
            continue
            
        bvid = match.group(1)
        
        # 请求 B 站官方接口获取真实的视频信息
        try:
            view_res = requests.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", headers=headers, timeout=10)
            data = view_res.json()
            if data.get('code') != 0:
                print(f"[-] BV 号无效或已被删除 ({bvid})，删除本地文件: {filename}")
                os.remove(filepath)
                deleted_count += 1
                continue
                
            real_title = data['data']['title']
            cid = data['data']['cid']
            
            # 重新校验字幕
            player_res = requests.get(f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}", headers=headers, timeout=10)
            player_data = player_res.json()
            subtitles = player_data.get('data', {}).get('subtitle', {}).get('subtitles', [])
            
            if not subtitles:
                print(f"[-] 真实 API 确认该视频无字幕 ({real_title})，删除错误文件: {filename}")
                os.remove(filepath)
                deleted_count += 1
                continue
                
            # 找到正确的字幕地址
            target_sub = None
            for s in subtitles:
                if s.get('lan') in ['zh-CN', 'ai-zh'] or 'zh' in s.get('lan', ''):
                    target_sub = s
                    break
            if not target_sub:
                target_sub = subtitles[0]
                
            sub_url = target_sub.get('subtitle_url', '')
            if sub_url.startswith('//'):
                sub_url = 'https:' + sub_url
                
            sub_res = requests.get(sub_url, timeout=10)
            sub_json = sub_res.json()
            text = "\n".join([item['content'] for item in sub_json.get('body', [])])
            
            if len(text.strip()) < 10:
                print(f"[-] 字幕内容过短/空文件 ({real_title})，删除: {filename}")
                os.remove(filepath)
                deleted_count += 1
                continue
                
            # 清理安全的文件名
            safe_real_title = "".join([c for c in real_title if c.isalpha() or c.isdigit() or c==' ' or c=='_']).rstrip()
            correct_filename = f"{safe_real_title}_{bvid}.txt"
            correct_filepath = os.path.join(SUB_DIR, correct_filename)
            
            # 如果文件名不一致或内容损坏，更新并修正文件名
            if filename != correct_filename or os.path.getsize(filepath) < 100:
                with open(correct_filepath, "w", encoding="utf-8") as f:
                    f.write(text)
                if filename != correct_filename:
                    print(f"[+] 修正错位标题文件名:\n    原文件名: {filename}\n    修正后名: {correct_filename}")
                    os.remove(filepath)
                else:
                    print(f"[+] 重新修复并覆盖写入正确的字幕内容: {correct_filename}")
                fixed_count += 1
            else:
                # 再次确认内容是否正确，写入最新抓取的权威内容
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(text)
                valid_bvids.add(bvid)
                
        except Exception as e:
            print(f"[!] 校验 {filename} 时发生异常: {e}")
            
    print(f"\n================ 校验完成 ================")
    print(f"删除不正确/错误字幕文件: {deleted_count} 个")
    print(f"修正/重新写入字幕文件: {fixed_count} 个")
    print(f"当前保留的绝对正确的字幕文件: {len(valid_bvids)} 个")

if __name__ == "__main__":
    validate_and_fix_subtitles()
