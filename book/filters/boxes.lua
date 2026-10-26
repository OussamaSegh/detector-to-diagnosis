-- boxes.lua: styled call-out boxes and index terms.
--
--   ::: {.box-regulated title="In a regulated product"}
--   ...
--   :::
-- Box classes: box-why, box-regulated, box-askteam, box-mistakes, box-note, box-milestone.
-- In LaTeX they become tcolorbox environments defined in templates/book-header.tex;
-- in EPUB they stay <div class="box-..."> styled by templates/epub.css with a heading.
--
-- Index terms: [lock-free queue]{.idx} prints the text and adds an index entry;
-- [SPSC]{.idx key="SPSC (single producer, single consumer)"} uses a different entry.

local box_titles = {
  ["box-why"] = "Why it matters",
  ["box-regulated"] = "In a regulated product",
  ["box-askteam"] = "Ask your team",
  ["box-mistakes"] = "Common mistakes",
  ["box-note"] = "Note",
  ["box-milestone"] = "MiniDAQ milestone",
}

local latex_map = {
  ["\\"] = "\\textbackslash{}", ["#"] = "\\#", ["$"] = "\\$", ["%"] = "\\%", ["&"] = "\\&",
  ["_"] = "\\_", ["{"] = "\\{", ["}"] = "\\}", ["~"] = "\\textasciitilde{}", ["^"] = "\\textasciicircum{}",
}
local function latex_escape(s)
  return (s:gsub("[\\#$%%&_{}~^]", latex_map))
end

function Div(el)
  for cls, default_title in pairs(box_titles) do
    if el.classes:includes(cls) then
      local title = el.attributes["title"] or default_title
      if FORMAT:match("latex") then
        local env = cls:gsub("%-", "")
        local blocks = { pandoc.RawBlock("latex", "\\begin{" .. env .. "}{" .. latex_escape(title) .. "}") }
        for _, b in ipairs(el.content) do table.insert(blocks, b) end
        table.insert(blocks, pandoc.RawBlock("latex", "\\end{" .. env .. "}"))
        return blocks
      else
        local head = pandoc.Div({ pandoc.Para({ pandoc.Strong(pandoc.Str(title)) }) }, pandoc.Attr("", { "box-title" }))
        table.insert(el.content, 1, head)
        el.attributes["title"] = nil
        return el
      end
    end
  end
  return nil
end

function Span(el)
  if not el.classes:includes("idx") then return nil end
  local key = el.attributes["key"] or pandoc.utils.stringify(el.content)
  if FORMAT:match("latex") then
    local k = latex_escape(key):gsub("!", "\"!"):gsub("@", "\"@"):gsub("|", "\"|")
    local out = { pandoc.RawInline("latex", "\\index{" .. k .. "}") }
    for _, i in ipairs(el.content) do table.insert(out, i) end
    return out
  end
  return el.content
end

-- Part openers: "# Part I: Title {.part}" becomes \part in LaTeX and an
-- unnumbered top-level heading elsewhere.
function Header(el)
  if el.level == 1 and el.classes:includes("part") then
    if FORMAT:match("latex") then
      return pandoc.RawBlock("latex", "\\part{" .. latex_escape(pandoc.utils.stringify(el.content)) .. "}")
    end
    if not el.classes:includes("unnumbered") then el.classes:insert("unnumbered") end
    return el
  end
  return nil
end
