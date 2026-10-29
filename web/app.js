"use strict";

const $ = (selector) => document.querySelector(selector);

/** Build a DOM node. Strings become text nodes, so scraped content can never inject markup. */
function h(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === false || value == null) continue;
    if (key === "class") node.className = value;
    else node.setAttribute(key, value === true ? "" : value);
  }
  node.append(...children.flat().filter((c) => c != null && c !== false));
  return node;
}

const YOUTUBE_WATCH = "https://www.youtube.com/watch?v=";
const YOUTUBE_THUMB = "https://i.ytimg.com/vi/";
const safe = (url, prefix) => (typeof url === "string" && url.startsWith(prefix) ? url : "#");

const KIND_LABELS = {
  live: "Live now",
  upcoming: "Upcoming",
  full: "Full fight / replay",
  highlights: "Highlights",
  extra: "Weigh-in / interview / preview",
  other: "Video",
};

// ---------- tabs ----------

const tabs = [...document.querySelectorAll('[role="tab"]')];

function selectTab(tab) {
  for (const t of tabs) {
    const selected = t === tab;
    t.setAttribute("aria-selected", selected);
    t.tabIndex = selected ? 0 : -1;
    $("#" + t.getAttribute("aria-controls")).hidden = !selected;
  }
  tab.focus();
}

for (const tab of tabs) {
  tab.addEventListener("click", () => selectTab(tab));
  tab.addEventListener("keydown", (event) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (step) selectTab(tabs[(tabs.indexOf(tab) + step + tabs.length) % tabs.length]);
  });
}

// ---------- suggestions + sources tab ----------

