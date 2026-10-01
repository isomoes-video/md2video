export type Cue = {start: number; end: number; text: string};
export type Scene = {
  slide_number: number;
  layout: 'title' | 'bullets' | 'chart' | 'code' | 'quote';
  title: string;
  subtitle?: string;
  model?: string;
  bullets?: string[];
  bars?: {label: string; value: number}[];
  unit?: string;
  code?: string;
  quote?: string;
  attribution?: string;
  revealSeconds?: number[];
  from: number;
  narrationFrames: number;
  durationInFrames: number;
  audio?: string;
  cues: Cue[];
};
export type VideoProps = {
  scenes: Scene[];
  fps: number;
  width: number;
  height: number;
  accent: string;
  subtitles: boolean;
};
