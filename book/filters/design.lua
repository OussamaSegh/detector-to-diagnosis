-- design.lua: the book's page design (book/docs/PLAN-interior-design.md, section 3). Runs before
-- boxes.lua and diagrams.lua.
--
-- * A Part header (# Part II: Title {.part}) becomes \dpart, the Part opener page with the
--   MiniDAQ map; every block after it belongs to that Part (its color).
-- * A chapter header (# Title {#ch08}, {#sol-ch08}) sets the Part from the chapter number, so
--   the solutions manual uses the colors of the Part it answers. In the EPUB it also sets
--   data-kicker for the Atlas opener (Part / Chapter, in the Part color).
-- * In "Exercises", each **Exercise n.m ...** paragraph and what follows it up to the next one
--   becomes a box-exercise. "Check yourself" and "Summary" get their cards. "Learning
--   objectives" and "Prerequisites and estimated time" stay body text under an opener heading.
-- * Diagram and figure blocks learn their Part (attribute part) for their colors.

local latex = FORMAT:match("latex") ~= nil

local roman = { I = 1, II = 2, III = 3, IV = 4, V = 5, VI = 6, VII = 7, VIII = 8, IX = 9 }
-- The stages each Part works on, lit on its opener's map (figures/tikz/pipeline-map.tex).
local lit = {
  [1] = "cpp,ro,sort", [2] = "det,ro,sort,lm,sino", [3] = "reg", [4] = "test",
  [5] = "hw,ro", [6] = "det,corr,recon,qc", [7] = "py,qc",
  [8] = "det,ro,sort,lm,sino,corr,recon,qc,dicom,cpp,reg,test,hw,py",
  [9] = "dicom,team",
}

local function part_of_chapter(n)
  if n <= 7 then return 1 elseif n <= 12 then return 2 elseif n <= 17 then return 3
  elseif n <= 21 then return 4 elseif n <= 25 then return 5 elseif n <= 30 then return 6
  elseif n <= 32 then return 7 elseif n <= 34 then return 8 else return 9 end
end

local latex_map = {
  ["\\"] = "\\textbackslash{}", ["#"] = "\\#", ["$"] = "\\$", ["%"] = "\\%", ["&"] = "\\&",
  ["_"] = "\\_", ["{"] = "\\{", ["}"] = "\\}", ["~"] = "\\textasciitilde{}", ["^"] = "\\textasciicircum{}",
}
local function esc(s) return (s:gsub("[\\#$%%&_{}~^]", latex_map)) end

local function raw(s) return pandoc.RawBlock("latex", s) end

-- Sections whose content becomes a card, by their (unnumbered) title.
local cards = {
  ["Check yourself"] = "box-check",
  ["Summary"] = "box-summary",
}
local opener_heads = {
  ["Learning objectives"] = true,
  ["Prerequisites and estimated time"] = true,
}
local part_roman = { "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX" }

local function kicker_of(part, chapter_n)
  if part == "A" then return "Appendix" end
  local roman_name = part_roman[part]
  local n = tonumber(chapter_n)
  if not roman_name or not n then return nil end
  return string.format("Part %s / Chapter %02d", roman_name, n)
end

local function is_exercise_para(b)
  if b.t ~= "Para" or #b.content == 0 or b.content[1].t ~= "Strong" then return false end
  return pandoc.utils.stringify(b.content[1]):match("^Exercise %d+%.%d+") ~= nil
end

-- Wraps the blocks of one level-2 section according to its title.
local function wrap_section(title, blocks, part)
  local card = cards[title]
  if card then
    if #blocks == 0 then return blocks end
    return { pandoc.Div(blocks, pandoc.Attr("", { card })) }
  end
  if title ~= "Exercises" then return blocks end
  local out, cur = {}, nil
  for _, b in ipairs(blocks) do
    if is_exercise_para(b) then
      if cur then out[#out + 1] = cur end
      local head = pandoc.utils.stringify(b.content[1]):gsub("%.$", "")
      local rest = {}
      for i = 2, #b.content do rest[#rest + 1] = b.content[i] end
      while #rest > 0 and (rest[1].t == "Space" or rest[1].t == "SoftBreak") do table.remove(rest, 1) end
      cur = pandoc.Div({ pandoc.Para(rest) }, pandoc.Attr("", { "box-exercise" }, { title = head }))
    elseif cur then
      cur.content:insert(b)
    else
      out[#out + 1] = b
    end
  end
  if cur then out[#out + 1] = cur end
  return out
end

local function tag_part(b, part)
  if b.t == "CodeBlock" and (b.classes:includes("dot") or b.classes:includes("figure")) then
    b.attributes["part"] = tostring(part)
  end
  return b
end

-- The chapters of each Part, for its opener: {part block index = "\\dpartch{..}{..}{..}..."}.
local function part_chapters(blocks)
  local lists, cur = {}, nil
  for i, b in ipairs(blocks) do
    if b.t == "Header" and b.level == 1 and b.classes:includes("part") then
      cur = i
      lists[cur] = {}
    elseif b.t == "RawBlock" and b.text:match("\\appendix") then
      cur = nil
    elseif cur and b.t == "Header" and b.level == 1 then
      local n = b.identifier:match("^ch(%d+)$")
      if n then
        table.insert(lists[cur], string.format("\\dpartch{%d}{%s}{%s}", tonumber(n),
          esc(pandoc.utils.stringify(b.content)), b.identifier))
      end
    end
  end
  local out = {}
  for k, v in pairs(lists) do out[k] = table.concat(v) end
  return out
end

function Pandoc(doc)
  local chapters = part_chapters(doc.blocks)
  local volume = doc.meta["d2d-volume"] and pandoc.utils.stringify(doc.meta["d2d-volume"]) or "book"
  local part = volume == "solutions" and "S" or 0
  local out = pandoc.List()
  if latex then out:insert(raw("\\dsetpart{" .. part .. "}")) end
  -- Level-2 section being collected: its title and blocks.
  local sec_title, sec_blocks = nil, nil
  local function flush()
    if sec_title then out:extend(wrap_section(sec_title, sec_blocks, part)) end
    sec_title, sec_blocks = nil, nil
  end
  for idx, b in ipairs(doc.blocks) do
    if b.t == "RawBlock" and b.format == "latex" and b.text:match("\\appendix") then
      flush()
      part = "A"
      out:insert(b)
      if latex then out:insert(raw("\\dsetpart{A}")) end
    elseif b.t == "Header" and b.level == 1 and b.classes:includes("part") then
      flush()
      local title = pandoc.utils.stringify(b.content)
      local r, rest = title:match("^Part ([IVX]+):%s*(.*)$")
      part = roman[r] or part
      if latex then
        out:insert(raw(string.format("\\dpart{%s}{%s}{%s}{%s}{%s}", part, r, esc(rest), lit[part] or "",
          chapters[idx] or "")))
      else
        b.classes:insert("part-" .. tostring(part))
        out:insert(b)
      end
    elseif b.t == "Header" and b.level == 1 then
      flush()
      local n = b.identifier:match("^ch(%d+)$") or b.identifier:match("^sol%-ch(%d+)$")
      if n then part = part_of_chapter(tonumber(n)) end
      if latex then
        out:insert(raw("\\dsetpart{" .. part .. "}\\dsetemblem{" .. b.identifier .. "}"))
      else
        b.classes:insert("part-" .. tostring(part))
        local kick = kicker_of(part, n)
        if kick then b.attributes["data-kicker"] = kick end
      end
      out:insert(b)
    elseif b.t == "Header" and b.level == 2 then
      flush()
      if opener_heads[pandoc.utils.stringify(b.content)] then
        b.classes:insert("opener-head")
      end
      out:insert(b)
      sec_title, sec_blocks = pandoc.utils.stringify(b.content), pandoc.List()
    elseif b.t == "Header" then
      flush()
      out:insert(b)
    else
      b = tag_part(b, part)
      if sec_title then sec_blocks:insert(b) else out:insert(b) end
    end
  end
  flush()
  doc.blocks = out
  return doc
end
