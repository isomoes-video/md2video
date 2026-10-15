# md2video workflow defaults

These rules apply to every stage prompt in this directory.

- Execute requested work automatically. Do not require a preview, storyboard, approval, confirmation, or a choice of workflow before continuing.
- For a complete video request, run scene/script generation → TTS → final render → intro → AI thumbnail, without pausing between stages. Use the existing scripts and each stage's input/output contracts.
- Respect the user's requested scope and stopping point. Run automatically through that point, then stop; a stopping point is not a request to ask for approval at earlier stages.
- “Do not upload” means finish the local video, intro, and AI thumbnail, then stop. Never upload, publish, commit, or push unless explicitly requested.
- For a stage-only request, perform only that stage and necessary prerequisites. Do not infer permission for unrelated later stages.
- Preview is opt-in. Start Studio or render a silent draft only when the user requests a preview or review. If they explicitly request an approval checkpoint, pause there, not at additional unsolicited checkpoints.
- Validate inputs and inspect outputs automatically. Internal checks do not require a user-facing preview or approval. Fix recoverable problems within scope and continue.
- Make reasonable content and style decisions from the request and repository conventions. Ask only when a material ambiguity cannot safely be resolved. If credentials, dependencies, or an API failure block execution, report the blocker; never substitute fake audio, a silent final video, or a frame capture for the required AI cover.
- Report completed artifacts and any blockers accurately. Do not call a preview or prepared HTML a finished video.
