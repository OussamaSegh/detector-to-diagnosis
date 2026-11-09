-- diagrams.lua: render ```{.dot caption="..."} blocks with Graphviz.
-- EPUB/HTML get SVG; LaTeX gets PDF (converted from the SVG with rsvg-convert),
-- so the same source produces vector graphics in both outputs.
local outdir = os.getenv("BOOK_DIAGRAM_DIR") or "build/diagrams"
local fmt = FORMAT

local function file_exists(p)
  local f = io.open(p, "r")
  if f then f:close() return true end
  return false
end

local counter = 0

-- The book's style (docs/PLAN-interior-design.md, 3.3): the book's sans font, borders in the
-- Part's color (design.lua sets the block's part), gray edges. Attributes a diagram sets itself
-- win, because these defaults come first.
local part_colors = {}
do
  local root = os.getenv("BOOK_REPO_ROOT") or "."
  local f = io.open(root .. "/book/tools/palette.json")
  if f then
    local pal = pandoc.json.decode(f:read("a"))
    f:close()
    for k, v in pairs(pal.parts) do part_colors[k] = "#" .. v[2] end
  end
end
local function restyle(src, part)
  local c = part_colors[part or "0"] or "#0F766E"
  local defaults = string.format('graph [fontname="TeX Gyre Heros"]; node [fontname="TeX Gyre Heros", color="%s", penwidth=1.1]; ' ..
    'edge [fontname="TeX Gyre Heros", color="#4B5563", fontcolor="#1F2937"]; ', c)
  src = src:gsub('fontname="Helvetica"', 'fontname="TeX Gyre Heros"'):gsub("fontname=Helvetica", 'fontname="TeX Gyre Heros"')
  return (src:gsub("^(.-{)", "%1 " .. defaults:gsub("%%", "%%%%"), 1))
end

function CodeBlock(el)
  if not el.classes:includes("dot") then return nil end
  counter = counter + 1
  local src = restyle(el.text, el.attributes["part"])
  local hash = pandoc.utils.sha1(src)
  os.execute("mkdir -p " .. outdir)
  local svg = outdir .. "/" .. hash .. ".svg"
  if not file_exists(svg) then
    local ok, out = pcall(pandoc.pipe, "dot", { "-Tsvg" }, src)
    if not ok then
      io.stderr:write("diagrams: graphviz failed for diagram " .. counter .. "\n" .. tostring(out) .. "\n")
      error("graphviz failure")
    end
    -- Graphviz emits a DOCTYPE with an external DTD, which EPUB 3 forbids.
    out = out:gsub("<!DOCTYPE.-%]?>%s*", "", 1)
    local f = io.open(svg, "w")
    f:write(out)
    f:close()
  end
  local img = svg
  if fmt:match("latex") then
    local pdf = outdir .. "/" .. hash .. ".pdf"
    if not file_exists(pdf) then
      os.execute("rsvg-convert -f pdf -o " .. pdf .. " " .. svg)
    end
    img = pdf
  end
  local caption = el.attributes["caption"] or ""
  local cap_inlines = {}
  if caption ~= "" then
    cap_inlines = pandoc.read(caption, "markdown").blocks[1].content
  end
  local attr = pandoc.Attr(el.identifier, {}, { width = el.attributes["width"] or "100%" })
  return pandoc.Figure(
    pandoc.Plain({ pandoc.Image(cap_inlines, img, "", attr) }),
    { pandoc.Plain(cap_inlines) },
    pandoc.Attr(el.identifier ~= "" and el.identifier or ("fig-dot-" .. hash:sub(1, 8)))
  )
end
