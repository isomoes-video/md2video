import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, writeFile, readFile, mkdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {validateSlides, parseSrt, buildTimeline} from '../video/data.mjs';

const slide = {slide_number: 1, layout: 'bullets', title: 'Title', bullets: ['First', 'Second']};
const script = [{slide_number: 1, narration: 'Narration'}];

test('validates scene layouts and narration mapping', () => {
  assert.doesNotThrow(() => validateSlides({slides: [slide]}, script));
  assert.throws(() => validateSlides({slides: [slide]}, []), /same slide count/);
  assert.throws(() => validateSlides({slides: [{...slide, slide_number: 2}]}, script), /consecutively/);
  assert.throws(() => validateSlides({slides: [{...slide, layout: 'unknown'}]}, script), /supported layout/);
  assert.throws(() => validateSlides({slides: [{...slide, bullets: []}]}, script), /bullets/);
  assert.throws(() => validateSlides({slides: [{...slide, layout: 'chart', bars: [{label: 'x', value: -1}]}]}, script), /bars/);
  assert.throws(() => validateSlides({slides: [slide]}, [{slide_number: 1, narration: ''}]), /narration/);
  assert.throws(() => validateSlides({slides: [{...slide, revealSeconds: [2, 1]}]}, script), /ordered/);
});

test('validates image layouts and local image paths', () => {
  const imageSlide = {slide_number: 1, layout: 'image', title: 'Figure', image: 'images/arch.png'};
  assert.doesNotThrow(() => validateSlides({slides: [imageSlide]}, script));
  assert.doesNotThrow(() => validateSlides({slides: [{...imageSlide, text: 'Intro', caption: 'Caption', alt: 'Alt'}]}, script));
  assert.throws(() => validateSlides({slides: [{...imageSlide, image: ''}]}, script), /image path/);
  assert.throws(() => validateSlides({slides: [{...imageSlide, image: '/abs/arch.png'}]}, script), /relative path/);
  assert.throws(() => validateSlides({slides: [{...imageSlide, image: 'images/../arch.png'}]}, script), /relative path/);
  assert.throws(() => validateSlides({slides: [{...imageSlide, image: 'images/arch.svg'}]}, script), /PNG, JPEG/);
  assert.throws(() => validateSlides({slides: [{...imageSlide, text: '   '}]}, script), /text/);
  assert.throws(() => validateSlides({slides: [{...imageSlide, caption: 'x'.repeat(81)}]}, script), /caption/);
  assert.throws(() => validateSlides({slides: [{...imageSlide, alt: 'x'.repeat(161)}]}, script), /alt/);
});

test('parses multiline Chinese SRT with BOM and Windows newlines', () => {
  const cues = parseSrt('\uFEFF1\r\n00:00:00,100 --> 00:00:01,250\r\n你好\r\n世界\r\n\r\n2\r\n00:00:01,300 --> 00:00:02,000\r\n字幕\r\n');
  assert.deepEqual(cues, [{start: 0.1, end: 1.25, text: '你好\n世界'}, {start: 1.3, end: 2, text: '字幕'}]);
  assert.deepEqual(parseSrt(''), []);
  assert.throws(() => parseSrt('1\ninvalid'), /timestamp/);
  assert.throws(() => parseSrt('1\n00:00:02,000 --> 00:00:01,000\nx'), /after/);
});

test('rounds audio duration up and adds gaps only between scenes', () => {
  const timeline = buildTimeline([slide, {...slide, slide_number: 2}], [1.001, 2], 30, 0.25);
  assert.equal(timeline[0].narrationFrames, 31);
  assert.equal(timeline[0].durationInFrames, 39);
  assert.equal(timeline[1].from, 39);
  assert.equal(timeline[1].durationInFrames, 60);
  assert.throws(() => buildTimeline([slide], [NaN], 30, 0), /duration/);
  assert.throws(() => buildTimeline([slide], [1], 0, 0), /fps/);
  assert.throws(() => buildTimeline([slide], [1], 30, -1), /gap/);
  assert.throws(() => buildTimeline([{...slide, revealSeconds: [1]}], [1], 30, 0), /exceeds/);
});

test('CLI prepares silent HTML and refuses missing narration by default', async () => {
  await mkdir('/tmp/opencode', {recursive: true});
  const workspace = await mkdtemp('/tmp/opencode/md2video-test-');
  await writeFile(path.join(workspace, 'slides.json'), JSON.stringify({slides: [slide]}));
  await writeFile(path.join(workspace, 'script.json'), JSON.stringify(script));
  assert.throws(() => execFileSync(process.execPath, ['scripts/render_video.mjs', '--workspace', workspace, '--prepare-only'], {stdio: 'pipe'}), /Missing narration audio/);
  execFileSync(process.execPath, ['scripts/render_video.mjs', '--workspace', workspace, '--silent', '--prepare-only'], {stdio: 'pipe'});
  const props = JSON.parse(await readFile(path.join(workspace, 'video-work/timeline.json'), 'utf8'));
  assert.equal(props.scenes[0].durationInFrames, 180);
  assert.equal(props.scenes[0].audio, undefined);
  assert.equal(props.width, 1920);
  const html = await readFile(path.join(workspace, 'video-work/index.html'), 'utf8');
  assert.match(html, /data-composition-id="md2video"/);
  assert.match(html, /data-duration="6"/);
  assert.doesNotMatch(html, /<audio/);
  assert.ok((await readFile(path.join(workspace, 'video-work/assets/gsap.min.js'))).length > 0);
});

test('CLI stages image files and fails when an image is missing', async () => {
  await mkdir('/tmp/opencode', {recursive: true});
  const workspace = await mkdtemp('/tmp/opencode/md2video-image-');
  await mkdir(path.join(workspace, 'images'));
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');
  await writeFile(path.join(workspace, 'images/diagram.png'), png);
  const imageSlide = {slide_number: 1, layout: 'image', title: 'Diagram', image: 'images/diagram.png', text: 'Intro text', caption: 'Caption'};
  await writeFile(path.join(workspace, 'slides.json'), JSON.stringify({slides: [imageSlide]}));
  await writeFile(path.join(workspace, 'script.json'), JSON.stringify(script));
  execFileSync(process.execPath, ['scripts/render_video.mjs', '--workspace', workspace, '--silent', '--prepare-only'], {stdio: 'pipe'});
  const props = JSON.parse(await readFile(path.join(workspace, 'video-work/timeline.json'), 'utf8'));
  assert.equal(props.scenes[0].image, 'assets/images/slide-01-diagram.png');
  assert.deepEqual(await readFile(path.join(workspace, 'video-work/assets/images/slide-01-diagram.png')), png);
  const html = await readFile(path.join(workspace, 'video-work/index.html'), 'utf8');
  assert.match(html, /src="assets\/images\/slide-01-diagram.png"/);
  assert.match(html, /class="figure-text">Intro text/);
  await writeFile(path.join(workspace, 'slides.json'), JSON.stringify({slides: [{...imageSlide, image: 'images/missing.png'}]}));
  assert.throws(() => execFileSync(process.execPath, ['scripts/render_video.mjs', '--workspace', workspace, '--silent', '--prepare-only'], {stdio: 'pipe'}), /Missing image/);
});
