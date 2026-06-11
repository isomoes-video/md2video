# Changelog

All notable changes to this project are recorded here.

Format per entry: `<type>: <commit message> (@who) <hash>`
Entries are grouped by package version.

Generated presentation outputs were extracted to the
[ai-video](https://github.com/isomoes-video/ai-video) repo (mounted as the
`output/` submodule); deck-only commits live in that repo's history.

## 0.1.4

- refactor: extract output/ into ai-video submodule (@isomoes) ac731c7
- docs: add version-grouped changelog and package metadata (@isomoes) 7cea866

## 0.1.3

- feat: add Qwen-Image thumbnail generation stage (@isomoes) 173fb85
- feat: add live pipeline watch dashboard (@isomoes) c455a85
- fix: resolve reveal.js assets from local node_modules (@isomoes) fe87f78

## 0.1.2

- feat: add Claude Code large codebases Chinese deck + PDF preview step (@isomoes) 4ed3867
- feat: add computer & browser use best practices Chinese video output (@isomoes) 1fc431c
- docs: require source URL in intro.txt for web-sourced videos (@isomoes) 0e50d6f
- feat: add Chinese prompt caching video output (@isomoes) 678ab46

## 0.1.1

- feat: add Anthropic postmortem presentation output (@isomoes) fec0e18
- feat: Add OpenAI TTS support (@freelw) db88a43
- fix: add chapter timeline intro for apaper-mcp (@isomoes) 3db693a
- feat: add SRT subtitle generation and video embedding support (@isomoes) ec1cc7f

## 0.1.0

- fix: regenerate md2video article video output (@isomoes) bb71b06
- fix: add top safe area for slide watermarks (@isomoes) 0193150
- feat: add keyboard-first workflow video output (@isomoes) fe295b5
- fix: add a default pause between combined slides (@isomoes) 47a18f1
- fix: switch TTS generation to CosyVoice websocket (@isomoes) a60fe8e
- docs: add narration continuity rules (@isomoes) 1ebd1c1
- docs: add md2video workflow guide (@isomoes) 2974afb
- refactor: rename plan workspace to output (@isomoes) a403447
- docs: broaden plan prompt input contract (@isomoes) c196524
- feat: add script-to-intro prompt (@isomoes) d3a9a24
- feat: add PDF-to-video combine workflow (@isomoes) eb97c9c
- feat: add script-driven tts generation (@isomoes) 4c256d2
- skills: revealjs for slide (@isomoes) edc114f
- chore: simple workflow (@isomoes) d7734d9
- skill: rename (@isomoes) 9bc2837
- ai: revealjs skills add for slide create (@isomoes) a0d3bb7
- feat: agent used prompts (@isomoes) 1274250
