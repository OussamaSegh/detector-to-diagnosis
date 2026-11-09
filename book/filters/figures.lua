-- figures.lua: the book's figures (book/docs/PLAN-interior-design.md, section 4). Runs after
-- design.lua (which sets each block's Part) and diagrams.lua.
--
--   ```{.figure #fig-ch08-annihilation src="book/figures/tikz/ch08-annihilation.tex"
--       caption="..." alt="..." width="90%" inputs="measurements/ch12/sino"}
--   ```
--
-- book/tools/figures.py builds the source (TikZ or a matplotlib script) for the profile of this
-- build (BOOK_PROFILE: screen, boox or bw): PDF for LaTeX, SVG for the EPUB, cached by hash.
-- The alt text becomes the image's description in the EPUB; the caption is the caption.
--
-- A reference: Figure [](#fig-ch08-annihilation) prints the figure's number ("8.3"): \ref in
-- LaTeX, the same number counted here for the EPUB.

local latex = FORMAT:match("latex") ~= nil
local profile = os.getenv("BOOK_PROFILE") or "screen"
local root = os.getenv("BOOK_REPO_ROOT") or "."

local function md_inlines(s)
  if not s or s == "" then return {} end
  local blocks = pandoc.read(s, "markdown").blocks
  return blocks[1] and blocks[1].content or {}
end

function CodeBlock(el)
  if not el.classes:includes("figure") then return nil end
  local src = el.attributes["src"]
  if not src then error("figures: a .figure block without src") end
  local fmt = latex and "pdf" or "svg"
  local ok, out = pcall(pandoc.pipe, "python3", { root .. "/book/tools/figures.py", "build", src, profile,
    el.attributes["part"] or "0", fmt, el.attributes["inputs"] or "" }, "")
  if not ok then
    io.stderr:write(tostring(out) .. "\n")
    error("figures: building " .. src .. " failed")
  end
  local path = out:gsub("%s+$", "")
  local cap = md_inlines(el.attributes["caption"])
  local alt = el.attributes["alt"] and { pandoc.Str(el.attributes["alt"]) } or cap
  local attr = pandoc.Attr("", {}, { width = el.attributes["width"] or "100%" })
  return pandoc.Figure(
    pandoc.Plain({ pandoc.Image(alt, path, "", attr) }),
    { pandoc.Plain(cap) },
    pandoc.Attr(el.identifier)
  )
end

-- Figure numbers, chapter by chapter, as LaTeX counts them (for the EPUB).
local function numbers(doc)
  local nums, chapter, k, appendix = {}, 0, 0, false
  local letters = "ABCDEFGHIJ"
  for _, b in ipairs(doc.blocks) do
    if b.t == "RawBlock" and b.text:match("\\appendix") then
      appendix, chapter = true, 0
    elseif b.t == "Header" and b.level == 1 and not b.classes:includes("unnumbered")
        and not b.classes:includes("part") then
      chapter, k = chapter + 1, 0
    end
    pandoc.Div({ b }):walk({ Figure = function(f)
      k = k + 1
      if f.identifier ~= "" then
        local c = appendix and letters:sub(chapter, chapter) or tostring(chapter)
        nums[f.identifier] = c .. "." .. k
      end
    end })
  end
  return nums
end

function Pandoc(doc)
  local nums = latex and {} or numbers(doc)
  return doc:walk({
    Link = function(l)
      local id = l.target:match("^#(fig%-.+)$")
      if not id or #l.content > 0 then return nil end
      if latex then return pandoc.RawInline("latex", "\\ref{" .. id .. "}") end
      return pandoc.Link({ pandoc.Str(nums[id] or "?") }, l.target)
    end,
  })
end
