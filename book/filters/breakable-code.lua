-- breakable-code.lua: let XeLaTeX break long inline code.
--
-- \texttt is never hyphenated, so a long identifier or path such as
-- `std::hardware_destructive_interference_size` sticks out into the margin.
-- For LaTeX output, this filter writes long inline code itself and allows a
-- line break after `_`, `/`, `.`, `,`, `(` and `::`. Headings are left alone
-- (they go into the table of contents and PDF bookmarks).

if not FORMAT:match("latex") then
  return {}
end

local MIN_LENGTH = 10

local escapes = {
  ["\\"] = "\\textbackslash{}", ["{"] = "\\{", ["}"] = "\\}",
  ["$"] = "\\$", ["&"] = "\\&", ["%"] = "\\%", ["#"] = "\\#", ["_"] = "\\_",
  ["~"] = "\\textasciitilde{}", ["^"] = "\\textasciicircum{}",
  ["<"] = "\\textless{}", [">"] = "\\textgreater{}", [" "] = "\\ ",
  ["-"] = "-\\/", ["'"] = "\\textquotesingle{}", ["`"] = "\\textasciigrave{}",
}

local break_after = { ["_"] = true, ["/"] = true, ["."] = true, [","] = true, ["("] = true }

local function latex_code(text)
  local out = {}
  local n = #text
  local i = 1
  while i <= n do
    local c = text:sub(i, i)
    out[#out + 1] = escapes[c] or c
    local next_c = text:sub(i + 1, i + 1)
    -- no break at the very end, and none inside "::" (only after it)
    if i < n then
      if break_after[c] and next_c ~= c then
        out[#out + 1] = "\\allowbreak{}"
      elseif c == ":" and text:sub(i - 1, i - 1) == ":" then
        out[#out + 1] = "\\allowbreak{}"
      end
    end
    i = i + 1
  end
  return "\\texttt{" .. table.concat(out) .. "}"
end

local function code(el)
  -- only ASCII: anything else is left to Pandoc's own writer
  if #el.text < MIN_LENGTH or el.text:find("[\128-\255]") then
    return nil
  end
  return pandoc.RawInline("latex", latex_code(el.text))
end

local function walk_inlines(block)
  return block:walk({ Code = code })
end

return {
  { Para = walk_inlines, Plain = walk_inlines },
}
