#!/usr/bin/env bash
# Builds Detector to Diagnosis (EPUB + PDF) and the solutions manual.
# Usage: book/build.sh [epub|pdf|all|kdp] [book|solutions|both]
#   all  the EPUB and the screen PDF (front cover on page 1), for the download page:
#        book/build/out/detector-to-diagnosis[-solutions]-v<VERSION>.{epub,pdf}
#   kdp  the files for an Amazon KDP paperback and Kindle eBook, checked against KDP's rules:
#        book/build/kdp/detector-to-diagnosis[-solutions]-v<VERSION>-{interior,cover}.pdf
#        and the EPUB. The interior has no cover, black links and an inside margin sized for
#        its page count; the cover is the full wrap (back, spine, front, bleed) with the spine
#        width computed from that page count. EPUBCheck must pass.
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

# The front cover (book/assets/cover.tex): a 7 x 10 in PDF that becomes page 1 of the screen PDF,
# and a PNG of it for the EPUB. $1 = book or solutions. The author is part of the cover, so a
# change of BOOK_AUTHOR rebuilds it.
build_cover() {
  local vol="$1" dir="$build/cover"
  mkdir -p "$dir"
  if [[ ! -f "$dir/cover-$vol.png" || "$here/assets/cover.tex" -nt "$dir/cover-$vol.png" \
        || "$(cat "$dir/cover-$vol.author" 2>/dev/null)" != "$author" ]]; then
    (cd "$dir" && xelatex -interaction=nonstopmode -halt-on-error -jobname="cover-$vol" \
      "\def\nlfvolume{$vol}\def\nlfauthor{$(cover_author)}\input{$here/assets/cover.tex}" \
      >"cover-$vol.xelatex.log" 2>&1) \
      || { echo "cover failed, see $dir/cover-$vol.log"; grep -n -A3 "^!" "$dir/cover-$vol.log" | head -20; exit 1; }
    pdftoppm -png -r 240 -singlefile "$dir/cover-$vol.pdf" "$dir/cover-$vol"
    printf '%s' "$author" > "$dir/cover-$vol.author"
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

# Checks a KDP interior: every page 7 x 10 in (no bleed), every font embedded, a page count KDP
# prints, and images of at least 300 ppi (a warning). $1 = PDF.
check_kdp_interior() {
  local pdf="$1" n
  n="$(pdf_pages "$pdf")"
  if (( n < 24 || n > 828 )); then
    echo "KDP: $pdf has $n pages; a 7 x 10 in paperback must have 24 to 828"; exit 1
  fi
  if pdfinfo -f 1 -l "$n" "$pdf" | awk '/^Page +[0-9]+ size:/ && !($4 == 504 && $6 == 720) {bad=1} END {exit !bad}'; then
    echo "KDP: $pdf has pages that are not 7 x 10 in:"
    pdfinfo -f 1 -l "$n" "$pdf" | awk '/^Page +[0-9]+ size:/ && !($4 == 504 && $6 == 720)' | head -5
    exit 1
  fi
  if pdffonts "$pdf" | awk 'NR > 2 && $(NF-4) != "yes" {bad=1} END {exit !bad}'; then
    echo "KDP: $pdf has fonts that are not embedded:"; pdffonts "$pdf"; exit 1
  fi
  pdfimages -list "$pdf" 2>/dev/null | awk 'NR > 2 && $3 == "image" && ($13 < 300 || $14 < 300) {
      printf "KDP warning: image on page %s at %s x %s ppi (300 or more prints sharply)\n", $1, $13, $14 }' \
    | sort -u | head -20
  echo "KDP interior ok: $n pages, 7 x 10 in, all fonts embedded"
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
    "\def\nlfvolume{$vol}\def\nlfwrap{1}\def\nlfspine{$spine}\def\nlfpages{$pages}\def\nlfauthor{$(cover_author)}\input{$here/assets/cover.tex}" \
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
      --epub-cover-image "$build/cover/cover-$vol.png" \
      -o "$out/$stem-v$version.epub" "$here/src/front/copyright.md" "${files[@]}"
    python3 "$here/tools/fix_epub.py" "$out/$stem-v$version.epub"
    echo "built $out/$stem-v$version.epub"
    epubcheck_run "$out/$stem-v$version.epub"
  fi
  if [[ "$what" == pdf || "$what" == all ]]; then
    # The screen PDF: the cover is page 1, links are colored.
    build_pdf "$stem" "$meta" "$vol" screen 0.85 "$out/$stem-v$version.pdf" "${files[@]}"
  fi
  if [[ "$what" == kdp ]]; then
    # The paperback interior: no cover, black links, and an inside margin of at least KDP's
    # gutter for the page count plus 1/8 in. A wider margin can add pages, so build again until
    # the margin fits the count.
    local inner=0.85 n need pdf="$out/$stem-v$version-interior.pdf"
    for _ in 1 2 3; do
      build_pdf "$stem" "$meta" "$vol" print "$inner" "$pdf" "${files[@]}"
      n="$(pdf_pages "$pdf")"
      need="$(awk -v g="$(kdp_gutter "$n")" 'BEGIN { m = g + 0.125; printf "%.3f", (m > 0.85 ? m : 0.85) }')"
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
  if [[ "$mode" == screen ]]; then
    # The cover is page 1. \frontmatter would add a blank page after it (\cleardoublepage).
    printf '%s\n' '\usepackage{pdfpages}' \
      "\\AtBeginDocument{\\includepdf[pages=1]{$build/cover/cover-$vol.pdf}}" \
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
      -V geometry:paperwidth=7in -V geometry:paperheight=10in -V "geometry:inner=${inner}in" \
      -V geometry:outer=0.7in -V geometry:top=0.8in -V geometry:bottom=0.8in \
      -V date="Version $version, $date_str" \
      -s -o "$tex" "${files[@]}"
  # Images are referenced relative to book/ (src/img/...); LaTeX runs in
  # build/tex, so give it the same view.
  ln -sfn "$here/src" "$build/tex/src"
  # A fenced block whose attributes Pandoc cannot parse (for example "[[" in
  # a from/to value) silently becomes paragraph text: fail instead.
  if grep -nE '\\\{\.(cpp|python|cmake|yaml|text|dot)' "$tex" | head -5 | grep . ; then
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
