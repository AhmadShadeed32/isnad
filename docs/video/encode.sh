#!/bin/bash
set -e
cd "$(dirname "$0")"
mkdir -p out
ffmpeg -y -loglevel error -framerate 30 -i frames/f%05d.jpg -i out/narration.wav \
  -c:v libx264 -preset slow -crf 19 -pix_fmt yuv420p -profile:v high -level 4.2 \
  -movflags +faststart -c:a aac -b:a 160k -ar 48000 -shortest out/isnad-pitch.mp4
ffmpeg -y -loglevel error -framerate 30 -i frames/f%05d.jpg \
  -c:v libx264 -preset slow -crf 19 -pix_fmt yuv420p -movflags +faststart \
  out/isnad-pitch-silent.mp4
ls -la out/
