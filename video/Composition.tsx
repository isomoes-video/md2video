import React from 'react';
import {AbsoluteFill, Html5Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, VideoProps} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const Reveal: React.FC<{at: number; children: React.ReactNode}> = ({at, children}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const progress = interpolate(frame, [at, at + Math.max(1, fps * 0.45)], [0, 1], clamp);
  return <div style={{opacity: progress, transform: `translateY(${(1 - progress) * 28}px)`}}>{children}</div>;
};

const Slide: React.FC<{scene: Scene; accent: string; subtitles: boolean; count: number}> = ({scene, accent, subtitles, count}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const exitFrames = Math.max(1, Math.min(Math.round(fps * 0.25), scene.durationInFrames - 1));
  const opacity = interpolate(frame, [scene.durationInFrames - exitFrames, scene.durationInFrames], [1, 0], clamp);
  const contentCount = scene.bullets?.length ?? scene.bars?.length ?? 1;
  // Keep all automatic reveals within the spoken portion, even for short clips.
  const revealAt = (i: number) => scene.revealSeconds?.[i] !== undefined
    ? Math.round(scene.revealSeconds[i] * fps)
    : Math.round(Math.min(fps * (0.55 + i * 0.7), scene.narrationFrames * (i + 1) / (contentCount + 2)));
  const maxBar = Math.max(1, ...(scene.bars?.map((b) => b.value) ?? []));
  const cue = scene.cues.find((c) => frame >= c.start * fps && frame < c.end * fps);
  return <AbsoluteFill style={{opacity, padding: '86px 110px 150px', color: '#f8fafc', fontFamily: '"Noto Sans CJK SC", "Microsoft YaHei", sans-serif'}}>
    <div style={{height: 7, width: 100, background: accent, marginBottom: 35}} />
    <Reveal at={0}><h1 style={{fontSize: scene.layout === 'title' ? 88 : 64, lineHeight: 1.2, margin: '0 0 25px', overflowWrap: 'anywhere'}}>{scene.title}</h1></Reveal>
    {scene.subtitle && <Reveal at={fps * 0.2}><div style={{fontSize: 32, color: '#a8b5cd', marginBottom: 35}}>{scene.subtitle}</div></Reveal>}
    {scene.model && scene.slide_number === 1 && <Reveal at={fps * 0.3}><div style={{fontSize: 22, color: '#94a3b8', marginTop: 24}}>{scene.model}</div></Reveal>}
    {scene.layout === 'bullets' && <div style={{display: 'grid', gap: 23, marginTop: 28}}>{scene.bullets?.map((text, i) => <Reveal key={i} at={revealAt(i)}><div style={{display: 'flex', gap: 24, fontSize: 38, lineHeight: 1.4}}><span style={{color: accent}}>•</span><span>{text}</span></div></Reveal>)}</div>}
    {scene.layout === 'chart' && <div style={{display: 'grid', gap: 20, marginTop: 24}}>{scene.bars?.map((bar, i) => {
      const progress = interpolate(frame, [revealAt(i), revealAt(i) + fps * 0.7], [0, 1], clamp);
      return <Reveal key={i} at={revealAt(i)}><div style={{fontSize: 27, marginBottom: 7}}>{bar.label} <span style={{color: accent}}>{bar.value}{scene.unit ?? ''}</span></div><div style={{height: 34, background: '#1e293b', borderRadius: 8}}><div style={{height: '100%', width: `${progress * bar.value / maxBar * 100}%`, background: accent, borderRadius: 8}} /></div></Reveal>;
    })}</div>}
    {scene.layout === 'code' && <Reveal at={revealAt(0)}><pre style={{fontSize: 30, lineHeight: 1.45, padding: 32, borderRadius: 18, background: '#162137', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', color: '#c4e4ff'}}>{scene.code}</pre></Reveal>}
    {scene.layout === 'quote' && <Reveal at={revealAt(0)}><blockquote style={{margin: '55px 0', borderLeft: `8px solid ${accent}`, paddingLeft: 40, fontSize: 48, lineHeight: 1.5}}>{scene.quote}<div style={{fontSize: 26, color: '#94a3b8', marginTop: 25}}>{scene.attribution}</div></blockquote></Reveal>}
    <div style={{position: 'absolute', bottom: 36, right: 70, fontSize: 23, color: '#94a3b8'}}>{scene.slide_number} / {count}</div>
    {subtitles && cue && <div style={{position: 'absolute', bottom: 82, left: 100, right: 100, textAlign: 'center', whiteSpace: 'pre-line', fontSize: 32, lineHeight: 1.4, padding: '12px 22px', borderRadius: 12, background: 'rgba(0,0,0,0.8)'}}>{cue.text}</div>}
  </AbsoluteFill>;
};

export const NarratedVideo: React.FC<VideoProps> = ({scenes, accent, subtitles}) => <AbsoluteFill style={{background: 'radial-gradient(ellipse at top right, #172b4d, #0b1220 70%)'}}>
  {scenes.map((scene) => <Sequence key={scene.slide_number} from={scene.from} durationInFrames={scene.durationInFrames} name={scene.title}>
    <Slide scene={scene} accent={accent} subtitles={subtitles} count={scenes.length} />
    {scene.audio && <Sequence durationInFrames={scene.narrationFrames} layout="none"><Html5Audio src={staticFile(scene.audio)} /></Sequence>}
  </Sequence>)}
</AbsoluteFill>;
