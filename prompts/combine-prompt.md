# md2video combine prompt

You are assembling the final narrated video.

## Goals

- Read `output/<presentation-slug>/output.pdf` and `output/<presentation-slug>/audio/`.
- Treat each PDF page as one slide visual and each matching mp3 as that slide narration.
- Derive each slide's on-screen duration from the actual audio length.
- Add a very short default pause between slides so slide transitions do not feel abrupt.
- Build a video where each slide image stays visible for the full duration of its narration audio.
- Concatenate all slide segments in slide order into one final video.

## Input contract

- `output.pdf` contains one presentation slide per PDF page.
- `audio/` contains one mp3 per slide, named by `slide_number`, for example `slide-01.mp3`, `slide-02.mp3`.
- Slide order comes from the PDF page order and matching audio file numbers.
- Fail clearly if any PDF page is missing a corresponding audio file, or if counts do not match.

## Output contract

- Output directory: write results inside the same `output/<presentation-slug>/` workspace.
- Final artifact: `output/<presentation-slug>/video.mp4`.
- Intermediate render assets, if needed, should stay under a subdirectory such as `output/<presentation-slug>/video-work/`.

## Implementation requirements

- Use FFmpeg for the final video assembly.
- Convert PDF pages into per-slide still images before video assembly.
- For each slide, create a video segment from the still image whose duration matches the exact narration audio duration.
- Extend each slide segment by a small default trailing hold between slides, and make that hold configurable through a script argument.
- Combine the still image and its matching mp3 into a single per-slide segment, then concatenate all segments in order.
- Encode slide segments and the final output with a normal constant frame rate such as 30 fps, not 1 fps, so common players can seek and play the MP4 reliably.
- Use explicit output settings for video and audio codecs.
- Choose audio settings that match narration content and sample rate so FFmpeg does not clamp to an invalid bitrate.
- Ensure the final MP4 is optimized for normal playback and seeking, for example by writing fast-start metadata.
- Ensure the final video contains both the slide visuals and the narration audio, with only the configured inter-slide pause added beyond the narration.
- Verify that each segment duration fully covers its narration audio plus any configured hold, and fail if the produced video stream is shorter than the audio stream.
- Prefer a standalone script runnable with `uv run` that accepts at least the presentation directory or PDF path as input.
- Log or print the resolved slide/audio mapping and final output path so the workflow is easy to verify.
