-- The printed book's volumes (roadmap 3.0.0, Theme K; book/tools/volumes.py).
--
-- Active only when book/build.sh builds one volume of the paperback (BOOK_VOLUME set):
-- * A link to an identifier that the other volume defines cannot be followed on paper, and
--   LaTeX would print "??" for it. Its text is kept and the volume is named after it:
--   "Chapter 28" becomes "Chapter 28 (Volume 2)". A link with no text of its own (an
--   automatic number, [](#fig-...)) has no number outside its volume, so it fails the build:
--   write the number in the text.
-- * Volume 2 and later continue the chapter numbers of the volume before (BOOK_CHAPTER_OFFSET),
--   so Chapter 28 is Chapter 28 in either edition.
local volume = tonumber(os.getenv("BOOK_VOLUME") or "")
if not volume then return {} end

local where = {}
local ids_file = os.getenv("BOOK_VOLUME_IDS")
if ids_file then
  for line in io.lines(ids_file) do
    local id, v = line:match("^(.-)\t(%d+)$")
    if id then where[id] = tonumber(v) end
  end
end

local function Link(el)
  local id = el.target:match("^#(.+)$")
  local other = id and where[id]
  if not other or other == volume then return nil end
  if #el.content == 0 then
    io.stderr:write(string.format(
      "volumes.lua: [](#%s) refers to volume %d from volume %d; write its number in the link text\n",
      id, other, volume))
    os.exit(1)
  end
  local out = el.content:clone()
  out:insert(pandoc.Str(string.format(" (Volume %d)", other)))
  return pandoc.Span(out)
end

local function Pandoc(doc)
  local offset = tonumber(os.getenv("BOOK_CHAPTER_OFFSET") or "0")
  if offset > 0 and FORMAT:match("latex") then
    doc.blocks:insert(1, pandoc.RawBlock("latex", string.format("\\setcounter{chapter}{%d}", offset)))
  end
  return doc
end

return { { Link = Link }, { Pandoc = Pandoc } }
