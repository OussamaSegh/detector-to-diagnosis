-- narrow-tables.lua: fit tables, inline code and headings to a narrow page (the phone and Kindle
-- PDFs).
--
-- Pandoc gives a pipe table whose source lines are short columns of natural width (`l`), which
-- never wrap: on a page 3.3 inches wide such a table runs off the page. This filter gives each
-- column a share of the line width instead, in proportion to the longest text in the column, and
-- LaTeX wraps the cells. A column is never made narrower than its longest unbreakable word (a
-- check name such as `cppcoreguidelines-` stays whole); when the words of all columns together do
-- not fit, the table is set in a smaller size. book/build.sh adds this filter only for the narrow
-- formats, with the width of the text in points as metadata `narrow-linewidth`; the print PDF and
-- the EPUB keep their tables as written.
--
-- It also lets a line break after `:`, `+`, `=` and `-` in table text, after `-`, `=`, `?` and
-- `&` in inline code anywhere (which breakable-code.lua has already written as LaTeX), and after
-- `_` and `:` in a long heading such as "Why std::hardware_destructive_interference_size exists".
-- A code line indented to line up with a parenthesis far to the right (60 spaces before
-- `float hi)`) is wider than the page before its first character, and no break helps; such an
-- indentation is cut to MAX_INDENT columns, which the reader of a phone screen loses nothing by.

if not FORMAT:match("latex") then
  return {}
end

-- Estimated advance of one character at 10 pt, in points: Inconsolata is 0.5 em; for TeX Gyre
-- Pagella 0.5 em is on the safe side for words with capitals and digits.
local CODE_PT, TEXT_PT = 5.0, 5.0
local TABCOLSEP_PT = 6.0
-- The sizes to try, with their scale to 10 pt.
local SIZES = { { nil, 1.0 }, { "\\footnotesize", 0.8 }, { "\\scriptsize", 0.7 } }

local MAX_INDENT = 16

local BREAK = "\\allowbreak{}"
local HEADING_BREAK = "\\texorpdfstring{\\allowbreak{}}{}"

