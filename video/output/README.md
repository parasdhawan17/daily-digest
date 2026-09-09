# Tickr Digest — Phase 5 Assembly Manifest

Status: **Clean first cut complete; caption burn blocked by unavailable Whisper pipeline**

## Deliverable

`tickr-digest-first-cut-clean.mp4`

- Duration: exactly 15.000 seconds.
- Frame: 1080 × 1920, 9:16.
- Video: H.264, 30 fps, yuv420p.
- Audio: AAC, 48 kHz, stereo, sourced from the locked Phase 4 mix.
- Website footage: authentic responsive mobile captures only.
- Generative footage: the approved 1.60-second ViewMax/Runway transition only.
- Credit spend in Phase 5: 0.

## Assembly QA

- [x] Official logo opener and end card.
- [x] Mobile landing hero with deterministic motion and mint highlight sweep.
- [x] Authentic inbox with editor-drawn AI briefing outline and popover.
- [x] Recorded price remains unchanged and receives a restrained focus treatment.
- [x] Approved Runway transition appears at 00:07.45–00:09.05.
- [x] Earnings moves from collapsed to expanded using deterministic motion.
- [x] Company-news source and timestamp receive a short focus ring.
- [x] CTA and disclaimer are visible on the end card.
- [x] Video and audio streams both end at 15.000 seconds.
- [x] Timeline contact sheet visually inspected.
- [ ] Burned captions: unavailable in this workspace because the subtitles skill's required local Whisper pipeline is absent and no configured STT key is available. The skill prohibits estimated timings or a hand-rolled caption burn. The clean master remains the immutable input for captioning when a supported pipeline is available.

## Rebuild

Run `zsh video/build_first_cut.sh` from the repository root. Generated intermediates are written to `video/work/`; the clean master is written to `video/output/`.

