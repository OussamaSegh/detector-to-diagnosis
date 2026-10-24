-- vars.lua: replace {{version}} and {{date}} in the text with build metadata.
local vals = {}
function Meta(m)
  vals.version = m.version and pandoc.utils.stringify(m.version) or "unversioned"
  vals.date = m.date and pandoc.utils.stringify(m.date) or ""
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
