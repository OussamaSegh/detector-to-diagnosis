#!/usr/bin/env bash
# Builds The NeuroLF Engineer (EPUB + PDF) and the solutions manual.
# Usage: book/build.sh [epub|pdf|all] [book|solutions|both]
# Output: book/build/out/the-neurolf-engineer-v<VERSION>.{epub,pdf}
#         book/build/out/the-neurolf-engineer-solutions-v<VERSION>.{epub,pdf}
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

common=(
  --from markdown+smart+fenced_divs+bracketed_spans+pipe_tables+grid_tables+tex_math_dollars+implicit_figures
  --lua-filter "$here/filters/include-code.lua"
  --lua-filter "$here/filters/diagrams.lua"
  --lua-filter "$here/filters/boxes.lua"
  --metadata "version=$version" --metadata "date=$date_str"
  --lua-filter "$here/filters/vars.lua"
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
    local tex="$build/tex/$stem.tex"
    pandoc "${common[@]}" --metadata-file "$meta" \
      --toc --toc-depth=2 --top-level-division=chapter \
      --pdf-engine=xelatex \
      --include-in-header "$here/templates/book-header.tex" \
      --include-after-body "$here/templates/book-after.tex" \
      -V date="Version $version, $date_str" \
      -s -o "$tex" "${files[@]}"
    # A fenced block whose attributes Pandoc cannot parse (for example "[[" in
    # a from/to value) silently becomes paragraph text: fail instead.
    if grep -nE '\\\{\.(cpp|python|cmake|yaml|text|dot)' "$tex" | head -5 | grep . ; then
      echo "unprocessed code-block attributes in $tex (see lines above)"; exit 1
    fi
    (cd "$build/tex" && latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet "$stem.tex" >"$stem.latexmk.log" 2>&1) \
      || { echo "LaTeX failed, see $build/tex/$stem.log"; grep -n -A3 "^!" "$build/tex/$stem.log" | head -30; exit 1; }
    cp "$build/tex/$stem.pdf" "$out/$stem-v$version.pdf"
    echo "built $out/$stem-v$version.pdf ($(pdfinfo "$out/$stem-v$version.pdf" 2>/dev/null | awk '/Pages/{print $2}') pages)"
  fi
}

if [[ "$which" == book || "$which" == both ]]; then
  build_one "$here/book.txt" "the-neurolf-engineer" "$here/metadata.yaml"
fi
if [[ "$which" == solutions || "$which" == both ]]; then
  build_one "$here/solutions.txt" "the-neurolf-engineer-solutions" "$here/metadata-solutions.yaml"
fi