async function getJson(url, options) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`);
  return body;
}

async function loadSuggestions() {
  try {
    const items = await getJson("/api/suggestions");
    $("#suggestions").replaceChildren(
      ...items.map((item) =>
        h("button", { type: "button", class: "chip", title: item.title }, item.query)
      )
    );
    $("#suggestions").addEventListener("click", (event) => {
      const chip = event.target.closest(".chip");
      if (chip) runSearch(chip.textContent);
    });
  } catch {
    $("#suggestions").replaceChildren(h("span", { class: "empty" }, "Suggestions unavailable."));
  }
}

async function loadChannels() {
  try {
    const names = await getJson("/api/channels");
    $("#channel-list").replaceChildren(...names.map((name) => h("li", {}, name)));
  } catch {
    $("#channel-list").replaceChildren(h("li", {}, "Could not load the list."));
  }
}

// ---------- rendering ----------

function formatDate(isoDate) {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { dateStyle: "long" });
}

function hasPassed(isoDate) {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(y, m - 1, d + 1) <= new Date();
}

function renderEvent(event) {
  const passed = hasPassed(event.date);
  const [a, b] = event.fighters;
  return h(
    "article",
    { class: "event" },
    h("h2", {}, event.title),
    h(
      "p",
      { class: "matchup" },
      `${a.name} vs ${b.name}`,
    ),
    h("p", { class: "record" }, `${a.name}: ${a.record} · ${b.name}: ${b.record}. ${event.records_note || ""}`),
    h("p", {}, event.bout),
    h(
      "p",
      { class: "when" },
      `${formatDate(event.date)} · ${event.venue} · `,
      passed ? "This card has already taken place, so look for replays and highlights." : "Coming up."
    ),
    ...event.broadcast.map((item) =>
      h(
        "p",
        { class: "broadcast" },
        h("span", { class: "badge paid" }, item.cost),
        ` ${item.name}. ${item.note}`
      )
    ),
    event.source &&
      h(
        "p",
        { class: "note" },
        "Card details: ",
        h("a", { href: safe(event.source.url, "https://"), target: "_blank", rel: "noopener noreferrer" }, event.source.label)
      )
  );
}

function renderResult(result) {
  const href = safe(result.url, YOUTUBE_WATCH);
  const kind = result.kind;
  const thumbnail = h("img", { src: safe(result.thumbnail, YOUTUBE_THUMB), alt: "", loading: "lazy", width: "168", height: "94" });
  thumbnail.addEventListener("error", () => thumbnail.remove());
  return h(
    "li",
    { class: "result" },
    h(
      "a",
      { class: "thumb", href, target: "_blank", rel: "noopener noreferrer", tabindex: "-1", "aria-hidden": "true" },
      thumbnail,
      result.duration && h("span", { class: "dur" }, result.duration)
    ),
    h(
      "div",
      {},
      h("h3", {}, h("a", { href, target: "_blank", rel: "noopener noreferrer" }, result.title)),
      h(
        "div",
        { class: "meta" },
        h("span", {}, result.channel),
        result.official && h("span", { class: "badge official" }, "✓ Official"),
        h("span", { class: `badge ${kind === "live" ? "live" : "kind"}` }, KIND_LABELS[kind] || KIND_LABELS.other),
        h("span", { class: "badge free" }, `Free · ${result.platform}`),
        result.published && h("span", {}, result.published),
        result.views && h("span", {}, result.views)
      )
    )
  );
}

const resultList = (items) => h("ul", { class: "results" }, items.map(renderResult));

function folded(summary, warning, items) {
  if (!items.length) return null;
  return h(
    "details",
    { class: "folded" },
    h("summary", {}, `${summary} (${items.length})`),
    h("p", { class: "warning" }, warning),
    resultList(items)
  );
}

function renderSources(sources) {
  const failed = sources.filter((s) => !s.ok);
  return [
    failed.length > 0 &&
      h(
        "div",
        { class: "alert", role: "alert" },
        "Search incomplete. ",
        failed.map((s) => `${s.name}: ${s.error}`).join(" "),
        " Results below may be missing."
      ),
    h(
      "ul",
      { class: "source-line", "aria-label": "Sources searched" },
      sources.map((s) => h("li", {}, s.ok ? `✓ ${s.name}: ${s.count} videos checked` : `✗ ${s.name}: unavailable`))
    ),
  ];
}

function renderResults(data) {
  const full = data.results.filter((r) => r.match === "full");
  const official = full.filter((r) => r.official);
  const unverified = full.filter((r) => !r.official);
  const related = data.results.filter((r) => r.match === "partial");
  const searched = data.sources.some((s) => s.ok);

  const officialSection = official.length
    ? [h("h2", { class: "section-title" }, `Official free streams and replays (${official.length})`), resultList(official)]
    : [
        h("h2", { class: "section-title" }, "Official free streams and replays"),
        h(
          "p",
          { class: "empty" },
          searched
            ? "No official free upload found right now. Official uploads can take time to appear, so check back later."
            : "Nothing to show because the search could not run."
        ),
      ];

  $("#results").replaceChildren(
    ...[
      data.event && renderEvent(data.event),
      ...renderSources(data.sources),
      ...officialSection,
      folded(
        "Uploads from unverified channels",
        "Not endorsed. These may not be legitimate uploads, so check who posted a video before you watch.",
        unverified
      ),
      folded("Related videos", "These mention only one of the two fighters.", related),
    ].filter(Boolean)
  );
}

// ---------- search ----------

let inFlight = null;

async function runSearch(query) {
  query = query.trim();
  if (!query) return $("#q").focus();
  $("#q").value = query;
  history.replaceState(null, "", `?q=${encodeURIComponent(query)}`);

  inFlight?.abort();
  const controller = (inFlight = new AbortController());
  const button = $("#search-form button");
  button.disabled = true;
  $("#results").setAttribute("aria-busy", "true");
  $("#status").textContent = "Searching…";
  try {
    const data = await getJson(`/api/search?q=${encodeURIComponent(query)}`, { signal: controller.signal });
    renderResults(data);
    $("#status").textContent = `Results for “${data.query}”`;
  } catch (error) {
    if (error.name === "AbortError") return;
    $("#results").replaceChildren(h("div", { class: "alert", role: "alert" }, `Search failed: ${error.message}`));
    $("#status").textContent = "";
  } finally {
    if (inFlight === controller) {
      button.disabled = false;
      $("#results").removeAttribute("aria-busy");
    }
  }
}

$("#search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  runSearch($("#q").value);
});

loadSuggestions();
loadChannels();
const initialQuery = new URLSearchParams(location.search).get("q");
if (initialQuery) runSearch(initialQuery);
