// usage: node render.js preview t1 t2 ...   |   node render.js video out.mp4
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const DIR = __dirname, FPS = 30;
(async () => {
  const [mode, ...args] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(DIR, 'reel.html'));
  const states = JSON.parse(fs.readFileSync(path.join(DIR, 'states.json'), 'utf8'));
  await page.evaluate(async s => {
    window.__reel.setStates(s);
    for (const f of ['900 60px "Inter Display"', '800 40px "Inter Display"', '700 30px Inter', '600 30px Inter', '500 30px Inter', 'italic 500 30px Inter', '40px "Noto Color Emoji"'])
      await document.fonts.load(f, 'Ab1🍺');
  }, states);
  const dur = await page.evaluate(() => window.__reel.DURATION);
  const grab = async t => Buffer.from((await page.evaluate(t => { window.__reel.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');
  if (mode === 'preview') {
    for (const a of args) fs.writeFileSync(path.join(DIR, `prev_${a}.png`), await grab(parseFloat(a)));
    console.log('duration', dur);
  } else {
    const out = args[0];
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const n = Math.round(dur * FPS);
    for (let i = 0; i < n; i++) {
      const buf = await grab(i / FPS);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 150 === 0) console.log(`frame ${i}/${n}`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
    console.log('done', out, dur.toFixed(1) + 's');
  }
  await browser.close();
})();
