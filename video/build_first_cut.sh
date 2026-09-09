#!/bin/zsh
set -euo pipefail

root_dir="${0:A:h:h}"
capture_dir="$root_dir/video/captures"
generated_dir="$root_dir/video/generated"
audio_dir="$root_dir/video/audio"
work_dir="$root_dir/video/work"
output_dir="$root_dir/video/output"
asset_dir="$root_dir/video/assets"

mkdir -p "$work_dir" "$output_dir"

common_video=(-an -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -r 30 -movflags +faststart)

# 00:00.00–00:01.90 — official logo opener.
ffmpeg -loglevel error -y \
  -f lavfi -i "color=c=0x0d1723:s=1080x1920:r=30:d=1.9" \
  -loop 1 -framerate 30 -i "$root_dir/public/assets/tickr-digest-logo.png" \
  -filter_complex \
  "[1:v]scale=720:-1,format=rgba,fade=t=in:st=0.12:d=0.35:alpha=1,fade=t=out:st=1.66:d=0.24:alpha=1[logo];
   [0:v][logo]overlay=x=(W-w)/2:y='(H-h)/2+18*max(0\,1-t/0.5)':shortest=1,
   drawbox=x=300:y=1100:w='if(lt(t\,0.5)\,0\,min(480\,(t-0.5)*686))':h=7:color=0xa8edca@0.95:t=fill,
   format=yuv420p[v]" \
  -map "[v]" -t 1.9 "${common_video[@]}" "$work_dir/shot-01-logo.mp4"

# 00:01.90–00:03.80 — mobile landing hero with a restrained highlight sweep.
ffmpeg -loglevel error -y \
  -loop 1 -framerate 30 -i "$capture_dir/01-landing-hero.png" \
  -vf "zoompan=z='1+0.018*on/56':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)*on/56':d=1:s=1080x1920:fps=30,
       drawbox=x=55:y=920:w='if(lt(t\,0.30)\,0\,min(420\,(t-0.30)*525))':h=8:color=0xa8edca@0.92:t=fill,
       format=yuv420p" \
  -t 1.9 "${common_video[@]}" "$work_dir/shot-02-landing.mp4"

# 00:03.80–00:06.35 — real inbox capture with editor-drawn AI context focus.
ffmpeg -loglevel error -y \
  -loop 1 -framerate 30 -i "$capture_dir/03-inbox-briefing.png" \
  -loop 1 -framerate 30 -i "$asset_dir/ai-context-label.png" \
  -filter_complex \
  "[0:v]zoompan=z='1+0.012*on/76':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)*on/76':d=1:s=1080x1920:fps=30,
   drawbox=x=44:y=1036:w=992:h=650:color=0xa8edca@0.95:t=6:enable='between(t\,0.18\,2.30)'[base];
   [1:v]scale=300:80,format=rgba,fade=t=in:st=0.28:d=0.16:alpha=1,fade=t=out:st=1.18:d=0.17:alpha=1[label];
   [base][label]overlay=x=720:y=985:enable='between(t\,0.28\,1.35)':shortest=1,format=yuv420p[v]" \
  -map "[v]" -t 2.55 "${common_video[@]}" "$work_dir/shot-03-inbox.mp4"

# 00:06.35–00:07.45 — authentic price and earnings summary; values stay unchanged.
ffmpeg -loglevel error -y \
  -loop 1 -framerate 30 -i "$capture_dir/05-earnings-collapsed.png" \
  -vf "zoompan=z='1+0.022*on/32':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:s=1080x1920:fps=30,
       drawbox=x=218:y=842:w='if(lt(t\,0.10)\,0\,min(510\,(t-0.10)*728))':h=112:color=0xa8edca@0.95:t=6,
       format=yuv420p" \
  -t 1.10 "${common_video[@]}" "$work_dir/shot-04-price.mp4"

# 00:07.45–00:09.05 — selected ViewMax/Runway transition.
ffmpeg -loglevel error -y \
  -i "$generated_dir/runway-transition-selected.mp4" \
  -vf "fps=30,fade=t=in:st=0:d=0.10,fade=t=out:st=1.45:d=0.15,format=yuv420p" \
  -t 1.60 "${common_video[@]}" "$work_dir/shot-05-transition.mp4"

# 00:09.05–00:11.05 — deterministic collapsed-to-expanded earnings card lift.
ffmpeg -loglevel error -y \
  -loop 1 -framerate 30 -t 2.0 -i "$capture_dir/05-earnings-collapsed.png" \
  -loop 1 -framerate 30 -t 2.0 -i "$capture_dir/06-earnings-expanded.png" \
  -filter_complex \
  "[0:v]scale=1080:1920,fps=30,setpts=PTS-STARTPTS[v0];
   [1:v]scale=1080:1920,fps=30,setpts=PTS-STARTPTS[v1];
   [v0][v1]xfade=transition=slideup:duration=0.32:offset=0.58,
   drawbox=x=95:y=964:w=890:h=158:color=0xa8edca@0.95:t=6:enable='between(t\,0.12\,0.86)',
   format=yuv420p[v]" \
  -map "[v]" -t 2.0 "${common_video[@]}" "$work_dir/shot-06-earnings.mp4"

# 00:11.05–00:12.95 — real company news with a brief source/timestamp focus ring.
ffmpeg -loglevel error -y \
  -loop 1 -framerate 30 -i "$capture_dir/07-company-news.png" \
  -vf "zoompan=z='1+0.010*on/56':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)*on/56':d=1:s=1080x1920:fps=30,
       drawbox=x=328:y=1082:w=310:h=74:color=0xa8edca@0.95:t=6:enable='between(t\,0.58\,1.18)',
       format=yuv420p" \
  -t 1.90 "${common_video[@]}" "$work_dir/shot-07-news.mp4"

# 00:12.95–00:15.00 — official logo and CTA end card.
ffmpeg -loglevel error -y \
  -loop 1 -framerate 30 -i "$asset_dir/end-card-copy.png" \
  -vf "scale=1080:1920,
   drawbox=x=300:y=920:w='if(lt(t\,0.38)\,0\,min(480\,(t-0.38)*800))':h=7:color=0xa8edca@0.95:t=fill,
   fade=t=in:st=0:d=0.18,format=yuv420p" \
  -t 2.05 "${common_video[@]}" "$work_dir/shot-08-end-card.mp4"

cat > "$work_dir/concat.txt" <<EOF
file '$work_dir/shot-01-logo.mp4'
file '$work_dir/shot-02-landing.mp4'
file '$work_dir/shot-03-inbox.mp4'
file '$work_dir/shot-04-price.mp4'
file '$work_dir/shot-05-transition.mp4'
file '$work_dir/shot-06-earnings.mp4'
file '$work_dir/shot-07-news.mp4'
file '$work_dir/shot-08-end-card.mp4'
EOF

ffmpeg -loglevel error -y \
  -f concat -safe 0 -i "$work_dir/concat.txt" \
  -i "$audio_dir/phase-4-mix.wav" \
  -map 0:v:0 -map 1:a:0 -frames:v 450 \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 256k -ar 48000 \
  -movflags +faststart "$output_dir/tickr-digest-first-cut-clean.mp4"

ffprobe -v error \
  -show_entries format=duration,size \
  -show_entries stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels,duration \
  -of default=noprint_wrappers=1 \
  "$output_dir/tickr-digest-first-cut-clean.mp4"
