#!/usr/bin/env bash
# Builds The NeuroLF Engineer (EPUB + PDF) and the solutions manual.
# Usage: book/build.sh [epub|pdf|all] [book|solutions|both]
# Output: book/build/out/the-neurolf-engineer-v<VERSION>.{epub,pdf}
#         book/build/out/the-neurolf-engineer-solutions-v<VERSION>.{epub,pdf}
# NEUROLF_PDF_FORMAT chooses the PDF's page: print (the default, 7 x 10 in), phone (a page with
# the shape of a Galaxy S25 Ultra's screen) or kindle (the 7-inch Kindle Paperwhite's screen).
# The phone and kindle PDFs are named ...-v<VERSION>-phone.pdf and ...-v<VERSION>-kindle.pdf.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/.." && pwd)"
what="${1:-all}"
which="${2:-both}"
version="$(tr -d '[:space:]' < "$repo/VERSION")"
date_str="${NEUROLF_DATE:-$(date +%Y-%m-%d)}"
build="$here/build"
out="$build/out"
mkdir -p "$out" "$build/diagrams" "$build/tex"

export NEUROLF_REPO_ROOT="$repo"
export NEUROLF_DIAGRAM_DIR="$build/diagrams"
export NEUROLF_STRICT=1

# The page of each PDF format. A screen shows the whole page at its width, so the page has the
# screen's shape and a size at which 10 pt text is still comfortable once it is scaled to the
# screen: the S25 Ultra's 1440 x 3120 pixels (19.5:9), the Paperwhite's 1264 x 1680 (3:4).
# narrow-linewidth is the width of the text in points, for filters/narrow-tables.lua.
pdf_format="${NEUROLF_PDF_FORMAT:-print}"
pdf_suffix=""
pdf_page=()
pdf_header=()   # after book-header.tex, which loads fvextra
case "$pdf_format" in
  print) ;;
  phone)
    pdf_suffix="-phone"
    pdf_page=(-V geometry=paperwidth=3.6in -V geometry=paperheight=7.8in -V geometry=left=0.18in
              -V geometry=right=0.18in -V geometry=top=0.35in -V geometry=bottom=0.3in
              -V geometry=headsep=0.12in -V classoption=oneside -V classoption=openany
              -V classoption=10pt --lua-filter "$here/filters/narrow-tables.lua" -M narrow-linewidth=234) ;;
  kindle)
    pdf_suffix="-kindle"
    pdf_page=(-V geometry=paperwidth=4.2in -V geometry=paperheight=5.6in -V geometry=left=0.2in
              -V geometry=right=0.2in -V geometry=top=0.35in -V geometry=bottom=0.3in
              -V geometry=headsep=0.12in -V classoption=oneside -V classoption=openany
              -V classoption=10pt --lua-filter "$here/filters/narrow-tables.lua" -M narrow-linewidth=274) ;;
  *) echo "NEUROLF_PDF_FORMAT is print, phone or kindle" >&2; exit 2 ;;
esac
[ "$pdf_format" = print ] || pdf_header=(--include-in-header "$here/templates/narrow-header.tex")

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

build_one() {   # $1 = list file, $2 = output stem, $3 = metadata file
  local list="$1" stem="$2" meta="$3"
  local files=()
  while IFS= read -r f; do
    [[ -z "$f" || "$f" == \#* ]] && continue
    files+=("$here/$f")
  done < "$list"
  if [[ "$what" == epub || "$what" == all ]]; then
    pandoc "${common[@]}" --metadata-file "$meta" \
      --toc --toc-depth=2 --split-level=1 --mathml \
      --css "$here/templates/epub.css" \
      --epub-cover-image "$here/assets/cover.png" \
      -o "$out/$stem-v$version.epub" "${files[@]}"
    python3 "$here/tools/fix_epub.py" "$out/$stem-v$version.epub"
    echo "built $out/$stem-v$version.epub"
    if command -v java >/dev/null && [ -f /usr/share/java/epubcheck.jar ]; then
      java -jar /usr/share/java/epubcheck.jar "$out/$stem-v$version.epub" 2>&1 | grep -v JAVA_TOOL_OPTIONS | grep -E "ERROR|WARNING|Messages" || true
    fi
  fi
  if [[ "$what" == pdf || "$what" == all ]]; then
    local tex="$build/tex/$stem$pdf_suffix.tex"
    pandoc "${common[@]}" --metadata-file "$meta" "${pdf_page[@]}" \
      --toc --toc-depth=2 --top-level-division=chapter \
      --pdf-engine=xelatex \
      --include-in-header "$here/templates/book-header.tex" "${pdf_header[@]}" \
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
    local job="$stem$pdf_suffix" pdf="$out/$stem-v$version$pdf_suffix.pdf"
    (cd "$build/tex" && latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet "$job.tex" >"$job.latexmk.log" 2>&1) \
      || { echo "LaTeX failed, see $build/tex/$job.log"; grep -n -A3 "^!" "$build/tex/$job.log" | head -30; exit 1; }
    cp "$build/tex/$job.pdf" "$pdf"
    # A glyph the font does not have is silently left out of the PDF.
    if grep -q "Missing character" "$build/tex/$job.log"; then
      echo "PDF has characters its fonts cannot show:"; grep "Missing character" "$build/tex/$job.log" | sort | uniq -c
      exit 1
    fi
    echo "built $pdf ($(pdfinfo "$pdf" 2>/dev/null | awk '/Pages/{print $2}') pages)"
  fi
}

if [[ "$which" == book || "$which" == both ]]; then
  build_one "$here/book.txt" "the-neurolf-engineer" "$here/metadata.yaml"
fi
if [[ "$which" == solutions || "$which" == both ]]; then
  build_one "$here/solutions.txt" "the-neurolf-engineer-solutions" "$here/metadata-solutions.yaml"
fi
