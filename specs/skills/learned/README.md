# Learned Skills

> Auto-generated skills from the Curator's cross-session learning loop.

## What lives here

This directory contains**skill manifests auto-learned by the Curator**during its 7-day analysis cycle. The Curator:

1. Scans session history from the last 7 days
2. Extracts patterns (repeated agent sequences, common routing decisions, failure modes)
3. Identifies**skill candidates**— repeated workflows that could become reusable skills
4. For high-confidence candidates (>70% confidence), writes a `manifest.yaml` to this directory

## Skill lifecycle

```text
Session history → Pattern extraction → Skill candidate → Curator review → Accept/Reject
                                                                              ↓
                                                              specs/skills/learned/<name>/manifest.yaml

```text

-**Accepted**skills appear here as subdirectories with a `manifest.yaml`
-**Rejected**candidates are discarded for this cycle (may be reconsidered in future cycles)
-**Pinned**skills (once marked as pinned) bypass auto-archival — see `runtime/learning_loop/curator.py`

## Manifest format

Each learned skill follows the same `manifest.yaml` schema as all other skills in `specs/skills/` — see `specs/skills/smoke-test/manifest.yaml` for a reference. The `source` field distinguishes auto-learned skills:

```yaml

source:
  type: curator-auto-learned
  cycle_ts: "2026-06-19T10:00:00+00:00"
  confidence: 0.85
  evidence_count: 12
  ...

```text

## Review before using

Auto-learned skills are**drafts**. Before trusting them in production:

1. Review the `system_prompt` for correctness
2. Verify the agent sequence matches your expected workflow
3. Test the skill on a known target
4. Pin it once validated (`tags: [pinned]` in manifest)

## Archival

Skills in this directory that go unused may be auto-archived by the learning loop curator. Archived skills move to `workspace/learning/archive/` and can be restored. No skill is ever auto-deleted.
