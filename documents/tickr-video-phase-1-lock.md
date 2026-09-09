# Tickr Digest — Phase 1 Production Lock

Status: **Awaiting approval before Phase 2**  
Target: **15.00 seconds, 1080 × 1920, 30 fps, 9:16**  
Platform: **ViewMax MCP**

## Locked creative

- Audience: busy retail investors.
- Tone: premium financial editorial; calm, precise, modern.
- Visual system: deep navy, warm white, Tickr mint, restrained glow.
- Authenticity rule: every readable website screen, price, ticker, headline, source, and timestamp must come from a real Tickr Digest capture. Generative video may only supply the abstract transition.
- Captions: sentence case, maximum two lines, warm white text with the current spoken phrase accented in mint. Keep captions inside the central 80% title-safe area and above the bottom 260 px.
- CTA: “Follow what matters.”
- Secondary CTA: “Build my free briefing ↗”
- Disclaimer: “AI-generated context. Not investment advice.”

## Locked voiceover

> Your watchlist is busy. Your briefing shouldn’t be. Tickr Digest brings AI context, price moves, earnings, and company news into one clear daily view. Follow what matters.

Delivery: warm, neutral, assured; no hype; light pause after the first two sentences; finish cleanly by 14.35 seconds.

ViewMax voice lock:

- Voice: **River** (`SAz9YHcvj6GT2YYXdXww`)
- Model: `eleven_v3`
- Speed: `1.06`
- Stability: `0.68`
- Similarity boost: `0.78`
- Current cost: **1 credit per generation**

## Locked edit and caption timing

| Time | Picture | Voiceover / burned caption |
|---|---|---|
| 00:00.00–00:01.90 | Logo on navy; mint line draws left-to-right; logo fades and rises 18 px. | Your watchlist is busy. |
| 00:01.90–00:03.80 | Real landing hero enters with three-plane vertical parallax; mint sweep under “bigger picture.” | Your briefing shouldn’t be. |
| 00:03.80–00:06.35 | Real inbox preview; outline AI briefing, then company stories; labels rise 12 px and soften out. | Tickr Digest brings AI context, |
| 00:06.35–00:07.45 | Inbox price region; restrained value-rise motion without altering recorded values. | price moves, |
| 00:07.45–00:09.05 | Mint data line exits inbox, crosses one abstract Runway transition, and wipes to the real digest. | earnings, |
| 00:09.05–00:11.05 | Real earnings section; controlled 24 px card lift; US and India chips slide into alignment. | and company news |
| 00:11.05–00:12.95 | Real company-news section; source and timestamp receive one 350 ms focus ring. | into one clear daily view. |
| 00:12.95–00:15.00 | Logo end card; underline draws on; one mint glow pulse; primary and secondary CTA fade up; disclaimer remains static. | Follow what matters. |

Narration starts at 00:00.20 and should end between 00:14.20 and 00:14.40. The final 0.60 seconds is reserved for visual hold and music resolution.

## Vertical capture plan

Record the site's authentic responsive mobile layout at a 360 × 640 CSS-pixel viewport with a controlled 3× render scale, producing native 1080 × 1920 masters. Do not substitute or squeeze the desktop layout. Disable the pointer, browser notifications, and automatic page translation. Preserve all text exactly as rendered.

| Capture | Source | Required content | Crop / motion notes |
|---|---|---|---|
| A | Landing page | Tickr Digest wordmark, hero, “bigger picture,” primary CTA | Keep headline centered in the middle 720 px. Capture 2 seconds before and after the planned scroll for handle room. Separate browser chrome, page, and overlay in the editor. |
| B | Email preview | Header, AI briefing, visible price movement, company stories | Frame the email column at 86–90% of canvas width. Use only deterministic zoom/parallax. Do not regenerate or replace any text. |
| C | Web digest — earnings | Earnings heading/cards plus visible US and India market labels | Hold 1 second before and after the section settles. Keep market chips at least 120 px from either side. |
| D | Web digest — news | Company-news card with source and timestamp visible | End with the source/timestamp in the middle third for the focus ring. |
| E | End-card reference | Official Tickr wordmark and icon | Use the official asset directly, not a generated facsimile. |

