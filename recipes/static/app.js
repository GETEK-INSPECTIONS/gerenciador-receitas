/* A local kitchen notebook. No external assets, accounts or browser storage. */
"use strict";
const $ = (selector, root = document) => root.querySelector(selector);
const escape = value => String(value).replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[char]));
const icons = {
  book: '<path d="M12 5v15M3 4c4-1 6 0 9 2 3-2 5-3 9-2v15c-4-1-6 0-9 2-3-2-5-3-9-2Z"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 10h18m-14 4h2m4 0h2m-8 3h2"/>',
  bag: '<path d="M5 7h14l2 14H3ZM8 8V6a4 4 0 0 1 8 0v2"/>',
  leaf: '<path d="M20 3C9 2 2 8 5 15s15 4 15-12ZM4 21 16 8m-7 8v-6m0 6h6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  right: '<path d="m9 5 7 7-7 7M4 12h12"/>',
  left: '<path d="m15 5-7 7 7 7m5-7H8"/>',
  people: '<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m1-16a3 3 0 0 1 0 6m2 3a5 5 0 0 1 3 4v3"/>',
  edit: '<path d="m15 4 5 5M4 20l5-1L21 7l-5-5L4 14Z"/>',
  print: '<path d="M7 8V3h10v5M7 17H3V9h18v8h-4M7 14h10v7H7Z"/>'
};
const icon = name => '<svg class="svg-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' + (icons[name] || icons.book) + '</svg>';
document.querySelectorAll("[data-icon]").forEach(node => { node.innerHTML = icon(node.dataset.icon); });
const localDate = date => [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"), String(date.getDate()).padStart(2, "0")].join("-");
const dateFrom = value => new Date(value + "T12:00:00");
const addDays = (value, days) => { const date = dateFrom(value); date.setDate(date.getDate() + days); return localDate(date); };
const monday = value => { const date = dateFrom(value); return addDays(value, -(date.getDay() + 6) % 7); };
const today = localDate(new Date());
const state = {recipes: [], entries: [], week: monday(today), view: "recipes", category: "", search: "", sort: "recent", selections: [], items: []};
state.checked = new Set();
const itemKey = item => JSON.stringify([item.name.toLowerCase(), item.unit, item.amount]);
const countLabel = (count, noun) => count + " " + noun + (count === 1 ? "" : "s");
const meals = ["Breakfast", "Lunch", "Dinner", "Snack"];
const dialog = $("#dialog");
let toastTimer, detailRequest = 0, shoppingRequest = 0, planRequest = 0;
$("#today").textContent = new Date().toLocaleDateString("en-US", {weekday: "long", month: "long", day: "numeric"});

async function api(path, method = "GET", data) {
  const response = await fetch("/api" + path, {
    method, headers: {"Content-Type": "application/json", "X-Recipe-Manager": "1"},
    body: data === undefined ? undefined : JSON.stringify(data)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Something went wrong. Please try again.");
  return result;
}
function report(error) {
  const target = dialog.open ? $("#form-error") : $("#page-error");
  if (target) { target.textContent = error.message; target.hidden = false; }
  else toast(error.message);
}
function toast(message) {
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $("#toast").hidden = true; }, 4000);
}
function recipeById(id) {
  const recipe = state.recipes.find(item => item.id === Number(id));
  if (!recipe) throw new Error("This recipe is no longer available. Reload the collection.");
  return recipe;
}
function foodArt(category) {
  const cat = category.toLowerCase();
  let food;
  if (cat.includes("breakfast")) {
    food = '<ellipse cx="160" cy="115" rx="67" ry="29" fill="#b87936"/><ellipse cx="160" cy="106" rx="67" ry="29" fill="#e7b25c"/><ellipse cx="160" cy="98" rx="63" ry="27" fill="#bd803a"/><ellipse cx="160" cy="90" rx="63" ry="26" fill="#efc474"/><path d="M118 78q45-21 86 8c-2 11-19 5-18 18s-15 11-18-1-25-6-31-9-22 0-19-16" fill="#a85f28"/><path d="m149 70 25-3 5 16-24 5Z" fill="#f9de91"/><circle cx="110" cy="128" r="8" fill="#485367"/><circle cx="99" cy="115" r="7" fill="#59657a"/><circle cx="206" cy="119" r="8" fill="#4a5570"/>';
  } else if (cat.includes("dessert")) {
    food = '<path d="m116 66 84 35v37l-84-34Z" fill="#c28b5c"/><path d="m116 67 84 34 30-28-83-28Z" fill="#f4debd"/><path d="m200 101 30-28v37l-30 28Z" fill="#a56a4c"/><path d="m117 80 83 34 30-27v10l-30 28-83-33Z" fill="#f9eee0"/><path d="m136 60 28 7 16-10-27-8Z" fill="#ad6247"/><circle cx="167" cy="57" r="9" fill="#b95740"/><path d="m168 51 8-12" stroke="#64804c" stroke-width="3"/><circle cx="105" cy="131" r="6" fill="#b95740"/>';
  } else if (cat.includes("soup")) {
    food = '<ellipse cx="160" cy="98" rx="68" ry="44" fill="#e6dcc3"/><path d="M92 98q3 60 68 61t68-61" fill="#e6dcc3"/><ellipse cx="160" cy="94" rx="64" ry="36" fill="#b86235"/><ellipse cx="160" cy="92" rx="58" ry="31" fill="#de9854"/><path d="M133 82q-12 15 14 19t33-16q-15-10-26 4" stroke="#f4de9c" stroke-width="3" fill="none"/><path d="m156 88 4-12 9 11-12 8-10-11Z" fill="#567e46"/><circle cx="190" cy="100" r="4" fill="#567e46"/><path d="m125 38 4-16m25 13 4-16" stroke="#fffdf4" stroke-width="3" stroke-linecap="round"/>';
  } else if (cat.includes("snack")) {
    food = '<path d="m106 70 52-24 64 57-52 28Z" fill="#c79653"/><path d="m106 70 64 56v13l-64-53Z" fill="#ab7544"/><path d="m115 73 43-18 53 47-42 22Z" fill="#e7d3a1"/><path d="m125 74 31-12 43 40-30 15Z" fill="#8caa62"/><path d="m134 73 38 37m-27-42 38 36m-30-28 38 32" stroke="#c3d795" stroke-width="5" stroke-linecap="round"/><circle cx="212" cy="132" r="12" fill="#c56f48"/><path d="m210 121 5 5 4-7" stroke="#5b7948" stroke-width="3" fill="none"/>';
  } else {
    food = '<path d="M113 71q-26 11-4 27t-6 24q26 22 54-9t15-51q-36-15-59 9" fill="#8aa263"/><path d="M162 68q23-16 43 6t-1 33q-28 4-42-39" fill="#d7ad68"/><path d="m173 69 21 28m-10-31 19 21" stroke="#b68a49" stroke-width="3"/><ellipse cx="170" cy="125" rx="33" ry="18" fill="#e9ddad"/><path d="m151 121 9-3m2 10 8-2m5-7 9 3" stroke="#c5b77c" stroke-width="2"/><circle cx="123" cy="81" r="11" fill="#c96e4a"/><circle cx="116" cy="113" r="9" fill="#cf8456"/><path d="m129 105 22-20m-21 18 1-13m0 13 13 2" stroke="#496b43" stroke-width="3"/>';
  }
  return '<svg aria-hidden="true" viewBox="0 0 320 180"><ellipse cx="165" cy="149" rx="94" ry="13" fill="#273c3010"/><path d="M21 51q15 31 48 28M37 44q-3 19 12 26m11-35q-17 12-10 34" fill="none" stroke="#a6b28c" stroke-width="2"/><path d="m267 112 28 39" stroke="#baac8d" stroke-width="3"/><path d="m272 107 27 37m-23-41 27 37" stroke="#baac8d" stroke-width="2"/><ellipse cx="160" cy="103" rx="88" ry="60" fill="#fffdf5"/><ellipse cx="160" cy="103" rx="77" ry="50" fill="#f3f0e3" stroke="#e5decc"/>' + food + '<circle cx="256" cy="43" r="3" fill="#b29a6c"/><circle cx="250" cy="52" r="2" fill="#b29a6c"/></svg>';
}
$("#hero-art").innerHTML = '<svg viewBox="0 0 360 310"><circle cx="215" cy="160" r="119" fill="#dde5ce"/><path d="m296 74 24-47m-17 32q-28-2-22-25 24 0 22 25m6-13q29 0 22-23-23 1-22 23" fill="#93a57e" stroke="#748d62" stroke-width="2"/><path d="m69 244 31-42m-22 31q-25-1-17-23 21 0 17 23m10-12q26 2 26-20-20-1-26 20" fill="#93a57e" stroke="#748d62" stroke-width="2"/><ellipse cx="213" cy="252" rx="103" ry="13" fill="#566c4214"/><path d="m89 91 17-6 22 55-12 5Z" fill="#cfb37a"/><path d="m89 91 17-6-10-30-6 2 6 19-5 2-6-19-5 2Z" fill="#cfb37a"/><g transform="translate(27 58) rotate(-9 160 100)">' + foodArt("Main dishes").replace('<svg aria-hidden="true" viewBox="0 0 320 180">', "").replace("</svg>", "") + '</g><circle cx="286" cy="224" r="22" fill="#c4794c"/><path d="m278 206 9 7 5-13" fill="none" stroke="#687c50" stroke-width="4"/><path d="M161 38q-27-16-39 7 18 12 39-7" fill="#a5b58b"/></svg>';

function categoryOptions(selected = "") {
  const categories = [...new Set(state.recipes.map(r => r.category || "Uncategorized"))].sort();
  return categories.map(c => '<option value="' + escape(c) + '"' + (c === selected ? " selected" : "") + '>' + escape(c) + '</option>').join("");
}
function recipeOptions(selected) {
  return state.recipes.map(r => '<option value="' + r.id + '"' + (r.id === Number(selected) ? " selected" : "") + '>' + escape(r.title) + '</option>').join("");
}
function renderRecipes() {
  $("#nav-count").textContent = state.recipes.length;
  $("#collection-count").textContent = state.recipes.length;
  const counts = new Map();
  state.recipes.forEach(r => { const c = r.category || "Uncategorized"; counts.set(c, (counts.get(c) || 0) + 1); });
  if (state.category && !counts.has(state.category)) state.category = "";
  const chip = (label, value, count) => '<button class="chip' + (value === state.category ? " active" : "") + '" data-category="' + escape(value) + '" aria-pressed="' + (value === state.category) + '">' + escape(label) + '<small>' + count + '</small></button>';
  $("#categories").innerHTML = chip("All recipes", "", state.recipes.length) + [...counts.entries()].sort().map(([c, n]) => chip(c, c, n)).join("");
  const items = state.recipes.filter(r => (!state.category || (r.category || "Uncategorized") === state.category) && r.title.toLowerCase().includes(state.search.trim().toLowerCase()));
  items.sort(state.sort === "name" ? (a, b) => a.title.localeCompare(b.title, "en") : (a, b) => b.id - a.id);
  $("#collection-caption").textContent = countLabel(items.length, "recipe") + " to make your own.";
  $("#recipe-grid").innerHTML = items.map(r => '<article class="recipe-card"><button class="card-open" data-action="detail" data-id="' + r.id + '" aria-label="View ' + escape(r.title) + '"><div class="food-art tone-' + (r.id % 4) + '">' + foodArt(r.category || "") + '<span class="card-category">' + escape(r.category || "Uncategorized") + '</span></div><div class="card-body"><h3>' + escape(r.title) + '</h3><p class="card-meta">' + icon("people") + countLabel(r.servings, 'serving') + '<span class="dot">·</span>' + countLabel(r.ingredients.length, 'ingredient') + '</p></div></button><div class="card-footer"><button class="text-button" data-action="plan-recipe" data-id="' + r.id + '">' + icon("calendar") + 'Add to week</button><button class="icon-button" data-action="edit-recipe" data-id="' + r.id + '" aria-label="Edit ' + escape(r.title) + '">' + icon("edit") + '</button></div></article>').join("") || '<div class="empty"><strong>' + (state.recipes.length ? "No recipes found." : "Your next favorite starts here.") + '</strong>' + (state.recipes.length ? "Try a different name or category." : 'Add your first recipe to start your collection.<br><button class="primary" data-action="new-recipe">Add a recipe</button>') + '</div>';
  const previous = $("#shopping-recipe").value;
  $("#shopping-recipe").innerHTML = recipeOptions(previous);
  $("#shopping-add button").disabled = !state.recipes.length;
}
function weekLabel() {
  const start = dateFrom(state.week), end = dateFrom(addDays(state.week, 6));
  return start.toLocaleDateString("en-US", {month: "short", day: "numeric"}) + " – " + end.toLocaleDateString("en-US", {month: "short", day: "numeric", year: "numeric"});
}
function renderPlan() {
  $("#week-title").textContent = weekLabel();
  $("#week-date").value = state.week;
  $("#shopping-week").textContent = weekLabel();
  const days = new Set(state.entries.map(entry => entry.day)).size;
  $("#plan-summary").textContent = countLabel(state.entries.length, "meal") + " planned · " + days + " of 7 days";
  $("#week-board").innerHTML = Array.from({length: 7}, (_, i) => {
    const day = addDays(state.week, i), date = dateFrom(day);
    return '<section class="day-column' + (day === today ? " is-today" : "") + '"><header class="day-heading"><span>' + date.toLocaleDateString("en-US", {weekday: "short"}) + '</span><strong>' + date.getDate() + '</strong></header>' + meals.map(meal => {
      const entries = state.entries.filter(entry => entry.day === day && entry.meal === meal);
      const add = ' data-action="new-meal" data-day="' + day + '" data-meal="' + meal + '"';
      return '<div class="meal-slot"><div class="slot-label">' + meal + '<button' + add + ' aria-label="Add ' + meal + ' on ' + day + '">' + icon("plus") + '</button></div>' + (entries.map(entry => '<article class="planned-meal"><button data-action="detail" data-id="' + entry.recipe_id + '">' + escape(entry.recipe.title) + '</button><p>' + countLabel(entry.servings, 'serving') + '</p><button class="meal-remove" data-action="remove-meal" data-id="' + entry.id + '" aria-label="Remove ' + escape(entry.recipe.title) + ' from ' + day + '">' + icon("close") + '</button></article>').join("") || '<button class="empty-slot"' + add + '>+ Add meal</button>') + '</div>';
    }).join("") + '</section>';
  }).join("");
}
async function loadPlan(week = state.week) {
  const request = ++planRequest;
  const plan = await api("/meals?week=" + encodeURIComponent(week));
  if (request !== planRequest) return;
  state.week = plan.week; state.entries = plan.entries; renderPlan();
}
async function refresh() {
  state.recipes = await api("/recipes");
  renderRecipes();
  await loadPlan();
}
function navigate(view) {
  if (!["recipes", "planner", "shopping"].includes(view)) view = "recipes";
  state.view = view;
  document.querySelectorAll(".view").forEach(node => { node.hidden = node.id !== view + "-view"; });
  document.querySelectorAll("[data-view]").forEach(button => {
    button.classList.toggle("active", button.dataset.view === view);
    if (button.dataset.view === view) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  $("#breadcrumb").textContent = "My kitchen / " + ({recipes: "Recipe collection", planner: "Weekly planner", shopping: "Shopping list"})[view];
  history.replaceState(null, "", "#" + view);
  $("#page-error").hidden = true;
  window.scrollTo({top: 0});
}
function openDialog(title, eyebrow, body, footer = "") {
  if (dialog.open) dialog.close();
  $("#dialog-content").innerHTML = '<header class="dialog-header"><div><p class="eyebrow">' + eyebrow + '</p><h2 id="dialog-title">' + escape(title) + '</h2></div><button class="icon-button" data-action="close" aria-label="Close dialog">' + icon("close") + '</button></header><div class="dialog-body"><div id="form-error" class="form-error" role="alert" hidden></div>' + body + '</div>' + (footer ? '<footer class="dialog-footer">' + footer + '</footer>' : "");
  dialog.setAttribute("aria-labelledby", "dialog-title");
  dialog.showModal();
}
function ingredientRow(item = {name: "", quantity: "", unit: "g"}) {
  return '<div class="ingredient-row"><label>Ingredient<input name="ingredient-name" value="' + escape(item.name) + '" required placeholder="e.g. Flour"></label><label>Amount<input name="ingredient-quantity" type="number" min="0.000000001" max="1000000000" step="any" value="' + escape(item.quantity) + '" required></label><label>Unit<input name="ingredient-unit" value="' + escape(item.unit) + '" required placeholder="g, ml…"></label><button class="icon-button" type="button" data-action="remove-row" aria-label="Remove ingredient">' + icon("close") + '</button></div>';
}
function stepRow(step = "") {
  return '<div class="step-row"><label>Direction<textarea name="step" required placeholder="Describe the next step…">' + escape(step) + '</textarea></label><button class="icon-button" type="button" data-action="remove-row" aria-label="Remove direction">' + icon("close") + '</button></div>';
}
function editRecipe(id) {
  const r = id ? recipeById(id) : {title: "", category: "", servings: 2, ingredients: [{name: "", quantity: "", unit: "g"}], steps: [""]};
  openDialog(id ? "A little recipe refinement." : "Something worth keeping.", id ? "EDIT YOUR RECIPE" : "ADD TO YOUR COLLECTION",
    '<form id="recipe-form" data-id="' + (id || "") + '"><label>Recipe name<input name="title" required value="' + escape(r.title) + '" placeholder="What are we making?"></label><div class="form-row"><label>Category<input name="category" list="category-options" value="' + escape(r.category || "") + '" placeholder="e.g. Breakfast"><datalist id="category-options">' + categoryOptions() + '</datalist></label><label>Servings<input name="servings" type="number" min="1" max="10000" required value="' + r.servings + '"></label></div><div class="form-section"><div class="panel-heading"><h3>Ingredients</h3><button class="text-button" type="button" data-action="add-ingredient">' + icon("plus") + 'Add ingredient</button></div><div id="ingredient-rows">' + r.ingredients.map(ingredientRow).join("") + '</div></div><div class="form-section"><div class="panel-heading"><h3>Directions</h3><button class="text-button" type="button" data-action="add-step">' + icon("plus") + 'Add step</button></div><div id="step-rows">' + r.steps.map(stepRow).join("") + '</div></div></form>',
    '<button class="secondary" data-action="close">Cancel</button><button class="primary" type="submit" form="recipe-form">Save recipe</button>');
}
async function detail(id) {
  const r = recipeById(id);
  openDialog(r.title, escape(r.category || "YOUR RECIPE"),
    '<div class="serving-control"><label for="detail-servings">Cooking for</label><input id="detail-servings" data-id="' + r.id + '" type="number" min="1" max="10000" value="' + r.servings + '"><span>servings</span></div><p class="footnote detail-note">Ingredient preview only. Cooking times and saved quantities stay the same.</p><div class="detail-columns"><section><h3>Ingredients</h3><div id="detail-ingredients">Loading ingredients…</div></section><section><h3>Let’s make it</h3><ol class="detail-steps">' + r.steps.map(step => '<li>' + escape(step) + '</li>').join("") + '</ol></section></div>',
    '<button class="danger-text" data-action="delete-recipe" data-id="' + r.id + '">Delete recipe</button><button class="secondary" data-action="edit-recipe" data-id="' + r.id + '">' + icon("edit") + 'Edit</button><button class="primary" data-action="plan-recipe" data-id="' + r.id + '">' + icon("calendar") + 'Add to week</button>');
  await updateDetail();
}
async function updateDetail() {
  const input = $("#detail-servings");
  if (!input || !input.reportValidity()) return;
  const request = ++detailRequest, id = input.dataset.id;
  const items = await api("/recipes/" + id + "/scale?servings=" + encodeURIComponent(input.value));
  if (request !== detailRequest || !$("#detail-servings") || $("#detail-servings").dataset.id !== id) return;
  $("#detail-ingredients").innerHTML = items.map(item => '<div class="detail-ingredient"><span>' + escape(item.name) + '</span><strong>' + escape(item.amount) + '</strong></div>').join("");
}
function newMeal(id, day, meal = "Dinner") {
  if (!state.recipes.length) { toast("Add a recipe before planning a meal."); return; }
  const r = id ? recipeById(id) : state.recipes[0];
  openDialog("Make room for something good.", "PLAN A MEAL",
    '<form id="meal-form"><label>Recipe<select name="recipe_id" id="meal-recipe">' + recipeOptions(r.id) + '</select></label><div class="form-row"><label>Date<input type="date" name="day" required value="' + (day || (today >= state.week && today <= addDays(state.week, 6) ? today : state.week)) + '"></label><label>Servings<input name="servings" id="meal-servings" type="number" min="1" max="10000" required value="' + r.servings + '"></label></div><label>Meal<select name="meal">' + meals.map(m => '<option' + (m === meal ? " selected" : "") + '>' + m + '</option>').join("") + '</select></label></form>',
    '<button class="secondary" data-action="close">Cancel</button><button class="primary" type="submit" form="meal-form">Add to planner</button>');
}
function confirmDelete(kind, id) {
  const isRecipe = kind === "recipe";
  const item = isRecipe ? recipeById(id) : state.entries.find(entry => entry.id === Number(id));
  const title = isRecipe ? item.title : item.recipe.title;
  openDialog(isRecipe ? "Delete this recipe?" : "Remove this planned meal?", "ONE LAST CHECK",
    '<p class="confirm-copy">' + escape(title) + '<br>' + (isRecipe ? "<strong>This permanently deletes the recipe.</strong> Recipes used in a meal plan must be removed from those plans first." : "This removes the meal from this week. Your recipe stays in the collection.") + '</p>',
    '<button class="secondary" data-action="close">Keep it</button><button class="danger-button" data-action="confirm-' + kind + '" data-id="' + id + '">' + (isRecipe ? "Delete recipe" : "Remove meal") + '</button>');
}
async function renderShopping() {
  const request = ++shoppingRequest;
  const selections = state.selections.map(entry => ({recipe_id: entry.recipe_id, servings: entry.servings}));
  const items = await api("/shopping", "POST", {selections});
  if (request !== shoppingRequest) return;
  state.items = items;
  const currentKeys = new Set(items.map(itemKey));
  state.checked = new Set([...state.checked].filter(key => currentKeys.has(key)));
  $("#shopping-selections").innerHTML = state.selections.map((entry, i) => '<div class="shopping-selection"><span class="selection-name">' + escape(recipeById(entry.recipe_id).title) + '<small>' + countLabel(entry.servings, 'serving') + '</small></span><button class="icon-button" data-action="remove-selection" data-index="' + i + '" aria-label="Remove ' + escape(recipeById(entry.recipe_id).title) + ' from shopping list">' + icon("close") + '</button></div>').join("");
  $("#shopping-items").innerHTML = items.map((item, index) => '<label class="check-item"><input type="checkbox" data-index="' + index + '"' + (state.checked.has(itemKey(item)) ? " checked" : "") + '><span class="ingredient-name">' + escape(item.name) + '</span><span class="ingredient-amount">' + escape(item.amount) + '</span></label>').join("") || '<div class="empty"><strong>A fresh start.</strong>Add a recipe or bring in your weekly plan.<br>Your ingredients will appear here.</div>';
  updateProgress();
}
function updateProgress() {
  const checked = [...document.querySelectorAll("#shopping-items input:checked")];
  state.checked = new Set(checked.map(input => itemKey(state.items[Number(input.dataset.index)])));
  const done = checked.length;
  $("#shopping-progress").textContent = state.items.length ? done + " of " + state.items.length + " ingredients checked · " + countLabel(state.selections.length, "recipe") : "Add a recipe to get started.";
}
const actions = {
  "new-recipe": () => editRecipe(),
  "edit-recipe": button => editRecipe(button.dataset.id),
  detail: button => detail(button.dataset.id),
  close: () => dialog.close(),
  "add-ingredient": () => { $("#ingredient-rows").insertAdjacentHTML("beforeend", ingredientRow()); $("#ingredient-rows").lastElementChild.querySelector("input").focus(); },
  "add-step": () => { $("#step-rows").insertAdjacentHTML("beforeend", stepRow()); $("#step-rows").lastElementChild.querySelector("textarea").focus(); },
  "remove-row": button => { const row = button.closest(".ingredient-row, .step-row"); if (row.parentElement.children.length > 1) row.remove(); else toast("Keep at least one ingredient and one direction."); },
  "new-meal": button => newMeal(null, button.dataset.day, button.dataset.meal),
  "plan-recipe": button => {
    const preview = $("#detail-servings");
    const servings = preview && preview.checkValidity() ? Number(preview.value) : null;
    newMeal(button.dataset.id);
    if (servings) $("#meal-servings").value = servings;
  },
  "delete-recipe": button => confirmDelete("recipe", button.dataset.id),
  "remove-meal": button => confirmDelete("meal", button.dataset.id),
  "confirm-recipe": async button => {
    const id = Number(button.dataset.id);
    await api("/recipes/" + id, "DELETE");
    state.selections = state.selections.filter(entry => entry.recipe_id !== id);
    dialog.close(); await refresh(); await renderShopping(); toast("Recipe deleted.");
  },
  "confirm-meal": async button => { await api("/meals/" + button.dataset.id + "?week=" + state.week, "DELETE"); dialog.close(); await loadPlan(); toast("Meal removed. Your recipe is still saved."); },
  "previous-week": () => loadPlan(addDays(state.week, -7)),
  "next-week": () => loadPlan(addDays(state.week, 7)),
  "this-week": () => loadPlan(monday(today)),
  "week-shopping": async () => {
    await loadPlan();
    state.selections = state.entries.map(entry => ({recipe_id: entry.recipe_id, servings: entry.servings}));
    await renderShopping(); navigate("shopping"); toast(state.entries.length ? "Shopping list updated from " + weekLabel() + "." : "No meals planned for this week yet.");
  },
  "remove-selection": async button => { state.selections.splice(Number(button.dataset.index), 1); await renderShopping(); },
  print: () => { if (state.items.length) window.print(); else toast("Add some ingredients before printing."); }
};
document.addEventListener("click", async event => {
  const button = event.target.closest("button");
  if (!button || button.disabled) return;
  try {
    if (button.dataset.view) navigate(button.dataset.view);
    if ("category" in button.dataset) { state.category = button.dataset.category; renderRecipes(); }
    const action = actions[button.dataset.action];
    if (action) {
      button.disabled = true;
      await action(button);
    }
  } catch (error) { report(error); }
  finally { button.disabled = false; }
});
document.addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.target, submit = event.submitter;
  if (form.dataset.busy) return;
  form.dataset.busy = "true";
  if (submit) submit.disabled = true;
  const errorBox = $("#form-error"); if (errorBox) errorBox.hidden = true;
  try {
    const data = new FormData(form);
    if (form.id === "recipe-form") {
      const recipe = {
        title: data.get("title").trim(), servings: Number(data.get("servings")),
        ingredients: [...form.querySelectorAll(".ingredient-row")].map(row => ({
          name: $('[name="ingredient-name"]', row).value.trim(),
          quantity: Number($('[name="ingredient-quantity"]', row).value),
          unit: $('[name="ingredient-unit"]', row).value.trim()
        })), steps: data.getAll("step").map(step => step.trim())
      };
      if (data.get("category").trim()) recipe.category = data.get("category").trim();
      await api("/recipes" + (form.dataset.id ? "/" + form.dataset.id : ""), form.dataset.id ? "PUT" : "POST", recipe);
      dialog.close(); await refresh(); await renderShopping(); toast("Recipe saved. Something delicious to come back to.");
    } else if (form.id === "meal-form") {
      await api("/meals", "POST", {day: data.get("day"), meal: data.get("meal"), recipe_id: Number(data.get("recipe_id")), servings: Number(data.get("servings"))});
      dialog.close(); await loadPlan(data.get("day")); navigate("planner"); toast("Meal added to your week.");
    } else if (form.id === "shopping-add") {
      state.selections.push({recipe_id: Number($("#shopping-recipe").value), servings: Number($("#shopping-servings").value)});
      await renderShopping(); toast("Recipe added to your shopping list.");
    }
  } catch (error) { report(error); }
  finally { delete form.dataset.busy; if (submit) submit.disabled = false; }
});
$("#search").addEventListener("input", event => { state.search = event.target.value; renderRecipes(); });
$("#sort").addEventListener("change", event => { state.sort = event.target.value; renderRecipes(); });
document.addEventListener("input", event => {
  if (event.target.id === "detail-servings" && event.target.value && event.target.checkValidity()) {
    updateDetail().catch(report);
  }
});
document.addEventListener("change", async event => {
  try {
    if (event.target.id === "week-date") await loadPlan(event.target.value);
    if (event.target.id === "detail-servings") await updateDetail();
    if (event.target.id === "meal-recipe") $("#meal-servings").value = recipeById(event.target.value).servings;
    if (event.target.id === "shopping-recipe") $("#shopping-servings").value = recipeById(event.target.value).servings;
    if (event.target.matches("#shopping-items input")) updateProgress();
  } catch (error) { report(error); }
});
window.addEventListener("hashchange", () => navigate(location.hash.slice(1)));
async function init() {
  navigate(location.hash.slice(1));
  try { await refresh(); if (state.recipes.length) $("#shopping-servings").value = state.recipes[0].servings; await renderShopping(); }
  catch (error) { report(error); $("#recipe-grid").innerHTML = '<div class="empty"><strong>Your kitchen could not be opened.</strong>Check that the local application is running, then reload this page.</div>'; }
}
init();
