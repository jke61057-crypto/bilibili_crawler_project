(async function() {
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    console.log("🚀 开始极速一对一扫描与修正字幕...");

    let videos = [];
    let seenBvids = new Set();

    // 翻页提取所有视频
    while (true) {
        window.scrollTo(0, document.body.scrollHeight);
        await sleep(2000); 

        let cards = document.querySelectorAll('.bili-video-card, .small-item, li.v-item, .upload-video-item');
        for (let card of cards) {
            let titleEl = card.querySelector('.bili-video-card__info--tit, a.title, h3[title], a[title]');
            let linkEl = card.querySelector('a[href*="/video/BV"]');
            if (!titleEl || !linkEl) continue;

            let title = titleEl.getAttribute('title') || titleEl.innerText || '';
            title = title.replace(/\n/g, '').trim();

            let href = linkEl.getAttribute('href') || '';
            let bvidMatch = href.match(/BV[a-zA-Z0-9]+/);

            if (title && title.length > 2 && bvidMatch) {
                let bvid = bvidMatch[0];
                if (!seenBvids.has(bvid)) {
                    seenBvids.add(bvid);
                    videos.push({ title, bvid });
                }
            }
        }

        let nextBtn = Array.from(document.querySelectorAll('button, li, a, span')).find(el => el.textContent.trim() === '下一页');
        if (nextBtn && !nextBtn.disabled && !nextBtn.className.includes('disabled')) {
            nextBtn.click();
            await sleep(3500); 
        } else {
            break;
        }
    }

    console.log(`📋 页面共提取到 ${videos.length} 个视频。开始自动下载/覆盖修正字幕...`);

    let downloadCount = 0;
    for (let i = 0; i < videos.length; i++) {
        let v = videos[i];
        try {
            let viewRes = await fetch(`https://api.bilibili.com/x/web-interface/view?bvid=${v.bvid}`, { credentials: 'include' });
            let viewData = await viewRes.json();
            if (viewData.code !== 0 || !viewData.data) continue;

            let cid = viewData.data.cid;
            let realTitle = viewData.data.title; // 直接以官方 API 返回的真实标题为准！

            let playerRes = await fetch(`https://api.bilibili.com/x/player/v2?bvid=${v.bvid}&cid=${cid}`, { credentials: 'include' });
            let playerData = await playerRes.json();
            let subtitles = playerData.data?.subtitle?.subtitles || [];

            if (subtitles.length > 0) {
                let targetSub = subtitles.find(s => s.lan === 'zh-CN' || s.lan === 'ai-zh' || s.lan.includes('zh')) || subtitles[0];
                let subUrl = targetSub.subtitle_url;
                if (subUrl.startsWith('//')) subUrl = 'https:' + subUrl;

                let subRes = await fetch(subUrl); // 不加 credentials 避免 CORS
                let subJson = await subRes.json();
                let text = (subJson.body || []).map(item => item.content).join('\n');

                if (text.trim().length > 100) {
                    let blob = new Blob([text], { type: "text/plain;charset=utf-8" });
                    let a = document.createElement("a");
                    a.href = URL.createObjectURL(blob);
                    let safeTitle = realTitle.replace(/[\\/:*?"<>|]/g, '_');
                    a.download = `${safeTitle}_${v.bvid}.txt`;
                    a.click();
                    downloadCount++;
                    console.log(`[${downloadCount}] ✅ 成功下载权威字幕: ${safeTitle} (${v.bvid})`);
                }
            }
        } catch (e) {
            console.error(`❌ 处理出错: ${v.bvid}`, e);
        }
        await sleep(1200); 
    }
    console.log(`🎊 极速下载修正完成！共生成 ${downloadCount} 个权威字幕文件。`);
})();