-- Str "62304:2006+A1:2015" becomes "62304:", break, "2006+", break, "A1:", break, "2015".
local function split_after(text, class, brk)
  local out = {}
  for piece, sep in text:gmatch("([^" .. class .. "]*)([" .. class .. "]*)") do
    if piece ~= "" or sep ~= "" then
      out[#out + 1] = pandoc.Str(piece .. sep)
      if sep ~= "" then
        out[#out + 1] = pandoc.RawInline("latex", brk)
      end
    end
  end
  if out[#out] and out[#out].t == "RawInline" then
    out[#out] = nil
  end
  return out
end

local function breakable_str(s)
  if #s.text < 8 or not s.text:find("[:+=%-].") then
    return nil
  end
  return split_after(s.text, ":+=%-", BREAK)
end

local function breakable_code(raw)
  if raw.format ~= "latex" or not raw.text:match("^\\texttt{") then
    return nil
  end
  local text = raw.text:gsub("%-\\/", "-\\/\\allowbreak{}"):gsub("([=?])", "%1\\allowbreak{}")
    :gsub("\\&", "\\&\\allowbreak{}")
  return pandoc.RawInline("latex", text)
end

local function shallow_code(block)
  local changed = false
  local text = block.text:gsub("([^\n]*)", function(line)
    local indent, rest = line:match("^( +)(.*)$")
    if indent and #indent > MAX_INDENT then
      changed = true
      return string.rep(" ", MAX_INDENT) .. rest
    end
  end)
  if changed then
    block.text = text
    return block
  end
end

local function breakable_heading(h)
  return h:walk({
    Str = function(s)
      if (utf8.len(s.text) or #s.text) < 20 or not s.text:find("[_:]") then
        return nil
      end
      return split_after(s.text, "_:", HEADING_BREAK)
    end,
  })
end

-- The widths in points at 10 pt of the whole text and of the longest unbreakable word of a
-- cell. A word is what lies between spaces and the break points added above.
local function measure(cell)
  local total, word, longest = 0, 0, 0
  local function add(n, pt)
    total = total + n * pt
    word = word + n * pt
    longest = math.max(longest, word)
  end
  local function gap()
    word = 0
  end
  local function space()
    total = total + TEXT_PT
    gap()
  end
  cell.contents:walk({
    Str = function(s)
      add(utf8.len(s.text) or #s.text, TEXT_PT)
    end,
    Space = space,
    SoftBreak = space,
    LineBreak = gap,
    Code = function(c)
      for w in c.text:gmatch("%S+") do
        add(utf8.len(w) or #w, CODE_PT)
        space()
      end
    end,
    RawInline = function(r)
      if r.format ~= "latex" then
        return
      end
      if r.text:find("allowbreak") and not r.text:match("^\\texttt{") then
        gap()
        return
      end
      -- \texttt{...} from breakable-code.lua: count the characters between break points.
      local body = r.text:gsub("^\\texttt{", ""):gsub("}$", "")
      for piece in (body .. "\\allowbreak{}"):gmatch("(.-)\\allowbreak{}") do
        local plain = piece:gsub("\\text%a+{}", "x"):gsub("\\/", ""):gsub("\\ ", " ")
          :gsub("\\(.)", "%1")
        for w, sp in plain:gmatch("(%S*)(%s*)") do
          if w ~= "" then
            add(utf8.len(w) or #w, CODE_PT)
          end
          if sp ~= "" then
            space()
          end
        end
        gap()
      end
    end,
  })
  return total, longest
end

local function fit(tbl, linewidth)
  local n = #tbl.colspecs
  if n == 0 then
    return nil
  end
  local long, word = {}, {}
  for i = 1, n do
    long[i], word[i] = 1, 0
  end
  local function visit(rows)
    for _, row in ipairs(rows) do
      local col = 1
      for _, cell in ipairs(row.cells) do
        local span = cell.col_span or 1
        local total, longest = measure(cell)
        for k = col, math.min(n, col + span - 1) do
          long[k] = math.max(long[k], total / span)
          word[k] = math.max(word[k], longest / span)
        end
        col = col + span
      end
    end
  end
  visit(tbl.head.rows)
  for _, body in ipairs(tbl.bodies) do
    visit(body.body)
  end
  visit(tbl.foot.rows)

  -- Pandoc sets a column to its share of (\columnwidth - 2(n - 1) \tabcolsep).
  local usable = linewidth - 2 * TABCOLSEP_PT * (n - 1)
  local size, mins, sum_min
  for _, s in ipairs(SIZES) do
    size, mins, sum_min = s, {}, 0
    for i = 1, n do
      -- one character of slack per column, for the estimate
      mins[i] = (word[i] + CODE_PT) * s[2] / usable
      sum_min = sum_min + mins[i]
    end
    if sum_min <= 0.97 then
      break
    end
  end

  -- Each column gets its minimum, and the rest of the line (0.97 of it, for the rules) in
  -- proportion to how much of its longest text the minimum does not yet hold.
  local extra, sum_extra = {}, 0
  for i = 1, n do
    extra[i] = math.max(0, long[i] * size[2] / usable - mins[i])
    sum_extra = sum_extra + extra[i]
  end
  local spare = math.max(0, 0.97 - sum_min)
  for i = 1, n do
    local share
    if sum_min > 0.97 then
      share = 0.97 * mins[i] / sum_min -- not even the smallest size fits: shrink all alike
    elseif sum_extra > 0 then
      share = mins[i] + spare * extra[i] / sum_extra
    else
      share = mins[i] + spare / n
    end
    tbl.colspecs[i] = { tbl.colspecs[i][1], share }
  end
  if size[1] then
    return { pandoc.RawBlock("latex", "{" .. size[1]), tbl, pandoc.RawBlock("latex", "}") }
  end
  return tbl
end

function Pandoc(doc)
  local linewidth = tonumber(pandoc.utils.stringify(doc.meta["narrow-linewidth"] or "")) or 234
  return doc:walk({
    RawInline = breakable_code,
    Header = breakable_heading,
    CodeBlock = shallow_code,
  }):walk({
    Table = function(tbl)
      return fit(tbl:walk({ Str = breakable_str }), linewidth)
    end,
  })
end
