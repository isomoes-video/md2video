import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, writeFile, readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';

// Explicitly opt in: this test launches a browser and requires FFmpeg/FFprobe.
test('renders scheduled audio and captions to a frame-complete H.264/AAC MP4', {
  skip: process.env.RUN_VIDEO_RENDER_TESTS !== '1', timeout: 120000,
}, async () => {
  const workspace = await mkdtemp('/tmp/opencode/md2video-render-');
  await mkdir(path.join(workspace, 'audio'));
  await writeFile(path.join(workspace, 'slides.json'), JSON.stringify({slides: [
    {slide_number: 1, layout: 'title', title: '音频与字幕测试', subtitle: 'First tone: 440 Hz'},
    {slide_number: 2, layout: 'bullets', title: '第二个场景', bullets: ['Second tone: 880 Hz', '字幕按时间显示']},
  ]}));
  await writeFile(path.join(workspace, 'script.json'), JSON.stringify([
    {slide_number: 1, narration: 'First'}, {slide_number: 2, narration: 'Second'},
  ]));
  for (const [index, frequency] of [440, 880].entries()) {
    const audio = path.join(workspace, `audio/slide-0${index + 1}.mp3`);
    execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i', `sine=frequency=${frequency}:duration=1.5`, '-c:a', 'libmp3lame', audio]);
    await writeFile(audio.replace('.mp3', '.srt'), `1\n00:00:00,200 --> 00:00:01,000\n场景 ${index + 1} 字幕\n`);
  }
  const cli = ['scripts/render_video.mjs', '--workspace', workspace];
  execFileSync(process.execPath, cli, {stdio: 'pipe', timeout: 110000});
  const output = path.join(workspace, 'video.mp4');
  const probe = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_streams', '-show_format', '-of', 'json', output], {encoding: 'utf8'}));
  const timeline = JSON.parse(await readFile(path.join(workspace, 'video-work/timeline.json'), 'utf8'));
  const video = probe.streams.find((stream) => stream.codec_type === 'video');
  assert.equal(video.codec_name, 'h264');
  assert.equal(video.width, 1920);
  assert.equal(video.height, 1080);
  assert.equal(video.pix_fmt, 'yuv420p');
  assert.equal(probe.streams.find((stream) => stream.codec_type === 'audio').codec_name, 'aac');
  const expectedFrames = timeline.scenes.reduce((sum, scene) => sum + scene.durationInFrames, 0);
  assert.equal(Number(video.nb_frames), expectedFrames);
  // Decode the final mix and confirm the gap is silent and tones stay ordered.
  const pcm = execFileSync('ffmpeg', ['-v', 'error', '-i', output, '-f', 'f32le', '-ac', '1', '-ar', '8000', 'pipe:1']);
  const sample = (i) => pcm.readFloatLE(i * 4);
  const rms = (start, end) => {
    let sum = 0;
    const first = Math.floor(start * 8000), last = Math.floor(end * 8000);
    for (let i = first; i < last; i++) sum += sample(i) ** 2;
    return Math.sqrt(sum / (last - first));
  };
  const secondStart = timeline.scenes[1].from / timeline.fps;
  assert.ok(rms(0.3, 0.8) > 0.01);
  assert.ok(rms(secondStart + 0.3, secondStart + 0.8) > 0.01);
  assert.ok(rms(secondStart - 0.15, secondStart - 0.05) < 0.001);
  const frequency = (start) => {
    let crossings = 0;
    const first = Math.floor(start * 8000), last = first + 1600;
    for (let i = first + 1; i < last; i++) if (sample(i - 1) <= 0 && sample(i) > 0) crossings++;
    return crossings / 0.2;
  };
  assert.ok(Math.abs(frequency(0.3) - 440) < 10);
  assert.ok(Math.abs(frequency(secondStart + 0.3) - 880) < 10);
  assert.throws(() => execFileSync(process.execPath, cli, {stdio: 'pipe'}), /Video already exists/);
  console.log(`Audio/caption integration artifact: ${output}`);
});
