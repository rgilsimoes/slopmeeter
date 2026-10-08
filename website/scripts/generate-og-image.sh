#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
assets_dir="$(cd "${script_dir}/../public/assets" && pwd)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

sans="/System/Library/Fonts/Supplemental/Arial.ttf"
sans_bold="/System/Library/Fonts/Supplemental/Arial Bold.ttf"
serif_italic="/System/Library/Fonts/Supplemental/Georgia Italic.ttf"

magick "${assets_dir}/slopmeeter-logo.png" \
  -resize 444x444^ -gravity center -extent 444x444 \
  "${tmp_dir}/logo-square.png"

magick -size 444x444 xc:none \
  -fill white -draw 'circle 222,222 222,0' \
  "${tmp_dir}/logo-mask.png"

magick "${tmp_dir}/logo-square.png" "${tmp_dir}/logo-mask.png" \
  -alpha off -compose CopyOpacity -composite \
  "${tmp_dir}/logo.png"

magick -size 1200x630 gradient:'#fffdf8-#f2eadc' \
  -fill '#ff625d1a' -stroke none -draw 'circle 82,-12 230,-12' \
  -fill '#54d86b1a' -draw 'circle 1128,68 1308,68' \
  -fill '#111a2a' -draw 'roundrectangle 72,68 424,110 21,21' \
  -fill '#54d86b' -draw 'circle 96,89 103,89' \
  -font "${sans_bold}" -pointsize 17 -fill white -draw "text 115,96 'REPOSITORY EVIDENCE, EXPLAINED'" \
  -font "${sans_bold}" -pointsize 77 -kerning -3 -fill '#111a2a' -draw "text 72,220 'Slop Meeter'" \
  -font "${serif_italic}" -pointsize 47 -kerning 0 -fill '#111a2a' -draw "text 72,294 'Where slop meets its match.'" \
  -font "${sans}" -pointsize 27 -fill '#445063' -draw "text 72,374 'Inspect the receipts behind a repository:'" \
  -draw "text 72,416 'history, tests, docs, security & maintenance.'" \
  -fill '#ff625d' -draw 'roundrectangle 72,483 251,501 9,9' \
  -fill '#ffc94a' -draw 'rectangle 242,483 430,501' \
  -fill '#54d86b' -draw 'roundrectangle 421,483 608,501 9,9' \
  -fill '#111a2a' -stroke '#fffdf8' -strokewidth 6 -draw 'circle 459,492 476,492' \
  -stroke none -font "${sans_bold}" -pointsize 20 -fill '#111a2a' -kerning 0 -draw "text 72,564 'DETERMINISTIC · EXPLAINABLE · NO CODE EXECUTION'" \
  -fill white -stroke '#111a2a' -strokewidth 10 -draw 'circle 936,314 1170,314' \
  "${tmp_dir}/logo.png" -geometry +714+92 -composite \
  -fill none -stroke '#54d86b' -strokewidth 10 -draw 'circle 936,314 1158,314' \
  -strip -define png:compression-level=9 \
  "${assets_dir}/slopmeeter-og.png"