## ViewMax Runway prompt lock

Generate two independent 5-second, 1080p, 9:16, silent clips with `runway`. Only a 1.6-second central excerpt will be used in the edit.

### Variation A — liquid data ribbon

> A premium abstract financial-data transition on a deep midnight navy background. A single thin luminous mint line enters from the lower left, sweeps upward through layered translucent glass planes, briefly forms a smooth market-chart arc without numbers or labels, then exits toward the upper right. Restrained editorial motion, subtle depth, elegant bloom, crisp edges, no camera shake, no people, no devices, no interface, no logos, no letters, no numbers, no symbols, no readable text. Designed as a seamless vertical wipe between two authentic website recordings. 9:16 composition, centered safe area, dark negative space at the beginning and end.

### Variation B — glass-plane data tunnel

> Vertical cinematic transition through three floating translucent navy glass planes connected by a precise mint data line. The line accelerates gently toward camera, passes through a soft luminous aperture, and resolves into flat dark navy negative space. Premium financial editorial style, minimal, controlled motion, shallow atmospheric depth, fine grain, no camera shake, no people, no device mockups, no interface, no logos, no letters, no numbers, no ticker symbols, no readable text. Preserve clean center framing for a deterministic wipe into real website footage. 9:16.

Selection rule: choose the variation with the cleaner first and last 12 frames, least bloom, and no accidental glyph-like artifacts. If neither passes, use one Seedence 1.0 Lite retry with the better prompt unchanged except for the failing visual trait.

## Deterministic animation lock

- Ease: cubic-bezier equivalent to 0.22, 1, 0.36, 1 unless noted.
- Mint highlight boxes: 3 px stroke, 14 px corner radius, 160 ms draw-on, 550–850 ms hold, 220 ms fade.
- Popover labels: 12 px rise, 180 ms in, 500 ms hold, 180 ms out.
- Data-line sweep: 4 px core plus 12 px soft glow; never cover readable text for more than 4 frames.
- Card lift: 24 px vertical travel, 320 ms, no overshoot.
- End glow: one pulse only, 480 ms total, maximum 18% luminance increase.
- No value morph may change a price, percentage, date, ticker, or earnings figure.

## Audio lock

- Music brief: restrained modern editorial pulse, 96 BPM, muted electronic percussion, warm sub pulse, sparse glassy mint-like accent, no vocals, no dramatic risers, clean ending at 15 seconds.
- UI sound: two soft low-volume interface ticks, one for the first highlight and one for the earnings-card lift.
- Transition sound: one short airy data sweep centered at 00:08.15.
- Mix target: narration dominant; music approximately -20 LUFS integrated under speech; SFX at least 8 dB below narration peaks; true peak at or below -1 dBTP.

## Live ViewMax budget lock

Checked through ViewMax MCP on 2026-09-07.

| Item | Locked maximum |
|---|---:|
| Two Runway 5 s / 1080p transition variations | 60 credits |
| One Seedence 1.0 Lite 5 s / 1080p fallback, only if required | 30 credits |
| River voiceover first pass | 1 credit |
| One River voiceover retry, reserve only | 1 credit |
| Music generation | 60 credits |
| SFX allowance | 15 credits |
| Assembly/caption/export allowance | 83 credits |
| Revision reserve | 50 credits |
| Safety margin, do not spend without a failed required generation | 58 credits |
| **Maximum planned** | **358 credits** |

Current ViewMax balance: **408 credits**. The first-cut production ceiling remains **300 credits**; the 50-credit revision reserve and 58-credit safety margin are separate. No credits were spent in Phase 1.

## Phase 1 acceptance checklist

- [x] Voiceover wording locked.
- [x] Shot and caption timing locked to exactly 15.00 seconds.
- [x] Vertical crop plan locked.
- [x] Runway transition prompts locked.
- [x] Narrator and voice settings locked against the live ViewMax catalog.
- [x] Current model capabilities and credit prices verified through ViewMax MCP.
- [x] Authentic-screen and no-generated-text rules locked.
- [ ] User approval to begin Phase 2 screen capture.
