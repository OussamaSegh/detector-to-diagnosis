-- vars.lua: replace {{version}}, {{date}}, {{year}}, {{title}} and {{author}} in the text with
-- build metadata.
local vals = {}
function Meta(m)
  vals.version = m.version and pandoc.utils.stringify(m.version) or "unversioned"
  vals.date = m.date and pandoc.utils.stringify(m.date) or ""
  vals.year = vals.date:match("^(%d%d%d%d)") or ""
  vals.title = m.title and pandoc.utils.stringify(m.title) or ""
  if m.author then
    local names = {}
    if m.author.t == "MetaList" or (type(m.author) == "table" and m.author[1]) then
      for _, a in ipairs(m.author) do names[#names + 1] = pandoc.utils.stringify(a) end
    else
      names[1] = pandoc.utils.stringify(m.author)
    end
    vals.author = table.concat(names, ", ")
  end
end
local function sub(s)
  return (s:gsub("{{(%w+)}}", function(k) return vals[k] or ("{{" .. k .. "}}") end))
end
function Str(el)
  if el.text:find("{{") then return pandoc.Str(sub(el.text)) end
end
function Code(el)
  if el.text:find("{{") then el.text = sub(el.text) return el end
end
return { { Meta = Meta }, { Str = Str, Code = Code } }
