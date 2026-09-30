# Gemini / Antigravity Rules

<!-- Inherits all rules from AGENTS.md -->

## 🚨 HIGHEST PRIORITY RULE: Prioritize Subtitles, Strictly No Audio/Video Downloads

- **Subtitles First (最高优先级)**: ALWAYS directly read and extract pre-existing subtitles from Bilibili API (`/x/player/wbi/v2` subtitle JSON, CC subtitles, or official AI subtitles).
- **Strictly Forbidden: Downloading Media (严禁下载音视频)**: DO NOT download audio streams (e.g. `.mp3`, `.m4a`, `.aac`) or video streams from Bilibili or the internet.
- **Strictly Forbidden: Speech-to-Text / Whisper (严禁擅自使用语音转写)**: DO NOT run Whisper or transcription pipelines. If subtitles do not exist, report it explicitly.
- **`yt-dlp` Usage**: `yt-dlp` in `requirements.txt` is ONLY for extracting cookies from local browsers, NEVER for downloading media streams.
