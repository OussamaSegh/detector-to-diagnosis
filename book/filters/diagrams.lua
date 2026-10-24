-- diagrams.lua: render ```{.dot caption="..."} blocks with Graphviz.
-- EPUB/HTML get SVG; LaTeX gets PDF (converted from the SVG with rsvg-convert),
-- so the same source produces vector graphics in both outputs.
local outdir = os.getenv("NEUROLF_DIAGRAM_DIR") or "build/diagrams"
local fmt = FORMAT

local function file_exists(p)
  local f = io.open(p, "r")
  if f then f:close() return true end
  return false
end

local counter = 0

function CodeBlock(el)
  if not el.classes:includes("dot") then return nil end
  counter = counter + 1
  local src = el.text
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
