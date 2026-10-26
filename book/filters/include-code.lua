-- include-code.lua: pull code listings from the repository into the book.
--
-- Usage in Markdown:
--   ```{.cpp include="minidaq/include/minidaq/core/quantity.hpp" snippet="quantity"}
--   ```
-- Attributes:
--   include  path relative to the repository root (required)
--   snippet  name of a region marked in the source with
--            // [snippet:NAME]  ...  // [/snippet:NAME]   (or # for Python/CMake/YAML)
--   lines    "A-B" line range (1-based, inclusive) when no snippet is given
--   from/to  literal text: include from the first line containing `from` up to
--            and including the next line containing `to` (robust to edits);
--            to="=}" matches a line that is exactly "}" at the indentation of
--            the `from` line (the brace that closes that block)
--   caption  optional text placed before the path in the listing caption
-- Without snippet or lines, the whole file is included (SPDX lines removed).
-- The book never contains code that is not in the repository, so every listing
-- in the book is compiled and tested by the repository's CI.

local repo_root = os.getenv("BOOK_REPO_ROOT") or "."
local tag = os.getenv("BOOK_LISTING_TAG")
local missing = 0

local function read_file(path)
  local f = io.open(repo_root .. "/" .. path, "r")
  if not f then return nil end
  local s = f:read("a")
  f:close()
  return s
end

local function split_lines(s)
  local t = {}
  for line in (s .. "\n"):gmatch("(.-)\r?\n") do table.insert(t, line) end
  if t[#t] == "" then table.remove(t) end
  return t
end

local function is_marker(line)
  return line:match("%[/?snippet:[%w_%-%.]+%]") ~= nil
end

local function extract(lines, name)
  local out, inside, found = {}, false, false
  local open_pat = "%[snippet:" .. name:gsub("%-", "%%-") .. "%]"
  local close_pat = "%[/snippet:" .. name:gsub("%-", "%%-") .. "%]"
  for _, line in ipairs(lines) do
    if line:match(close_pat) then
      inside = false
    elseif line:match(open_pat) then
      inside, found = true, true
    elseif inside and not is_marker(line) then
      table.insert(out, line)
    end
  end
  if not found then return nil end
  return out
end

local function dedent(lines)
  local min = math.huge
  for _, l in ipairs(lines) do
    if l:match("%S") then
      local ind = #l:match("^(%s*)")
      if ind < min then min = ind end
    end
  end
  if min == math.huge or min == 0 then return lines end
  local out = {}
  for _, l in ipairs(lines) do table.insert(out, l:sub(min + 1)) end
  return out
end

function CodeBlock(el)
  local path = el.attributes["include"]
  if not path then
    -- A listing written in another syntax would be printed as its own text (MDQ-PR-025).
    if el.text:match("^%s*!include") then
      io.stderr:write("include-code: not an include attribute: " .. el.text:match("^[^\n]*") .. "\n")
      missing = missing + 1
    end
    return nil
  end
  local content = read_file(path)
  if not content then
    io.stderr:write("include-code: cannot read " .. path .. "\n")
    missing = missing + 1
    return pandoc.Para({ pandoc.Strong(pandoc.Str("MISSING LISTING: " .. path)) })
  end
  local lines = split_lines(content)
  local snippet = el.attributes["snippet"]
  local range = el.attributes["lines"]
  if snippet then
    local s = extract(lines, snippet)
    if not s then
      io.stderr:write("include-code: snippet '" .. snippet .. "' not found in " .. path .. "\n")
      missing = missing + 1
      return pandoc.Para({ pandoc.Strong(pandoc.Str("MISSING SNIPPET: " .. snippet)) })
    end
    lines = dedent(s)
  elseif el.attributes["from"] then
    -- `to` is searched from the line after the `from` line onwards.
    local from, to = el.attributes["from"], el.attributes["to"]
    local s, started, indent = {}, false, ""
    for _, l in ipairs(lines) do
      if started then
        if not is_marker(l) then table.insert(s, l) end
        if to then
          -- "=text" matches a line whose trimmed content is exactly text and
          -- whose indentation equals the `from` line's, so to="=}" finds the
          -- brace that closes the block, not an inner one.
          local exact = to:sub(1, 1) == "=" and to:sub(2) or nil
          if exact then
            if l:match("^%s*(.-)%s*$") == exact and l:match("^(%s*)") == indent then break end
          elseif l:find(to, 1, true) then
            break
          end
        end
      elseif l:find(from, 1, true) then
        started = true
        indent = l:match("^(%s*)")
        table.insert(s, l)
      end
    end
    if not started then
      io.stderr:write("include-code: text '" .. from .. "' not found in " .. path .. "\n")
      missing = missing + 1
    end
    lines = dedent(s)
  elseif range then
    local a, b = range:match("^(%d+)%-(%d+)$")
    a, b = tonumber(a), tonumber(b)
    local s = {}
    for i = a, math.min(b, #lines) do table.insert(s, lines[i]) end
    lines = s
  else
    local s = {}
    for _, l in ipairs(lines) do
      if not l:match("SPDX%-License%-Identifier") and not is_marker(l) then table.insert(s, l) end
    end
    lines = s
  end
  -- Drop leading/trailing blank lines.
  while #lines > 0 and not lines[1]:match("%S") do table.remove(lines, 1) end
  while #lines > 0 and not lines[#lines]:match("%S") do table.remove(lines) end

  local attrs = {}
  for k, v in pairs(el.attributes) do
    if k ~= "include" and k ~= "snippet" and k ~= "lines" and k ~= "caption" and k ~= "from" and k ~= "to" then
      attrs[k] = v
    end
  end
  if el.classes:includes("dot") then
    -- A diagram kept in the repository: diagrams.lua renders it with its caption.
    attrs["caption"] = el.attributes["caption"]
    return pandoc.CodeBlock(table.concat(lines, "\n"), pandoc.Attr(el.identifier, el.classes, attrs))
  end
  local block = pandoc.CodeBlock(table.concat(lines, "\n"), pandoc.Attr(el.identifier, el.classes, attrs))

  local cap = { pandoc.Str("Listing:"), pandoc.Space() }
  if el.attributes["caption"] then
    for _, i in ipairs(pandoc.read(el.attributes["caption"], "markdown").blocks[1].content) do
      table.insert(cap, i)
    end
    table.insert(cap, pandoc.Space())
    table.insert(cap, pandoc.Str("("))
    table.insert(cap, pandoc.Code(path))
    table.insert(cap, pandoc.Str(")"))
  else
    table.insert(cap, pandoc.Code(path))
  end
  if tag then
    table.insert(cap, pandoc.Str(", tag"))
    table.insert(cap, pandoc.Space())
    table.insert(cap, pandoc.Code(tag))
  end
  return { pandoc.Div({ pandoc.Para({ pandoc.Emph(cap) }) }, pandoc.Attr("", { "listing-caption" })), block }
end

function Pandoc(doc)
  if missing > 0 and os.getenv("BOOK_STRICT") == "1" then
    error("include-code: " .. missing .. " missing listing(s)")
  end
  return doc
end
