"use strict";
const form = document.getElementById("menu-form");
const fields = document.getElementById("preferences-fields");
const button = document.getElementById("analyze-btn");
const campus = document.getElementById("campus-select");
const dateSelect = document.getElementById("date-select");
const diet = document.getElementById("diet-select");
const results = document.getElementById("results-container");
const optionsError = document.getElementById("options-error");
const preferenceInputs = {
  exclude_beef: document.getElementById("exclude-beef"),
  exclude_pork: document.getElementById("exclude-pork"),
  prioritize_protein: document.getElementById("prioritize-protein"),
};
let busy = false;
let saved = {};
try {
  saved = JSON.parse(localStorage.getItem("menuPreferences") || "{}") || {};
} catch (_) {
  /* optional storage */
}
if (typeof saved !== "object" || Array.isArray(saved)) saved = {};
diet.value =
  saved.vegan === true
    ? "vegan"
    : saved.vegetarian === true
      ? "vegetarian"
      : "any";
for (const [key, input] of Object.entries(preferenceInputs))
  input.checked = saved[key] === true;

function readPreferences() {
  return {
    campus: campus.value,
    vegetarian: diet.value === "vegetarian",
    vegan: diet.value === "vegan",
    ...Object.fromEntries(
      Object.entries(preferenceInputs).map(([key, input]) => [
        key,
        input.checked,
      ]),
    ),
  };
}
function savePreferences() {
  try {
    localStorage.setItem("menuPreferences", JSON.stringify(readPreferences()));
  } catch (_) {
    /* private browsing */
  }
}
function updateDietControls() {
  const disabled = diet.value !== "any";
  document
    .getElementById("meat-options")
    .setAttribute("aria-disabled", String(disabled));
  preferenceInputs.exclude_beef.disabled = disabled;
  preferenceInputs.exclude_pork.disabled = disabled;
}
updateDietControls();
form.addEventListener("change", () => {
  updateDietControls();
  savePreferences();
});

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function showNotice(text, isError = false) {
  const notice = element("div", `notice${isError ? " error" : ""}`, text);
  if (isError) notice.setAttribute("role", "alert");
  return notice;
}
async function fetchJSON(url, options = {}, timeout = 60000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    const data = await response.json().catch(() => null);
    if (!response.ok)
      throw new Error(
        typeof data?.error === "string"
          ? data.error
          : "The service is unavailable. Please try again.",
      );
    if (!data || typeof data !== "object")
      throw new Error("The menu response was incomplete. Please try again.");
    return data;
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error(
        "This is taking longer than expected. Please try again in a moment.",
      );
    if (error instanceof TypeError)
      throw new Error(
        "Could not connect. Check your connection and try again.",
      );
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
async function loadOptions() {
  button.disabled = true;
  optionsError.hidden = true;
  try {
    const data = await fetchJSON("/api/options", {}, 20000);
    if (
      !Array.isArray(data.campuses) ||
      !Array.isArray(data.dates) ||
      !data.campuses.length ||
      !data.dates.length
    ) {
      throw new Error(
        "No menu dates are available. Please use the official PSU menus.",
      );
    }
    campus.replaceChildren(
      ...data.campuses.map((item) => new Option(item.label, item.value)),
    );
    const preferred =
      typeof saved.campus === "string" ? saved.campus : "up-east-findlay";
    if (data.campuses.some((item) => item.value === preferred))
      campus.value = preferred;
    dateSelect.replaceChildren(
      ...data.dates.map(
        (item) =>
          new Option(
            item.value === data.today ? `Today · ${item.label}` : item.label,
            item.value,
          ),
      ),
    );
    if (data.dates.some((item) => item.value === data.today))
      dateSelect.value = data.today;
    button.disabled = false;
  } catch (error) {
    optionsError.replaceChildren(showNotice(error.message, true));
    const retry = element("button", "secondary", "Retry loading menus");
    retry.type = "button";
    retry.addEventListener("click", loadOptions);
    optionsError.append(retry);
    optionsError.hidden = false;
  }
}

function displayResults(data, selection) {
  if (
    !["Breakfast", "Lunch", "Dinner"].every((meal) => Array.isArray(data[meal]))
  ) {
    throw new Error("The menu response was incomplete. Please try again.");
  }
  results.replaceChildren();
  const meta = data._meta || {};
  const header = element("div", "result-heading");
  header.append(
    element(
      "h2",
      "",
      meta.analysis === "gemini" ? "Your meal ideas" : "On the menu",
    ),
  );
  header.append(element("p", "", `${selection.campus} · ${selection.date}`));
  const nav = element("nav", "meal-nav");
  nav.setAttribute("aria-label", "Jump to a meal");
  for (const meal of ["Breakfast", "Lunch", "Dinner"]) {
    const link = element("a", "", meal);
    link.href = `#meal-${meal.toLowerCase()}`;
    nav.append(link);
  }
  header.append(nav);
  results.append(header);
  for (const warning of meta.warnings || [])
    results.append(showNotice(warning));
  if (
    Object.values(data)
      .filter(Array.isArray)
      .every((items) => items.length === 0)
  ) {
    results.append(
      showNotice(
        meta.published_count === 0
          ? "No items are published for this location and date. It may be closed or the menu may not be posted yet."
          : "No published items match these preferences. Try another dining location or adjust your filters.",
      ),
    );
  }
  for (const meal of ["Breakfast", "Lunch", "Dinner"]) {
    const section = element("section", "panel meal");
    section.id = `meal-${meal.toLowerCase()}`;
    const heading = element("div", "meal-title");
    heading.append(
      element("h3", "", meal),
      element(
        "span",
        "",
        `${data[meal].length} ${data[meal].length === 1 ? "option" : "options"}`,
      ),
    );
    section.append(heading);
    if (!data[meal].length)
      section.append(
        element("p", "empty", "No matching items are listed for this meal."),
      );
    for (const [name, _score, reason, source] of data[meal]) {
      const food = element("article", "food");
      food.append(element("h4", "", name), element("p", "", reason));
      // Treat scraped and model-produced strings as text, never HTML.
      try {
        const url = new URL(source);
        if (
          url.protocol === "https:" &&
          url.hostname === "www.absecom.psu.edu" &&
          !url.username &&
          !url.password &&
          url.pathname.toLowerCase().endsWith("/nutrition-label.cfm")
        ) {
          const link = element("a", "", "Ingredients & nutrition ↗");
          link.href = url.href;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          food.append(link);
        }
      } catch (_) {
        /* omit unexpected source links */
      }
      section.append(food);
    }
    results.append(section);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy || button.disabled) return;
  busy = true;
  savePreferences();
  const preferences = { ...readPreferences(), date: dateSelect.value };
  const selection = {
    campus: campus.selectedOptions[0].text,
    date: dateSelect.selectedOptions[0].text,
  };
  fields.disabled = true;
  button.disabled = true;
  button.textContent = "Finding your menu…";
  results.setAttribute("aria-busy", "true");
  const loading = element("div", "panel loading");
  loading.append(
    element("div", "spinner"),
    element("p", "", "Loading the menu and finding meal ideas…"),
  );
  results.replaceChildren(loading);
  const slow = setTimeout(() => {
    loading.querySelector("p").textContent =
      "Still loading. Some dining menus take a little longer.";
  }, 8000);
  try {
    const data = await fetchJSON(
      "/api/analyze",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(preferences),
      },
      75000,
    );
    displayResults(data, selection);
  } catch (error) {
    results.replaceChildren(showNotice(error.message, true));
  } finally {
    clearTimeout(slow);
    busy = false;
    fields.disabled = false;
    updateDietControls();
    button.disabled = false;
    button.replaceChildren(
      document.createTextNode("Find meal ideas "),
      element("span", "", "→"),
    );
    results.setAttribute("aria-busy", "false");
  }
});
loadOptions();
// Deliver the retirement worker to browsers with the old version already installed.
if ("serviceWorker" in navigator) {
  navigator.serviceWorker
    .getRegistrations()
    .then((registrations) => {
      for (const registration of registrations) {
        const script =
          registration.active?.scriptURL || registration.waiting?.scriptURL;
        if (script && new URL(script).pathname === "/sw.js")
          registration.update().catch(() => {});
      }
    })
    .catch(() => {});
}
