// usage: node render.js data.json preview out_dir t1 t2 ...
//        node render.js data.json video out.mp4 [driveSeconds]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const FPS = 30;
(async () => {
  const [dataFile, mode, out, ...rest] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(__dirname, 'reel.html'));
  await page.addScriptTag({ content: 'window.__DATA = ' + fs.readFileSync(dataFile, 'utf8') + ';' });
  const drive = mode === 'video' && rest[0] ? parseFloat(rest[0]) : undefined;
  const dur = await page.evaluate(async drive => {
    for (const f of ['900 60px "Inter Display"', '800 40px "Inter Display"', '700 30px Inter', '600 30px Inter', '500 30px Inter', '40px "Noto Color Emoji"'])
      await document.fonts.load(f, 'Ab1🍺');
    return window.__reel.setData(window.__DATA, { drive });
  }, drive);
  const grab = async t => Buffer.from((await page.evaluate(t => { window.__reel.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');
  if (mode === 'preview') {
    fs.mkdirSync(out, { recursive: true });
    for (const a of rest) fs.writeFileSync(path.join(out, `prev_${a}.png`), await grab(parseFloat(a)));
    console.log('duration', dur.toFixed(1));
  } else {
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '19', '-preset', 'medium', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const n = Math.round(dur * FPS);
    const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      const buf = await grab(i / FPS);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 300 === 0) console.log(`frame ${i}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
    console.log('done', out, dur.toFixed(1) + 's');
  }
  await browser.close();
})();
