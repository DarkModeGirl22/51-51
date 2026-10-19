// Shared browser logic for 51/51: remembers who you are and talks to the server.
const KEY_NAME = "5151-partner-key";

function getKey() {
  try { return localStorage.getItem(KEY_NAME); } catch (e) { return null; }
}
function setKey(k) {
  try { localStorage.setItem(KEY_NAME, k); } catch (e) { /* private mode: stays in memory only */ }
}
function forget() {
  try { localStorage.removeItem(KEY_NAME); } catch (e) {}
  location.href = "/";
}

async function api(path, options = {}) {
  const headers = options.headers || {};
  const key = getKey();
  if (key) headers["X-Partner-Key"] = key;
  headers["X-TZ-Offset"] = String(new Date().getTimezoneOffset());
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.json);
  }
  const res = await fetch(path, { ...options, headers });
  let data = null;
  try { data = await res.json(); } catch (e) {}
  if (!res.ok) {
    let msg = "Something went wrong. Please try again.";
    if (data && typeof data.detail === "string") msg = data.detail;
    else if (data && Array.isArray(data.detail) && data.detail[0] && data.detail[0].msg)
      msg = String(data.detail[0].msg).replace(/^Value error, /, "");
    else if (data && data.detail) msg = "Please check your answers and try again.";
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of children) if (c != null) node.append(c);
  return node;
}

function whoChip(p) {
  return el("span", { class: "who" }, el("i", { class: "c-" + p.colour }), p.name);
}

const AREAS = {
  kids: { icon: "🧸", label: "Kids" },
  home: { icon: "🏡", label: "Home" },
  money: { icon: "💰", label: "Money" },
  unsorted: { icon: "✨", label: "To sort" },
};

function isToday(iso) {
  const d = new Date(iso), n = new Date();
  return d.getFullYear() === n.getFullYear() && d.getMonth() === n.getMonth() && d.getDate() === n.getDate();
}
function timeOf(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
