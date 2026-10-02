#!/usr/bin/env node
import {readFile, mkdir, writeFile, access, copyFile} from 'node:fs/promises';
import {constants} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseArgs} from 'node:util';
import {execFileSync, spawn} from 'node:child_process';
import {validateSlides, parseSrt, buildTimeline} from '../video/data.mjs';
import {createComposition} from '../video/html.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const exists = async (file) => access(file, constants.F_OK).then(() => true, () => false);
const json = async (file) => JSON.parse(await readFile(file, 'utf8'));

async function main() {
  const {values} = parseArgs({options: {
    workspace: {type: 'string'}, preview: {type: 'boolean'}, silent: {type: 'boolean'},
    'prepare-only': {type: 'boolean'}, overwrite: {type: 'boolean'},
    fps: {type: 'string', default: '30'}, 'slide-gap': {type: 'string', default: '0.25'},
    subtitles: {type: 'string', default: 'burn'}, concurrency: {type: 'string', default: '2'},
    'browser-executable': {type: 'string'}, help: {type: 'boolean'},
  }});
  if (values.help) {
    console.log('Usage: node scripts/render_video.mjs --workspace output/<slug> [--preview | --prepare-only] [--silent] [--overwrite]\nOptions: --fps 30 --slide-gap 0.25 --subtitles burn|none --concurrency 2 --browser-executable /path/to/chrome\n--silent uses durationSeconds (default 6) instead of audio, for demos only. Preview allows missing audio.');
    return;
  }
  if (!values.workspace) throw new Error('--workspace is required');
  if (!['burn', 'none'].includes(values.subtitles)) throw new Error('--subtitles must be burn or none');
  const concurrency = Number(values.concurrency);
  if (!Number.isInteger(concurrency) || concurrency < 1) throw new Error('--concurrency must be a positive integer');
  const workspace = path.resolve(values.workspace);
  const data = validateSlides(await json(path.join(workspace, 'slides.json')), await json(path.join(workspace, 'script.json')));
  const fps = Number(values.fps);
  const output = path.join(workspace, 'video.mp4');
  if (!values.preview && !values['prepare-only'] && !values.overwrite && await exists(output)) {
    throw new Error(`Video already exists: ${output}. Pass --overwrite to replace it.`);
  }
  const audioDir = path.join(workspace, 'audio');
  const audioFiles = new Map();
  if (!values.silent && await exists(audioDir)) {
    const {readdir} = await import('node:fs/promises');
    for (const name of await readdir(audioDir)) {
      const match = name.match(/^slide-(\d+)\.mp3$/);
      if (!match) continue;
      const number = Number(match[1]);
      if (number < 1 || number > data.slides.length || audioFiles.has(number)) throw new Error(`Extra or duplicate slide audio: ${name}`);
      audioFiles.set(number, name);
    }
  }
  const durations = [];
  const media = [];
  for (const slide of data.slides) {
    const name = audioFiles.get(slide.slide_number);
    let seconds = slide.durationSeconds ?? 6;
    let audio;
    let cues = [];
    if (name) {
      const audioPath = path.join(audioDir, name);
      seconds = Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audioPath], {encoding: 'utf8'}).trim());
      audio = `audio/${name}`;
      const srtPath = path.join(audioDir, name.replace(/\.mp3$/, '.srt'));
      if (values.subtitles === 'burn' && await exists(srtPath)) cues = parseSrt(await readFile(srtPath, 'utf8'));
    } else if (!values.preview && !values.silent) {
      throw new Error(`Missing narration audio for slide ${slide.slide_number}. Run TTS first, or use --silent for a demo.`);
    } else {
      console.log(`Slide ${slide.slide_number}: silent ${seconds}s (${values.silent ? 'demo' : 'preview'})`);
    }
    durations.push(seconds);
    media.push({audio, cues});
    console.log(`Slide ${slide.slide_number}: ${slide.title} → ${audio ?? '(no audio)'} (${seconds.toFixed(3)}s)`);
  }
  const scenes = buildTimeline(data.slides, durations, fps, Number(values['slide-gap'])).map((scene, i) => ({...scene, ...media[i]}));
  const inputProps = {scenes, fps, width: 1920, height: 1080, accent: data.accent ?? '#38bdf8', subtitles: values.subtitles === 'burn'};
  const workDir = path.join(workspace, 'video-work');
  await mkdir(workDir, {recursive: true});
  const propsPath = path.join(workDir, 'timeline.json');
  await writeFile(propsPath, JSON.stringify(inputProps, null, 2));
  // Stage only referenced media and a local animation runtime; no CDN requests.
  await mkdir(path.join(workDir, 'audio'), {recursive: true});
  for (const scene of scenes) {
    if (scene.audio) await copyFile(path.join(workspace, scene.audio), path.join(workDir, scene.audio));
  }
  await mkdir(path.join(workDir, 'assets'), {recursive: true});
  await copyFile(path.join(root, 'node_modules/gsap/dist/gsap.min.js'), path.join(workDir, 'assets/gsap.min.js'));
  await writeFile(path.join(workDir, 'index.html'), createComposition(inputProps));
  if (values['prepare-only']) {
    console.log(`Prepared: ${path.join(workDir, 'index.html')}`);
    return;
  }
  const cli = path.join(root, 'node_modules/hyperframes/bin/hyperframes.mjs');
  const env = {...process.env};
  if (values['browser-executable']) {
    env.HYPERFRAMES_BROWSER_PATH = path.resolve(values['browser-executable']);
    env.PRODUCER_HEADLESS_SHELL_PATH = env.HYPERFRAMES_BROWSER_PATH;
  }
  const args = values.preview
    ? ['preview', workDir, '--foreground']
    : ['render', workDir, '--output', output, '--fps', String(fps), '--workers', String(concurrency), '--format', 'mp4', '--strict', '--no-best-effort'];
  const child = spawn(process.execPath, [cli, ...args], {stdio: 'inherit', cwd: root, env});
  const code = await new Promise((resolve, reject) => {child.on('error', reject); child.on('exit', (code) => resolve(code ?? 1));});
  if (code !== 0) throw new Error(`HyperFrames ${values.preview ? 'preview' : 'render'} failed (exit ${code})`);
  if (values.preview) return;
  const probe = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'stream=codec_type,duration:format=duration', '-of', 'json', output], {encoding: 'utf8'}));
  const duration = Number(probe.format.duration);
  const videoDuration = Number(probe.streams.find((stream) => stream.codec_type === 'video')?.duration);
  const expectedDuration = scenes.reduce((sum, scene) => sum + scene.durationInFrames, 0) / fps;
  if (!Number.isFinite(videoDuration) || videoDuration + 1 / fps < expectedDuration) throw new Error('Rendered video is shorter than its timeline');
  if (scenes.some((scene) => scene.audio) && !probe.streams.some((stream) => stream.codec_type === 'audio')) throw new Error('Rendered video is missing its narration audio stream');
  console.log(`\nRendered: ${output} (${duration.toFixed(2)}s)`);
}

main().catch((error) => {console.error(`Error: ${error.message}`); process.exitCode = 1;});
