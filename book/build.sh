#!/usr/bin/env bash
# Builds Detector to Diagnosis (EPUB + PDF) and the solutions manual.
# Usage: book/build.sh [epub|pdf|all|kdp|boox] [book|solutions|both]
#   all  the EPUB and the screen PDF (front cover on page 1), for the download page, and the
#        covers: the front as a JPEG and the paperback's full wrap as a PDF:
#        book/build/out/detector-to-diagnosis[-solutions]-v<VERSION>.{epub,pdf}
#        book/build/out/detector-to-diagnosis[-solutions]-v<VERSION>-cover.{jpg,pdf}
#   kdp  the files for an Amazon KDP paperback and Kindle eBook, checked against KDP's rules:
#        book/build/kdp/detector-to-diagnosis[-solutions]-v<VERSION>-{interior,cover}.pdf
#        and the EPUB. The interior has no cover, black links and an inside margin sized for
#        its page count; the cover is the full wrap (back, spine, front, bleed) with the spine
#        width computed from that page count. EPUBCheck must pass.
#   boox the PDF for a 10.3 inch 4:3 color E Ink tablet (Onyx Boox Air 5C), page = screen,
#        narrow margins, colored links and bookmarks (user request, 2026-11-09):
#        book/build/out/detector-to-diagnosis[-solutions]-v<VERSION>-boox-air-5c.pdf
# Environment:
#   BOOK_AUTHOR    the author's name, on the title page, the copyright page and the covers
#                  (default: Oussama Seghaier)
#   BOOK_DATE      the edition date (default: today)
#   BOOK_PAPER     white (default) or cream: the KDP paper, which sets the spine width
#   EPUBCHECK_JAR  path of epubcheck.jar (default /usr/share/java/epubcheck.jar)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/.." && pwd)"
what="${1:-all}"
which="${2:-both}"
version="$(tr -d '[:space:]' < "$repo/VERSION")"
date_str="${BOOK_DATE:-$(date +%Y-%m-%d)}"
author="${BOOK_AUTHOR:-Oussama Seghaier}"
paper="${BOOK_PAPER:-white}"
# The trim size (user decision, 2026-10-26: 8.5 x 11 in, one volume) and the page margins in
# inches. The inside margin of the KDP interior grows with the page count (kdp_gutter).
trim_w=8.5 trim_h=11
margin_inner=1.0 margin_outer=0.85 margin_top=0.85 margin_bottom=0.85
# The Boox page: the 10.3 in 4:3 screen in portrait (8.24 x 6.18 in), so a page fills it at 1:1
# with no zoom. Narrow margins; the header and footer sit inside the top and bottom margins.
boox_w=6.18 boox_h=8.24
boox_side=0.32 boox_top=0.22 boox_bottom=0.12
# A suffix of the cover's file names, so covers of other trims do not overwrite each other.
cover_tag=""
epubcheck_jar="${EPUBCHECK_JAR:-/usr/share/java/epubcheck.jar}"
build="$here/build"
out="$build/out"
kdp="$build/kdp"
[[ "$what" == kdp ]] && out="$kdp"
mkdir -p "$out" "$build/diagrams" "$build/tex"

export BOOK_REPO_ROOT="$repo"
export BOOK_DIAGRAM_DIR="$build/diagrams"
export BOOK_STRICT=1

common=(
  --from markdown+smart+fenced_divs+bracketed_spans+pipe_tables+grid_tables+tex_math_dollars+implicit_figures
  --lua-filter "$here/filters/include-code.lua"
  --lua-filter "$here/filters/diagrams.lua"
  --lua-filter "$here/filters/boxes.lua"
  --metadata "version=$version" --metadata "date=$date_str" --metadata "author=$author"
  --metadata "rights=Copyright © ${date_str:0:4} $author. All rights reserved. Code: MIT License."
  --lua-filter "$here/filters/vars.lua"
  --lua-filter "$here/filters/breakable-code.lua"
  --resource-path "$here:$here/assets:$build"
  --highlight-style tango
  --number-sections
)

