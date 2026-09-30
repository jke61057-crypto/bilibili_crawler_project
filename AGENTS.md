# Agent Guidelines & Project Rules

## 🚨 HIGHEST PRIORITY RULE: Prioritize Subtitles, Strictly No Audio/Video Downloads

When working on, interacting with, or extending this project:

1. **Subtitles First (最高优先级)**:
   - **ALWAYS** directly read and extract pre-existing subtitles from Bilibili API (`/x/player/wbi/v2` subtitle JSON, CC subtitles, or official AI subtitles).
   - Subtitle extraction is instantaneous, requires virtually zero bandwidth, and natively includes high-precision timestamps and segmentations.

2. **Strictly Forbidden: Downloading Media (严禁下载音视频)**:
   - **DO NOT** download audio streams (e.g. `.mp3`, `.m4a`, `.aac`) or video streams from Bilibili or the internet.
   - **DO NOT** invoke media downloaders (e.g., `yt-dlp` media download methods, ffmpeg stream dumps, or requests to streaming CDNs).
   - *Note on dependencies*: `yt-dlp` in `requirements.txt` is **only** used for browser cookie extraction (`extract_cookies_from_browser`), NEVER for downloading audio/video.

3. **Strictly Forbidden: Unsolicited Speech-to-Text (严禁擅自使用语音转写)**:
   - **DO NOT** run local or remote speech-to-text / ASR models (such as OpenAI Whisper, SenseVoice, etc.).
   - If a video lacks subtitles, report it explicitly as `此分 P 没有可用字幕`—do not fall back to downloading audio for transcription.

4. **Preserve MVP Simplicity**:
   - Keep operations lightweight, surgical, and centered on structured subtitle JSON/Markdown processing.
