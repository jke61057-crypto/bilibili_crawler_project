# B 站字幕提取 MVP

输入一个 BV 链接，或一个 UP 的空间链接 / MID，保存**完整字幕**。程序只读取 B 站视频信息、投稿列表和字幕 JSON，不下载音视频，也不进行语音转写。字幕不存在时会明确记录失败原因。

## 安装

建议 Python 3.11 或更新版本：

```powershell
python -m pip install -r requirements.txt
```

## 使用

单个视频（链接中的 `?p=2` 可指定分 P）：

```powershell
python preview_video.py "https://www.bilibili.com/video/BV1tMtm6nEzo/" --prompt-sessdata
```

UP 最新三个投稿；也可把参数换成空间链接或纯 MID：

```powershell
python preview_up.py "https://www.bilibili.com/video/BV1tMtm6nEzo/" --count 3 --prompt-sessdata
```

`--prompt-sessdata` 会在终端不回显地读取登录 Cookie，不将其写入源码或命令历史。已有 `BILIBILI_SESSDATA` 环境变量时可省略该选项。`--cookies-from-browser edge` 也是可选方式，但浏览器占用 Cookie 数据库时可能失败。不要在聊天、日志或代码中粘贴登录凭据。

输出默认在 `previews/`：每个视频的 `.md` 是完整字幕正文，`.json` 保留每句起止时间、分 P 和字幕语言。批量命令另写 `up_<MID>_latest<N>.json`，记录每条的成功或失败状态。批量只处理最新 N 个投稿；不会跳过无字幕视频去寻找更早的投稿。`download_up_latest.py` 是兼容旧命令的包装入口。

### 批量恢复与失败重试

若某次批量抓取中部分视频因网络或限流失败，可通过 `--retry-failed`（或 `--resume`）仅重试失败项，自动跳过已成功项且保留现有字幕文件：

```powershell
# 方式 1：指定 UP 与 --retry-failed
python preview_up.py "https://space.bilibili.com/<MID>" --count 3 --retry-failed

# 方式 2：直接传入历史批处理 JSON 文件
python preview_up.py previews/up_<MID>_latest3.json
```

## 代码结构

- `bilibili_core.py`：认证、B 站请求、UP 列表、字幕解析和结果保存。
- `preview_video.py`：单视频命令行入口。
- `preview_up.py`：UP 批量命令行入口，默认最新三条，`--count` 支持 1–30。
- `tests/`：不访问网络的核心行为测试。
- `bilibili_subtitles/`、`previews/`：已有数据及输出目录，未迁移或清空。

运行测试：

```powershell
python -B -m unittest discover -s tests -p "test_preview_*.py"
```
