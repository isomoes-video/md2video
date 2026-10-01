// Pure data helpers shared by the renderer and tests.
export function validateSlides(data, script) {
  if (!data || !Array.isArray(data.slides) || data.slides.length === 0) {
    throw new Error('slides.json must contain a non-empty slides array');
  }
  if (!Array.isArray(script) || script.length !== data.slides.length) {
    throw new Error('script.json and slides.json must have the same slide count');
  }
  if (data.accent !== undefined && !/^#[0-9a-f]{6}$/i.test(data.accent)) {
    throw new Error('accent must be a six-digit hex color');
  }
  const layouts = ['title', 'bullets', 'chart', 'code', 'quote'];
  data.slides.forEach((slide, index) => {
    const number = index + 1;
    if (slide.slide_number !== number || script[index]?.slide_number !== number) {
      throw new Error(`Slides and narration must be ordered consecutively from 1 (slide ${number})`);
    }
    if (typeof script[index].narration !== 'string' || !script[index].narration.trim()) {
      throw new Error(`Missing narration for slide ${number}`);
    }
    if (typeof slide.title !== 'string' || !slide.title.trim() || !layouts.includes(slide.layout)) {
      throw new Error(`Slide ${number} needs a title and a supported layout: ${layouts.join(', ')}`);
    }
    if (slide.layout === 'bullets' && (!Array.isArray(slide.bullets) || !slide.bullets.length ||
      slide.bullets.length > 6 || slide.bullets.some((b) => typeof b !== 'string' || !b.trim()))) {
      throw new Error(`Slide ${number} needs 1–6 text bullets`);
    }
    if (slide.layout === 'chart' && (!Array.isArray(slide.bars) || !slide.bars.length ||
      slide.bars.length > 6 || slide.bars.some((b) => !b || typeof b.label !== 'string' ||
        !Number.isFinite(b.value) || b.value < 0))) {
      throw new Error(`Slide ${number} needs 1–6 bars with labels and non-negative numeric values`);
    }
    if (slide.layout === 'code' && (typeof slide.code !== 'string' || !slide.code.trim())) {
      throw new Error(`Slide ${number} needs code`);
    }
    if (slide.layout === 'quote' && (typeof slide.quote !== 'string' || !slide.quote.trim())) {
      throw new Error(`Slide ${number} needs quote text`);
    }
    if (slide.durationSeconds !== undefined && (!Number.isFinite(slide.durationSeconds) || slide.durationSeconds <= 0)) {
      throw new Error(`Slide ${number} durationSeconds must be positive`);
    }
    if (slide.revealSeconds !== undefined && (!Array.isArray(slide.revealSeconds) ||
      slide.revealSeconds.some((t, i, a) => !Number.isFinite(t) || t < 0 || (i > 0 && t < a[i - 1])))) {
      throw new Error(`Slide ${number} revealSeconds must be ordered non-negative times`);
    }
  });
  return data;
}

export function parseSrt(text) {
  const timestamp = (value) => {
    const m = value.match(/^(\d+):(\d{2}):(\d{2})[,.](\d{3})$/);
    if (!m) throw new Error(`Invalid SRT timestamp: ${value}`);
    return Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]) + Number(m[4]) / 1000;
  };
  return text.replace(/^\uFEFF/, '').replace(/\r/g, '').trim().split(/\n\s*\n/).filter(Boolean).map((block) => {
    const lines = block.split('\n');
    const at = lines.findIndex((line) => line.includes('-->'));
    if (at < 0) throw new Error('Invalid SRT cue: missing timestamp');
    const times = lines[at].split(/\s*-->\s*/);
    const start = timestamp(times[0]);
    const end = timestamp(times[1]);
    if (end <= start) throw new Error('SRT cue end must be after its start');
    return {start, end, text: lines.slice(at + 1).join('\n')};
  });
}

export function buildTimeline(slides, durations, fps, gapSeconds) {
  if (!Number.isInteger(fps) || fps < 1 || fps > 120) throw new Error('fps must be an integer from 1 to 120');
  if (!Number.isFinite(gapSeconds) || gapSeconds < 0) throw new Error('slide-gap must be non-negative');
  let from = 0;
  return slides.map((slide, i) => {
    const seconds = durations[i];
    if (!Number.isFinite(seconds) || seconds <= 0) throw new Error(`Invalid audio duration for slide ${i + 1}`);
    if (slide.revealSeconds?.some((t) => t >= seconds)) throw new Error(`Slide ${i + 1} reveal time exceeds narration duration`);
    const narrationFrames = Math.ceil(seconds * fps);
    const durationInFrames = narrationFrames + (i < slides.length - 1 ? Math.ceil(gapSeconds * fps) : 0);
    const scene = {...slide, from, narrationFrames, durationInFrames};
    from += durationInFrames;
    return scene;
  });
}
