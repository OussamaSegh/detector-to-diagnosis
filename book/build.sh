#!/usr/bin/env bash
# Builds Detector to Diagnosis (EPUB + PDF) and the solutions manual.
# Usage: book/build.sh [epub|pdf|all] [book|solutions|both]
# Output: book/build/out/detector-to-diagnosis-v<VERSION>.{epub,pdf}
#         book/build/out/detector-to-diagnosis-solutions-v<VERSION>.{epub,pdf}
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/.." && pwd)"
what="${1:-all}"
which="${2:-both}"
version="$(tr -d '[:space:]' < "$repo/VERSION")"
date_str="${BOOK_DATE:-$(date +%Y-%m-%d)}"
build="$here/build"
out="$build/out"
mkdir -p "$out" "$build/diagrams" "$build/tex"

export BOOK_REPO_ROOT="$repo"
export BOOK_DIAGRAM_DIR="$build/diagrams"
export BOOK_STRICT=1

common=(
  --from markdown+smart+fenced_divs+bracketed_spans+pipe_tables+grid_tables+tex_math_dollars+implicit_figures
  --lua-filter "$here/filters/include-code.lua"
  --lua-filter "$here/filters/diagrams.lua"
  --lua-filter "$here/filters/boxes.lua"
  --metadata "version=$version" --metadata "date=$date_str"
  --lua-filter "$here/filters/vars.lua"
  --lua-filter "$here/filters/breakable-code.lua"
  --resource-path "$here:$here/assets:$build"
  --highlight-style tango
  --number-sections
)

# The front cover (book/assets/cover.tex): a 7 x 10 in PDF that becomes page 1 of the print PDF,
# and a PNG of it for the EPUB. $1 = book or solutions.
build_cover() {
  local vol="$1" dir="$build/cover"
  mkdir -p "$dir"
  if [[ ! -f "$dir/cover-$vol.png" || "$here/assets/cover.tex" -nt "$dir/cover-$vol.png" ]]; then
    (cd "$dir" && xelatex -interaction=nonstopmode -halt-on-error -jobname="cover-$vol" \
      "\def\nlfvolume{$vol}\input{$here/assets/cover.tex}" >"cover-$vol.xelatex.log" 2>&1) \
      || { echo "cover failed, see $dir/cover-$vol.log"; grep -n -A3 "^!" "$dir/cover-$vol.log" | head -20; exit 1; }
    pdftoppm -png -r 240 -singlefile "$dir/cover-$vol.pdf" "$dir/cover-$vol"
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
  if [[ "$what" == epub || "$what" == all ]]; then
    pandoc "${common[@]}" --metadata-file "$meta" \
      --toc --toc-depth=2 --split-level=1 --mathml \
      --css "$here/templates/epub.css" \
      --epub-cover-image "$build/cover/cover-$vol.png" \
      -o "$out/$stem-v$version.epub" "${files[@]}"
    python3 "$here/tools/fix_epub.py" "$out/$stem-v$version.epub"
    echo "built $out/$stem-v$version.epub"
    if command -v java >/dev/null && [ -f /usr/share/java/epubcheck.jar ]; then
      java -jar /usr/share/java/epubcheck.jar "$out/$stem-v$version.epub" 2>&1 | grep -v JAVA_TOOL_OPTIONS | grep -E "ERROR|WARNING|Messages" || true
    fi
  fi
  if [[ "$what" == pdf || "$what" == all ]]; then
    local tex="$build/tex/$stem.tex"
    # The cover is page 1. \frontmatter would add a blank page after it (\cleardoublepage).
    printf '%s\n' '\usepackage{pdfpages}' \
      "\\AtBeginDocument{\\includepdf[pages=1]{$build/cover/cover-$vol.pdf}}" \
      '\makeatletter\renewcommand\frontmatter{\clearpage\@mainmatterfalse\pagenumbering{roman}}\makeatother' \
      > "$build/tex/$stem-cover.tex"
    pandoc "${common[@]}" --metadata-file "$meta" \
      --toc --toc-depth=2 --top-level-division=chapter \
      --include-in-header "$build/tex/$stem-cover.tex" \
      --pdf-engine=xelatex \
      --include-in-header "$here/templates/book-header.tex" \
      --include-after-body "$here/templates/book-after.tex" \
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
    (cd "$build/tex" && latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet "$stem.tex" >"$stem.latexmk.log" 2>&1) \
      || { echo "LaTeX failed, see $build/tex/$stem.log"; grep -n -A3 "^!" "$build/tex/$stem.log" | head -30; exit 1; }
    cp "$build/tex/$stem.pdf" "$out/$stem-v$version.pdf"
    # A glyph the font does not have is silently left out of the PDF.
    if grep -q "Missing character" "$build/tex/$stem.log"; then
      echo "PDF has characters its fonts cannot show:"; grep "Missing character" "$build/tex/$stem.log" | sort | uniq -c
      exit 1
    fi
    echo "built $out/$stem-v$version.pdf ($(pdfinfo "$out/$stem-v$version.pdf" 2>/dev/null | awk '/Pages/{print $2}') pages)"
  fi
}

if [[ "$which" == book || "$which" == both ]]; then
  build_one "$here/book.txt" "detector-to-diagnosis" "$here/metadata.yaml" book
fi
if [[ "$which" == solutions || "$which" == both ]]; then
  build_one "$here/solutions.txt" "detector-to-diagnosis-solutions" "$here/metadata-solutions.yaml" solutions
fi
