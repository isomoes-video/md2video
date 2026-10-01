import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {NarratedVideo} from './Composition';
import type {VideoProps} from './types';

const defaultProps: VideoProps = {
  scenes: [{slide_number: 1, layout: 'title', title: 'md2video', subtitle: 'Animated scenes with Remotion', from: 0, narrationFrames: 150, durationInFrames: 150, cues: []}],
  fps: 30, width: 1920, height: 1080, accent: '#38bdf8', subtitles: true,
};

const Root: React.FC = () => <Composition
  id="NarratedVideo"
  component={NarratedVideo}
  defaultProps={defaultProps}
  durationInFrames={150}
  fps={30}
  width={1920}
  height={1080}
  calculateMetadata={({props}) => ({
    durationInFrames: props.scenes.reduce((sum, scene) => sum + scene.durationInFrames, 0),
    fps: props.fps, width: props.width, height: props.height,
  })}
/>;

registerRoot(Root);