# The front cover (book/assets/cover.tex, with the artwork book/assets/cover-*.jpg that
# book/tools/cover_art.py draws): a PDF of the trim size that becomes page 1 of the screen PDF,
# and a JPEG of it for the EPUB. $1 = book or solutions. The author is part of the cover, so a
# change of BOOK_AUTHOR rebuilds it.
build_cover() {
  local vol="$1" dir="$build/cover" c="cover-$1$cover_tag"
  mkdir -p "$dir"
  if [[ ! -f "$dir/$c.jpg" || "$here/assets/cover.tex" -nt "$dir/$c.jpg" \
        || "$here/assets/cover-front-$vol.jpg" -nt "$dir/$c.jpg" \
        || "$(cat "$dir/$c.author" 2>/dev/null)" != "$author" ]]; then
    (cd "$dir" && xelatex -interaction=nonstopmode -halt-on-error -jobname="$c" \
      "\def\nlfvolume{$vol}\def\nlftrimw{$trim_w}\def\nlftrimh{$trim_h}\def\nlfauthor{$(cover_author)}\def\nlfassets{$here/assets}\input{$here/assets/cover.tex}" \
      >"$c.xelatex.log" 2>&1) \
      || { echo "cover failed, see $dir/$c.log"; grep -n -A3 "^!" "$dir/$c.log" | head -20; exit 1; }
    # 200 dpi; a JPEG keeps the EPUB small (the artwork is a photo-like raster).
    pdftoppm -jpeg -jpegopt quality=90 -r 200 -singlefile "$dir/$c.pdf" "$dir/$c"
    printf '%s' "$author" > "$dir/$c.author"
  fi
}

# The name on the covers.
cover_author() { printf '%s' "$author"; }

# The copyright page (src/front/copyright.md) as LaTeX, set small at the foot of the page that
# follows the title page. $1 = metadata file, $2 = output .tex.
copyright_tex() {
  local meta="$1" tex="$2"
  {
    printf '%s\n' '\clearpage\thispagestyle{empty}\vspace*{\fill}' \
      '{\footnotesize\setlength{\parindent}{0pt}\setlength{\parskip}{0.6em}'
    tail -n +2 "$here/src/front/copyright.md" \
      | pandoc --from markdown+smart --to latex --metadata-file "$meta" \
          --metadata "version=$version" --metadata "date=$date_str" --metadata "author=$author" \
          --lua-filter "$here/filters/vars.lua"
    printf '%s\n' '\par}' '\clearpage'
  } > "$tex"
}

# KDP's minimum inside margin (gutter) for a page count, in inches.
kdp_gutter() {
  local n="$1"
  if (( n <= 150 )); then echo 0.375
  elif (( n <= 300 )); then echo 0.5
  elif (( n <= 500 )); then echo 0.625
  elif (( n <= 700 )); then echo 0.75
  else echo 0.875
  fi
}

pdf_pages() { pdfinfo "$1" | awk '/^Pages:/{print $2}'; }

# Checks a KDP interior: every page of the trim size (no bleed), every font embedded, a page count KDP
# prints, and images of at least 300 ppi (a warning). $1 = PDF.
check_kdp_interior() {
  local pdf="$1" n w h
  n="$(pdf_pages "$pdf")"
  w="$(awk -v x="$trim_w" 'BEGIN { print x * 72 }')" h="$(awk -v x="$trim_h" 'BEGIN { print x * 72 }')"
  if (( n < 24 || n > 828 )); then
    echo "KDP: $pdf has $n pages; a $trim_w x $trim_h in paperback must have 24 to 828"; exit 1
  fi
  if pdfinfo -f 1 -l "$n" "$pdf" | awk -v w="$w" -v h="$h" '/^Page +[0-9]+ size:/ && !($4 == w && $6 == h) {bad=1} END {exit !bad}'; then
    echo "KDP: $pdf has pages that are not $trim_w x $trim_h in:"
    pdfinfo -f 1 -l "$n" "$pdf" | awk -v w="$w" -v h="$h" '/^Page +[0-9]+ size:/ && !($4 == w && $6 == h)' | head -5
    exit 1
  fi
  if pdffonts "$pdf" | awk 'NR > 2 && $(NF-4) != "yes" {bad=1} END {exit !bad}'; then
    echo "KDP: $pdf has fonts that are not embedded:"; pdffonts "$pdf"; exit 1
  fi
  pdfimages -list "$pdf" 2>/dev/null | awk 'NR > 2 && $3 == "image" && ($13 < 300 || $14 < 300) {
      printf "KDP warning: image on page %s at %s x %s ppi (300 or more prints sharply)\n", $1, $13, $14 }' \
    | sort -u | head -20
  echo "KDP interior ok: $n pages, $trim_w x $trim_h in, all fonts embedded"
}

