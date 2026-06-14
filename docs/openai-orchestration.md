# OpenAI Orchestration Design

This project should use OpenAI APIs as production tooling, not as an unreviewed replacement for authorship or licensing judgment.

Official docs consulted:

- Responses API and tool use: https://developers.openai.com/api/docs
- Agents SDK orchestration: https://developers.openai.com/api/docs/guides/agents
- Agents SDK handoffs and tracing: https://openai.github.io/openai-agents-python/
- Realtime and audio: https://developers.openai.com/api/docs/guides/realtime
- OpenAI SDKs and CLI: https://developers.openai.com/api/docs/libraries
- Codex MCP workflows: https://developers.openai.com/codex/mcp

## API Fit

| Need | OpenAI surface | Guardrail |
| --- | --- | --- |
| Prompted arrangement, lyric alternatives, source summaries | Responses API | Use structured outputs and store prompts/results only when useful. |
| Multi-role production chain | Agents SDK | Handoffs require explicit role boundaries and trace review. |
| Live performance co-pilot or talkback | Realtime API | Do not stream private rehearsal audio without explicit opt-in. |
| Transcribing field notes or rehearsal takes | Audio / transcription APIs | Keep raw audio local unless a reviewed workflow permits upload. |
| Codex-driven repo automation | Codex CLI / MCP | Run in branch/worktree, require tests, PR review, and no secret exposure. |
| ChatGPT-facing control surface | Apps SDK / MCP | Expose narrow tools; never expose arbitrary filesystem or DAW control. |

## Worker Chain

The canonical worker chain is versioned in `automation/worker-chain.json`.

High-value divisions of labor:

- **Archivist**: rights metadata, source lineage, historical notes.
- **Banjo Controller Engineer**: AeroBand MIDI mapping, velocity curves, articulations.
- **Max Device Builder**: clock, probability, modulation, and provenance sampler devices.
- **Arrangement Producer**: song form, hooks, contrast, and track-specific constraints.
- **Mix Engineer**: gain staging, masking, space, loudness, and translation checks.
- **Release QA**: provenance, credits, export manifest, and CI status.

## Safe Tool Design

Tools exposed to agents should be narrow and auditable:

- `read_inventory`: reads generated inventory only.
- `propose_session_change`: writes a patch proposal, not a Live set directly.
- `validate_source_rights`: checks catalog metadata before download.
- `summarize_take`: processes local transcript text, not raw audio by default.
- `render_checklist`: emits required human checks before export.

No agent gets unrestricted shell, filesystem, browser, or DAW control in production without a branch, log, and approval boundary.
