import test from 'node:test';
import assert from 'node:assert/strict';
import {runInNewContext} from 'node:vm';
import {createComposition, escapeHtml} from '../video/html.mjs';
import {buildTimeline} from '../video/data.mjs';

const slides = [
  {slide_number: 1, layout: 'title', title: '<script>alert("x")</script>', subtitle: '你好', model: 'Test model'},
  {slide_number: 2, layout: 'bullets', title: 'Bullets', bullets: ['one & two', 'three'], revealSeconds: [0.3, 1.1]},
  {slide_number: 3, layout: 'chart', title: 'Chart', bars: [{label: 'zero', value: 0}, {label: 'full', value: 100}], unit: '%'},
  {slide_number: 4, layout: 'code', title: 'Code', code: '</script><img src=x onerror=alert(1)>'},
  {slide_number: 5, layout: 'quote', title: 'Quote', quote: 'hello\nworld', attribution: 'Author'},
];
const props = () => ({
  scenes: buildTimeline(slides, slides.map(() => 3), 30, 0.25).map((scene, i) => ({
    ...scene, audio: `audio/slide-0${i + 1}.mp3`, cues: [{start: 0.1, end: 1.2, text: '字幕 <test>'}],
  })),
  fps: 30, width: 1920, height: 1080, accent: '#38bdf8', subtitles: true,
});

test('HTML composition preserves all layouts and escapes user content', () => {
  const html = createComposition(props());
  assert.equal(escapeHtml('&<>"\''), '&amp;&lt;&gt;&quot;&#39;');
  assert.match(html, /&lt;script&gt;alert\(&quot;x&quot;\)&lt;\/script&gt;/);
  assert.doesNotMatch(html, /<img src=x/);
  assert.match(html, /one &amp; two/);
  assert.match(html, /class="bar-track"/);
  assert.match(html, /<pre>&lt;\/script&gt;/);
  assert.match(html, /<blockquote>hello\nworld/);
  assert.match(html, /Test model/);
  assert.equal((html.match(/class="clip scene"/g) ?? []).length, 5);
  assert.match(html, /src="assets\/gsap.min.js"/);
  assert.doesNotMatch(html, /https?:\/\//);
});

test('schedules audio, reveals, captions, and fades on a paused global clock', () => {
  const input = props();
  const html = createComposition(input);
  const calls = [];
  const timeline = Object.fromEntries(['fromTo', 'set', 'to'].map((method) => [method, (...args) => {calls.push({method, args});}]));
  const window = {};
  runInNewContext(html.match(/<script>\n([\s\S]*?)<\/script>/)[1], {
    window, gsap: {timeline: (options) => {assert.equal(options.paused, true); return timeline;}},
  });
  assert.equal(window.__timelines.md2video, timeline);
  const secondStart = input.scenes[1].from / 30;
  assert.match(html, new RegExp(`id="scene-2-audio"[^>]*data-start="${secondStart}" data-duration="3"`));
  const bullet = calls.find((call) => call.args[0] === '#scene-2-bullet-0');
  assert.equal(bullet.args[3], secondStart + 0.3);
  assert.equal(bullet.args[2].immediateRender, false);
  const cue = calls.filter((call) => call.args[0] === '#scene-2-cue-0');
  assert.equal(cue[0].args[2], secondStart + 0.1);
  assert.equal(cue[1].args[2], secondStart + 1.2);
  const fade = calls.find((call) => call.args[0] === '#scene-2');
  assert.equal(fade.args[3] + fade.args[2].duration, input.scenes[2].from / 30);
  assert.equal(calls.at(-1).args[1].duration, 482 / 30);
});

test('disables captions and clips late cues to narration duration', () => {
  const input = props();
  assert.doesNotMatch(createComposition({...input, subtitles: false}), /id="scene-1-cue-0"/);
  input.scenes[0].cues = [{start: 2.5, end: 8, text: 'clipped'}, {start: 4, end: 5, text: 'past audio'}];
  const html = createComposition(input);
  assert.match(html, /tl.set\('#scene-1-cue-0', \{opacity: 0\}, 3\);/);
  assert.doesNotMatch(html, /past audio/);
});