# The full-wrap paperback cover. $1 = book or solutions, $2 = interior page count, $3 = output.
build_wrap_cover() {
  local vol="$1" pages="$2" pdf="$3" dir="$build/cover" spine perpage
  case "$paper" in
    white) perpage=0.002252 ;;
    cream) perpage=0.0025 ;;
    *) echo "BOOK_PAPER must be white or cream"; exit 1 ;;
  esac
  spine="$(awk -v n="$pages" -v p="$perpage" 'BEGIN { printf "%.4f", n * p }')"
  mkdir -p "$dir"
  (cd "$dir" && xelatex -interaction=nonstopmode -halt-on-error -jobname="wrap-$vol" \
    "\def\nlfvolume{$vol}\def\nlftrimw{$trim_w}\def\nlftrimh{$trim_h}\def\nlfwrap{1}\def\nlfspine{$spine}\def\nlfpages{$pages}\def\nlfauthor{$(cover_author)}\def\nlfassets{$here/assets}\input{$here/assets/cover.tex}" \
    >"wrap-$vol.xelatex.log" 2>&1) \
    || { echo "wrap cover failed, see $dir/wrap-$vol.log"; grep -n -A3 "^!" "$dir/wrap-$vol.log" | head -20; exit 1; }
  cp "$dir/wrap-$vol.pdf" "$pdf"
  echo "built $pdf (full wrap for $pages pages on $paper paper: spine $spine in, $(pdfinfo "$pdf" | awk '/^Page size/{printf "%.3f x %.3f in", $3/72, $5/72}'))"
  if pdffonts "$pdf" | awk 'NR > 2 && $(NF-4) != "yes" {bad=1} END {exit !bad}'; then
    echo "KDP: $pdf has fonts that are not embedded"; exit 1
  fi
}

epubcheck_run() {   # $1 = EPUB; in the kdp build, a finding fails the build
  if command -v java >/dev/null && [[ -f "$epubcheck_jar" ]]; then
    local log="$1.epubcheck.txt"
    java -jar "$epubcheck_jar" "$1" >"$log" 2>&1 || true
    grep -v JAVA_TOOL_OPTIONS "$log" | grep -E "ERROR|WARNING|FATAL|Messages" || true
    if [[ "$what" == kdp ]] && grep -qE "^(ERROR|FATAL|WARNING)" "$log"; then
      echo "KDP: EPUBCheck reported problems in $1"; exit 1
    fi
    rm -f "$log"
  elif [[ "$what" == kdp ]]; then
    echo "KDP: EPUBCheck not found (set EPUBCHECK_JAR)"; exit 1
  fi
}

