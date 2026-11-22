// Rend une liste de plans (JSON) en clips MP4 à 24 i/s via Chromium headless + ffmpeg.
// usage : node render.js shots.json outdir [--stills]
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const { chromium } = require('playwright');
const [,, shotsFile, outDir, flag] = process.argv;
const FPS = 24, root = __dirname;
const server = http.createServer((req, res) => {
  const f = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (!f.startsWith(root) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': f.endsWith('.js') ? 'text/javascript' : 'text/html' }); fs.createReadStream(f).pipe(res);
});
(async () => {
  await new Promise((r) => server.listen(0, r));
  const port = server.address().port;
  const shots = JSON.parse(fs.readFileSync(shotsFile, 'utf8'));
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 720, height: 1280 } });
  page.on('pageerror', (e) => console.error('PAGE ERROR', e.message));
  await page.goto(`http://127.0.0.1:${port}/engine.html`);
  await page.waitForFunction(() => window.ENGINE_READY === true, null, { timeout: 60000 });
  fs.mkdirSync(outDir, { recursive: true });
  for (let i = 0; i < shots.length; i++) {
    const shot = shots[i]; const t0 = Date.now();
    await page.evaluate((s) => window.setupShot(s), shot);
    const n = flag === '--stills' ? 1 : Math.max(1, Math.round(shot.duration * FPS));
    if (flag === '--stills') {
      const url = await page.evaluate(([t]) => window.renderFrame(t, {}), [shot.duration * 0.5]);
      fs.writeFileSync(path.join(outDir, `still_${String(i).padStart(2, '0')}.jpg`), Buffer.from(url.split(',')[1], 'base64'));
      console.log(`still ${i} ${shot.set}`); continue;
    }
    const out = path.join(outDir, `anim_${String(i).padStart(2, '0')}.mp4`);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-vf', 'scale=1080:1920:flags=lanczos,format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-r', String(FPS), out]);
    for (let f = 0; f < n; f++) {
      const t = f / FPS;
      const mouths = {};
      for (const [id, env] of Object.entries(shot.mouths || {})) mouths[id] = env[Math.min(env.length - 1, f)] || 0;
      const url = await page.evaluate(([t, m]) => window.renderFrame(t, m), [t, mouths]);
      if (!ff.stdin.write(Buffer.from(url.split(',')[1], 'base64'))) await new Promise((r) => ff.stdin.once('drain', r));
    }
    ff.stdin.end(); await new Promise((r) => ff.on('close', r));
    console.log(`clip ${i} ${shot.set} ${n} images en ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  await browser.close(); server.close();
})().catch((e) => { console.error(e); process.exit(1); });
