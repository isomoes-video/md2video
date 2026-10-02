// Generate a self-contained, seekable HyperFrames composition from scene data.
export const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

export function createComposition({scenes, fps, width, height, accent, subtitles}) {
  const animations = [];
  const duration = scenes.reduce((sum, scene) => sum + scene.durationInFrames, 0) / fps;
  const markup = scenes.map((scene) => {
    const id = `scene-${scene.slide_number}`;
    const start = scene.from / fps;
    const length = scene.durationInFrames / fps;
    const count = scene.bullets?.length ?? scene.bars?.length ?? 1;
    const revealAt = (i) => scene.revealSeconds?.[i] !== undefined
      ? Math.round(scene.revealSeconds[i] * fps) / fps
      : Math.round(Math.min(fps * (0.55 + i * 0.7), scene.narrationFrames * (i + 1) / (count + 2))) / fps;
    const reveal = (name, html, at) => {
      const target = `${id}-${name}`;
      animations.push(`tl.fromTo('#${target}', {opacity: 0, y: 28}, {opacity: 1, y: 0, duration: 0.45, ease: 'none', immediateRender: false}, ${start + at});`);
      return `<div id="${target}" class="reveal">${html}</div>`;
    };
    let content = reveal('title', `<h1 class="${scene.layout === 'title' ? 'hero' : ''}">${escapeHtml(scene.title)}</h1>`, 0);
    if (scene.subtitle) content += reveal('subtitle', `<div class="subtitle">${escapeHtml(scene.subtitle)}</div>`, 0.2);
    if (scene.model && scene.slide_number === 1) content += reveal('model', `<div class="model">${escapeHtml(scene.model)}</div>`, 0.3);
    if (scene.layout === 'bullets') content += `<div class="bullets">${scene.bullets.map((text, i) => reveal(`bullet-${i}`, `<div class="bullet"><span class="accent">•</span><span>${escapeHtml(text)}</span></div>`, revealAt(i))).join('')}</div>`;
    if (scene.layout === 'chart') {
      const max = Math.max(1, ...scene.bars.map((bar) => bar.value));
      content += `<div class="bars">${scene.bars.map((bar, i) => {
        animations.push(`tl.fromTo('#${id}-bar-${i}', {width: '0%'}, {width: '${bar.value / max * 100}%', duration: 0.7, ease: 'none', immediateRender: false}, ${start + revealAt(i)});`);
        return reveal(`row-${i}`, `<div class="bar-label">${escapeHtml(bar.label)} <span class="accent">${bar.value}${escapeHtml(scene.unit)}</span></div><div class="bar-track"><div id="${id}-bar-${i}" class="bar"></div></div>`, revealAt(i));
      }).join('')}</div>`;
    }
    if (scene.layout === 'code') content += reveal('code', `<pre>${escapeHtml(scene.code)}</pre>`, revealAt(0));
    if (scene.layout === 'quote') content += reveal('quote', `<blockquote>${escapeHtml(scene.quote)}<div class="attribution">${escapeHtml(scene.attribution)}</div></blockquote>`, revealAt(0));
    if (subtitles) content += scene.cues.map((cue, i) => {
      const end = Math.min(cue.end, scene.narrationFrames / fps);
      if (cue.start >= end) return '';
      const target = `${id}-cue-${i}`;
      animations.push(`tl.set('#${target}', {opacity: 1}, ${start + cue.start});`, `tl.set('#${target}', {opacity: 0}, ${start + end});`);
      return `<div id="${target}" class="caption">${escapeHtml(cue.text)}</div>`;
    }).join('');
    const fade = Math.max(1, Math.min(Math.round(fps * 0.25), scene.durationInFrames - 1)) / fps;
    animations.push(`tl.fromTo('#${id}', {opacity: 1}, {opacity: 0, duration: ${fade}, ease: 'none', immediateRender: false}, ${start + length - fade});`);
    const audio = scene.audio ? `<audio id="${id}-audio" src="${escapeHtml(scene.audio)}" data-start="${start}" data-duration="${scene.narrationFrames / fps}" data-track-index="1"></audio>` : '';
    return `<section id="${id}" class="clip scene" data-start="${start}" data-duration="${length}" data-track-index="0"><div class="rule"></div>${content}<div class="counter">${scene.slide_number} / ${scenes.length}</div></section>${audio}`;
  }).join('\n');
  return `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>md2video</title>
<style>
@font-face { font-family: "Noto Sans CJK SC"; src: local("Noto Sans CJK SC"); }
@font-face { font-family: "Microsoft YaHei"; src: local("Microsoft YaHei"); }
* { box-sizing: border-box; }
html, body { margin: 0; width: ${width}px; height: ${height}px; overflow: hidden; }
#stage { position: relative; width: ${width}px; height: ${height}px; background: radial-gradient(ellipse at top right, #172b4d, #0b1220 70%); color: #f8fafc; font-family: "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; --accent: ${accent}; }
.scene { position: absolute; inset: 0; padding: 86px 110px 150px; }
.rule { height: 7px; width: 100px; background: var(--accent); margin-bottom: 35px; }
.reveal { opacity: 0; }
h1 { font-size: 64px; line-height: 1.2; margin: 0 0 25px; overflow-wrap: anywhere; }
h1.hero { font-size: 88px; }
.subtitle { font-size: 32px; color: #a8b5cd; margin-bottom: 35px; }
.model { font-size: 22px; color: #94a3b8; margin-top: 24px; }
.bullets { display: grid; gap: 23px; margin-top: 28px; }
.bullet { display: flex; gap: 24px; font-size: 38px; line-height: 1.4; }
.accent { color: var(--accent); }
.bars { display: grid; gap: 20px; margin-top: 24px; }
.bar-label { font-size: 27px; margin-bottom: 7px; }
.bar-track { height: 34px; background: #1e293b; border-radius: 8px; }
.bar { height: 100%; width: 0; background: var(--accent); border-radius: 8px; }
pre { font-size: 30px; line-height: 1.45; padding: 32px; border-radius: 18px; background: #162137; white-space: pre-wrap; overflow-wrap: anywhere; color: #c4e4ff; }
blockquote { margin: 55px 0; border-left: 8px solid var(--accent); padding-left: 40px; font-size: 48px; line-height: 1.5; white-space: pre-line; }
.attribution { font-size: 26px; color: #94a3b8; margin-top: 25px; }
.counter { position: absolute; bottom: 36px; right: 70px; font-size: 23px; color: #94a3b8; }
.caption { opacity: 0; position: absolute; bottom: 82px; left: 100px; right: 100px; text-align: center; white-space: pre-line; font-size: 32px; line-height: 1.4; padding: 12px 22px; border-radius: 12px; background: rgba(0,0,0,0.8); }
</style></head><body>
<div id="stage" data-composition-id="md2video" data-start="0" data-duration="${duration}" data-width="${width}" data-height="${height}" data-fps="${fps}">
${markup}
</div>
<script src="assets/gsap.min.js"></script>
<script>
const tl = gsap.timeline({paused: true});
${animations.join('\n')}
// Keep the animation clock alive through the final frame.
tl.to({}, {duration: ${duration}}, 0);
window.__timelines = {md2video: tl};
</script></body></html>\n`;
}