build_one() {   # $1 = list file, $2 = output stem, $3 = metadata file, $4 = cover (book|solutions)
  local list="$1" stem="$2" meta="$3" vol="$4"
  build_cover "$vol"
  local files=()
  while IFS= read -r f; do
    [[ -z "$f" || "$f" == \#* ]] && continue
    files+=("$here/$f")
  done < "$list"
  if [[ "$what" == epub || "$what" == all || "$what" == kdp ]]; then
    # The copyright page follows the EPUB's title page.
    pandoc "${common[@]}" --metadata-file "$meta" \
      --toc --toc-depth=2 --split-level=1 --mathml \
      --css "$here/templates/epub.css" \
      --epub-cover-image "$build/cover/cover-$vol.jpg" \
      -o "$out/$stem-v$version.epub" "$here/src/front/copyright.md" "${files[@]}"
    python3 "$here/tools/fix_epub.py" "$out/$stem-v$version.epub"
    echo "built $out/$stem-v$version.epub"
    epubcheck_run "$out/$stem-v$version.epub"
  fi
  if [[ "$what" == pdf || "$what" == all ]]; then
    # The screen PDF: the cover is page 1, links are colored.
    build_pdf "$stem" "$meta" "$vol" screen "$margin_inner" "$out/$stem-v$version.pdf" "${files[@]}"
  fi
  if [[ "$what" == all ]]; then
    # The covers for the download page: the front as a 300 dpi JPEG, and the paperback's full
    # wrap with the spine for the screen PDF's pages less its cover page. Below 829 pages the
    # KDP interior has the same inside margin, so the same count; `kdp` counts the interior.
    pdftoppm -jpeg -jpegopt quality=92 -r 300 -singlefile "$build/cover/cover-$vol.pdf" \
      "$out/$stem-v$version-cover"
    build_wrap_cover "$vol" "$(( $(pdf_pages "$out/$stem-v$version.pdf") - 1 ))" \
      "$out/$stem-v$version-cover.pdf"
  fi
  if [[ "$what" == boox ]]; then
    # The same screen PDF on the Boox page: its own cover of that size, equal side margins.
    local trim_w="$boox_w" trim_h="$boox_h" margin_outer="$boox_side" margin_top="$boox_top" \
          margin_bottom="$boox_bottom" cover_tag="-boox"
    build_cover "$vol"
    build_pdf "$stem" "$meta" "$vol" boox "$boox_side" "$out/$stem-v$version-boox-air-5c.pdf" "${files[@]}"
  fi
  if [[ "$what" == kdp ]]; then
    # The paperback interior: no cover, black links, and an inside margin of at least KDP's
    # gutter for the page count plus 1/8 in, and never below margin_inner. A wider margin can
    # add pages, so build again until the margin fits the count.
    local inner="$margin_inner" n need pdf="$out/$stem-v$version-interior.pdf"
    for _ in 1 2 3; do
      build_pdf "$stem" "$meta" "$vol" print "$inner" "$pdf" "${files[@]}"
      n="$(pdf_pages "$pdf")"
      need="$(awk -v g="$(kdp_gutter "$n")" -v b="$margin_inner" 'BEGIN { m = g + 0.125; printf "%.3f", (m > b ? m : b) }')"
      [[ "$need" == "$(awk -v i="$inner" 'BEGIN { printf "%.3f", i }')" ]] && break
      echo "KDP: $n pages need an inside margin of $need in; building again"
      inner="$need"
    done
    check_kdp_interior "$pdf"
    build_wrap_cover "$vol" "$(pdf_pages "$pdf")" "$out/$stem-v$version-cover.pdf"
  fi
}

# One PDF. $1 = stem, $2 = metadata, $3 = cover volume, $4 = screen or print, $5 = inside
# margin in inches, $6 = output PDF, then the source files.
build_pdf() {
  local stem="$1" meta="$2" vol="$3" mode="$4" inner="$5" pdfout="$6"
  shift 6
  local files=("$@") job="$stem-$mode"
  local tex="$build/tex/$job.tex" extra=()
  if [[ "$mode" == boox ]]; then
    # The header and footer inside the narrow margins, close to the text. The page number sits
    # 24 pt below the text, so a code block that runs a line past the text (framed splits them
    # late) never touches it.
    # Tables in 9 pt with columns 4 pt apart (not 6), so the widest fit the narrower page.
    printf '%s\n' '\setlength{\tabcolsep}{4pt}' '\AtBeginEnvironment{longtable}{\small}' \
      > "$build/tex/$job-boox.tex"
    extra+=(-V "geometry:includeheadfoot" -V "geometry:headheight=13pt" -V "geometry:headsep=7pt"
            -V "geometry:footskip=24pt" --include-in-header "$build/tex/$job-boox.tex")
  fi
  if [[ "$mode" == screen || "$mode" == boox ]]; then
    # The cover is page 1. \frontmatter would add a blank page after it (\cleardoublepage).
    printf '%s\n' '\usepackage{pdfpages}' \
      "\\AtBeginDocument{\\includepdf[pages=1]{$build/cover/cover-$vol$cover_tag.pdf}}" \
      '\makeatletter\renewcommand\frontmatter{\clearpage\@mainmatterfalse\pagenumbering{roman}}\makeatother' \
      > "$build/tex/$job-cover.tex"
    extra+=(--include-in-header "$build/tex/$job-cover.tex")
  else
    # Printed links are plain text; \frontmatter keeps the title page and its back together.
    printf '%s\n' '\makeatletter\renewcommand\frontmatter{\clearpage\@mainmatterfalse\pagenumbering{roman}}\makeatother' \
      > "$build/tex/$job-cover.tex"
    extra+=(--include-in-header "$build/tex/$job-cover.tex" -M colorlinks=false)
  fi
  copyright_tex "$meta" "$build/tex/$job-copyright.tex"
  pandoc "${common[@]}" --metadata-file "$meta" \
      --toc --toc-depth=2 --top-level-division=chapter \
      "${extra[@]}" \
      --pdf-engine=xelatex \
      --include-in-header "$here/templates/book-header.tex" \
      --include-before-body "$build/tex/$job-copyright.tex" \
      --include-after-body "$here/templates/book-after.tex" \
      -V "geometry:paperwidth=${trim_w}in" -V "geometry:paperheight=${trim_h}in" \
      -V "geometry:inner=${inner}in" -V "geometry:outer=${margin_outer}in" \
      -V "geometry:top=${margin_top}in" -V "geometry:bottom=${margin_bottom}in" \
      -V date="Version $version, $date_str" \
      -s -o "$tex" "${files[@]}"
  # Images are referenced relative to book/ (src/img/...); LaTeX runs in
  # build/tex, so give it the same view.
  ln -sfn "$here/src" "$build/tex/src"
  # A fenced block whose attributes Pandoc cannot parse (for example "[[" or
  # leading spaces in a from/to value) silently becomes paragraph text: fail
  # instead. breakable-code.lua may put \allowbreak{} after the dot.
  if grep -nE '\\\{\.(\\allowbreak\{\})?(cpp|python|cmake|yaml|text|dot)' "$tex" | head -5 | grep . ; then
    echo "unprocessed code-block attributes in $tex (see lines above)"; exit 1
  fi
  (cd "$build/tex" && latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet "$job.tex" >"$job.latexmk.log" 2>&1) \
    || { echo "LaTeX failed, see $build/tex/$job.log"; grep -n -A3 "^!" "$build/tex/$job.log" | head -30; exit 1; }
  cp "$build/tex/$job.pdf" "$pdfout"
  # A glyph the font does not have is silently left out of the PDF.
  if grep -q "Missing character" "$build/tex/$job.log"; then
    echo "PDF has characters its fonts cannot show:"; grep "Missing character" "$build/tex/$job.log" | sort | uniq -c
    exit 1
  fi
  echo "built $pdfout ($(pdfinfo "$pdfout" 2>/dev/null | awk '/Pages/{print $2}') pages)"
}

if [[ "$which" == book || "$which" == both ]]; then
  build_one "$here/book.txt" "detector-to-diagnosis" "$here/metadata.yaml" book
fi
if [[ "$which" == solutions || "$which" == both ]]; then
  build_one "$here/solutions.txt" "detector-to-diagnosis-solutions" "$here/metadata-solutions.yaml" solutions
fi
