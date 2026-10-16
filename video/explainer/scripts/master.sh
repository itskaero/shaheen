#!/bin/sh
# Masters the render's audio: loudness to -14 LUFS (streaming norm) with a
# -2 dBTP ceiling (with a limiter after it), so the music + SFX mix never clips. Video is copied.
# Usage: sh scripts/master.sh in.mp4 out.mp4
set -e
ffmpeg -v error -y -i "$1" -c:v copy \
  -af "loudnorm=I=-14:TP=-2:LRA=11,alimiter=limit=0.79:level=false:attack=1:release=60,aresample=48000" \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart "$2"
echo "mastered -> $2"
