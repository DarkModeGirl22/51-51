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
  kids: { label: "Kids" }, home: { label: "Home" }, money: { label: "Money" }, unsorted: { label: "To sort" },
};

// Small line icons (no emoji), drawn as SVG.
const ICON_PATHS = {
  kids: ["M9 7.5a2.5 2.5 0 1 0 0-.01", "M4.5 20v-1.5a4.5 4.5 0 0 1 9 0V20", "M17 10a2 2 0 1 0 0-.01", "M15 20v-1a3.5 3.5 0 0 1 5.5-2.9"],
  home: ["M3.5 11 12 4l8.5 7", "M6 9.5V20h12V9.5", "M10 20v-5h4v5"],
  money: ["M3.5 6.5h17v11h-17z", "M12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 1 0 0-5", "M6.5 9.5v5M17.5 9.5v5"],
  unsorted: ["M12 4a8 8 0 1 0 0 16 8 8 0 1 0 0-16", "M12 8v5M12 16h.01"],
  bell: ["M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 1.5h-15z", "M10 20.5a2 2 0 0 0 4 0"],
  talk: ["M4 5h16v11H10l-5 4v-4H4z"],
  camera: ["M4 8h3.5l2-2.5h5l2 2.5H20v11H4z", "M12 10.5a3 3 0 1 0 0 6 3 3 0 1 0 0-6"],
  receipt: ["M6 3h12v18l-3-1.8-3 1.8-3-1.8L6 21z", "M9 8h6M9 12h6M9 16h3"],
  heart: ["M12 20s-7.5-4.6-7.5-10.2A4.2 4.2 0 0 1 12 7.3a4.2 4.2 0 0 1 7.5 2.5C19.5 15.4 12 20 12 20z"],
};
function icon(name) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "ico");
  svg.setAttribute("aria-hidden", "true");
  for (const d of ICON_PATHS[name] || ICON_PATHS.unsorted) {
    const p = document.createElementNS(ns, "path");
    p.setAttribute("d", d);
    svg.append(p);
  }
  return svg;
}

function isToday(iso) {
  const d = new Date(iso), n = new Date();
  return d.getFullYear() === n.getFullYear() && d.getMonth() === n.getMonth() && d.getDate() === n.getDate();
}
function timeOf(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
