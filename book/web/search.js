// SPDX-License-Identifier: MIT
// The web edition's search (book/tools/web.py, roadmap 2.0.0 Theme F). search.json holds every
// section's page, anchor, title and first words, and each word's sections. A query's words must
// all be in a section; the last word may be the start of a word. No library is used.
(function () {
  "use strict";
  var input, box, index = null, loading = null, words = null, timer = null;

  function load() {
    if (!loading) {
      loading = fetch(input.getAttribute("data-index")).then(function (r) { return r.json(); })
        .then(function (data) { index = data; words = Object.keys(data.words); return data; });
    }
    return loading;
  }

  function tokens(text) {
    return (text.toLowerCase().match(/[a-z0-9][a-z0-9_.+#-]*/g) || [])
      .map(function (w) { return w.replace(/^[._-]+|[._-]+$/g, ""); })
      .filter(function (w) { return w.length > 1; });
  }

  function prefixed(prefix) {  // the sections of every word that starts with prefix
    var lo = 0, hi = words.length, out = new Set();
    while (lo < hi) { var mid = (lo + hi) >> 1; if (words[mid] < prefix) lo = mid + 1; else hi = mid; }
    for (var i = lo; i < words.length && words[i].lastIndexOf(prefix, 0) === 0 && out.size < 5000; i++) {
      index.words[words[i]].forEach(function (s) { out.add(s); });
    }
    return out;
  }

  function search(query) {
    var terms = tokens(query);
    if (!terms.length) return null;
    var sets = terms.map(function (t, i) {
      // own keys only: a word such as "constructor" must not find Object.prototype's
      return i === terms.length - 1 ? prefixed(t)
        : new Set(Object.prototype.hasOwnProperty.call(index.words, t) ? index.words[t] : []);
    });
    sets.sort(function (a, b) { return a.size - b.size; });
    var hits = Array.from(sets[0]).filter(function (s) { return sets.every(function (x) { return x.has(s); }); });
    // Sections whose title has the words first, then in book order.
    var score = function (s) {
      var title = index.sections[s][2].toLowerCase();
      return terms.filter(function (t) { return title.indexOf(t) >= 0; }).length;
    };
    hits.sort(function (a, b) { return score(b) - score(a) || a - b; });
    return hits;
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }

  function show() {
    var q = input.value.trim();
    box.textContent = "";
    if (!q) { box.hidden = true; return; }
    box.hidden = false;
    var hits = search(q);
    if (!hits || !hits.length) { box.appendChild(el("p", null, "No section has all of these words.")); return; }
    box.appendChild(el("p", null, hits.length + (hits.length === 1 ? " section" : " sections")));
    hits.slice(0, 40).forEach(function (s) {
      var sec = index.sections[s], a = el("a");
      a.href = sec[0] + "#" + sec[1];
      a.appendChild(el("span", null, sec[2]));
      a.appendChild(el("span", "where", index.titles ? index.titles[sec[0]] : sec[0]));
      a.appendChild(el("span", "snip", sec[3]));
      box.appendChild(a);
    });
  }

  function onInput() {
    clearTimeout(timer);
    timer = setTimeout(function () { load().then(show); }, 120);
  }

  document.addEventListener("DOMContentLoaded", function () {
    input = document.getElementById("q");
    box = document.getElementById("results");
    var menu = document.querySelector(".bar .menu");
    if (menu) {
      menu.addEventListener("click", function () {
        var open = document.body.classList.toggle("show-contents");
        menu.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }
    // Show the current chapter in the contents without moving the page.
    var side = document.getElementById("contents"), current = document.querySelector(".contents a.current");
    if (side && current) side.scrollTop = Math.max(0, current.offsetTop - side.clientHeight / 3);
    if (!input) return;
    input.addEventListener("focus", function () { load(); });
    input.addEventListener("input", onInput);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { input.value = ""; box.hidden = true; }
      if (e.key === "ArrowDown") { var f = box.querySelector("a"); if (f) { e.preventDefault(); f.focus(); } }
    });
    box.addEventListener("keydown", function (e) {
      var a = document.activeElement;
      if (e.key === "ArrowDown" && a.nextElementSibling) { e.preventDefault(); a.nextElementSibling.focus(); }
      if (e.key === "ArrowUp") { e.preventDefault(); (a.previousElementSibling && a.previousElementSibling.tagName === "A" ? a.previousElementSibling : input).focus(); }
      if (e.key === "Escape") { box.hidden = true; input.focus(); }
    });
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".search")) box.hidden = true;
    });
    var q = new URLSearchParams(location.search).get("q");
    if (q) { input.value = q; onInput(); }
  });
})();
