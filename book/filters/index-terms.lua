-- index-terms.lua: the book's index from a list of terms (book/index-terms.txt).
--
-- For each chapter and the appendix (a level-1 heading), the first place in running text where a term of the
-- list appears gets \index{KEY} in front of it. Headings, code blocks, figures and captions are
-- left alone, so no \index lands in a moving argument. Only the LaTeX output is changed, and
-- only when the metadata field index-terms names the list (the book sets it; the solutions
-- manual does not).

local stringify = pandoc.utils.stringify

local function trim(s) return (s:gsub("^%s+", ""):gsub("%s+$", "")) end

-- Lowercased word without the punctuation around it.
local function norm(s)
  s = s:lower():gsub("\u{2019}", "'")
  s = s:gsub("^[%(%[\"'\u{201C}\u{2018}]+", ""):gsub("[%)%]%.,;:!?\"'\u{201D}\u{2019}]+$", "")
  return s
end

local function load_terms(path)
  local f = io.open(path, "r")
  if not f then error("index-terms.lua: cannot read " .. path) end
  local terms = {}
  for line in f:lines() do
    local s = trim(line)
    if s ~= "" and s:sub(1, 1) ~= "#" then
      local phrase, key = s:match("^(.-)%s*|%s*(.-)$")
      if not phrase then phrase, key = s, s end
      if key == "" then key = phrase end
      local t = { key = key }
      if phrase:sub(1, 1) == "`" then
        t.code = phrase:gsub("^`", ""):gsub("`$", "")
      else
        t.words = {}
        for w in phrase:gmatch("%S+") do table.insert(t.words, norm(w)) end
      end
      table.insert(terms, t)
    end
  end
  f:close()
  return terms
end

local terms, by_first, by_code = nil, {}, {}
local seen = {}
local active = false

-- makeindex: a key may hold ! (levels) and @ (sort key) on purpose; quote the other specials
-- and escape LaTeX outside an explicit @ form.
local latex_map = {
  ["#"] = "\\#", ["$"] = "\\$", ["%"] = "\\%", ["&"] = "\\&", ["~"] = "\\textasciitilde{}",
  ["^"] = "\\textasciicircum{}",
}
local function index_key(key)
  local parts = {}
  for part in (key .. "!"):gmatch("(.-)!") do
    local sort, shown = part:match("^(.-)@(.*)$")
    if sort then
      table.insert(parts, sort .. "@" .. shown)
    else
      table.insert(parts, (part:gsub("[#$%%&~^]", latex_map):gsub("([^\\])_", "%1\\_")))
    end
  end
  return table.concat(parts, "!"):gsub("|", "\"|")
end

local function word_at(list, i)
  local el = list[i]
  if el and el.t == "Str" then return norm(el.text) end
  return nil
end

-- The next Str after position i, skipping spaces; returns its index.
local function next_word(list, i)
  local j = i + 1
  while list[j] and (list[j].t == "Space" or list[j].t == "SoftBreak") do j = j + 1 end
  if list[j] and list[j].t == "Str" then return j end
  return nil
end

local function matches(list, i, words)
  local j = i
  for n, w in ipairs(words) do
    local got = word_at(list, j)
    if not got then return false end
    if n == #words then
      if not (got == w or got == w .. "s" or got == w .. "es") then return false end
    elseif got ~= w then
      return false
    end
    if n < #words then
      j = next_word(list, j)
      if not j then return false end
    end
  end
  return true
end

local function mark(list)
  local out = pandoc.Inlines({})
  for i, el in ipairs(list) do
    local adds = {}
    if el.t == "Str" then
      local first = norm(el.text)
      for _, t in ipairs(by_first[first] or {}) do
        if not seen[t.key] and matches(list, i, t.words) then
          seen[t.key] = true
          table.insert(adds, t.key)
        end
      end
    elseif el.t == "Code" then
      for _, t in ipairs(by_code[el.text] or {}) do
        if not seen[t.key] then
          seen[t.key] = true
          table.insert(adds, t.key)
        end
      end
    end
    for _, k in ipairs(adds) do
      out:insert(pandoc.RawInline("latex", "\\index{" .. index_key(k) .. "}"))
    end
    out:insert(el)
  end
  return out
end

local walker = {
  traverse = "topdown",
  Header = function(el)
    -- Only the chapters (#chNN) and the appendix (#app-...) are indexed, not the front matter
    -- or the Part openers.
    if el.level == 1 then
      seen = {}
      active = el.identifier:match("^ch%d") ~= nil or el.identifier:match("^app%-") ~= nil
    end
    return el, false
  end,
  CodeBlock = function(el) return el, false end,
  RawBlock = function(el) return el, false end,
  Figure = function(el) return el, false end,
  Image = function(el) return el, false end,
  Link = function(el) return el, false end,
  Note = function(el) return el, false end,
  Inlines = function(list)
    if active then return mark(list) end
    return list
  end,
}

function Pandoc(doc)
  if not FORMAT:match("latex") then return nil end
  local path = doc.meta["index-terms"]
  if not path then return nil end
  path = stringify(path)
  if path:sub(1, 1) ~= "/" then
    path = (os.getenv("BOOK_REPO_ROOT") or ".") .. "/" .. path
  end
  terms = load_terms(path)
  for _, t in ipairs(terms) do
    if t.code then
      by_code[t.code] = by_code[t.code] or {}
      table.insert(by_code[t.code], t)
    else
      local w = t.words[1]
      by_first[w] = by_first[w] or {}
      table.insert(by_first[w], t)
    end
  end
  return doc:walk(walker)
end
