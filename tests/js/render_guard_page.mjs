// Headless smoke test for the Guard tab: a tiny fake React renders the real
// component tree with realistic backend data, clicks the decision buttons and
// checks what was sent. Run: node tests/js/render_guard_page.mjs <index.js>
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(process.argv[2], "utf8");
const posted = [];
const GH_PREVIEW = "ghp_…ab12";
const incidents = {
  status: "ok", pending: 2, items: [
    { id: "YG-1A2B3C", status: "pending", at: Math.floor(Date.now() / 1000) - 30, attempts: 2,
      tool: "terminal", destination: "shell: curl",
      agent: { session_id: "sess-123", task_id: "task-9" }, process: { pid: 4242, name: "hermes" },
      findings: [{ kind: "github_token", label: "Credentials", title: "GitHub access token", preview: GH_PREVIEW,
                   path: "command", token: "yg_tok_Credentials_0123456789abcdef" }] },
    { id: "YG-ACT777", status: "pending", at: 5, attempts: 1, tool: "terminal", destination: "shell: ollama", kind: "action",
      agent: { session_id: "sess-777" }, findings: [],
      risks: [{ kind: "expose_bind_all", title: "Starts a server open to the whole network", why: "Any device can connect.",
                safer: "Use --host 127.0.0.1", snippet: "ollama serve --host 0.0.0.0" }] },
    { id: "YG-OLD001", status: "quarantined", at: 1, attempts: 1, tool: "http_request",
      destination: "https://x.example", agent: {}, findings: [] }] };
const exposure = { status: "ok", score: 70, scanned_at: 1, counts: { critical: 1, high: 0, medium: 1, low: 0, info: 1 },
  limits: ["It cannot see port forwarding on your router."],
  listeners: [
    { proto: "TCP", address: "0.0.0.0", port: 5432, pid: 700, process: "postgres.exe", reach: "all_networks",
      service: "PostgreSQL database", severity: "critical", why: "An open database is the classic SaaS data breach.",
      fix: "Set listen_addresses='localhost'.", firewall: "allowed", tags: ["firewall-allows"] },
    { proto: "TCP", address: "127.0.0.1", port: 18434, pid: 1, process: "llama-server.exe", reach: "this_computer",
      service: "llama.cpp server", severity: "info", why: "safe", fix: "Nothing to do.", firewall: "not needed", tags: [] }] };
const vault = { status: "ok", items: [{ token: "yg_tok_PII_aa", label: "PII", title: "Email", created: 1, source: "manual" }] };

// ---- fake React with hooks (single render pass, re-render on state change) ----
// Hooks are stored per component instance (keyed by its position in the tree),
// like real React, so switching tabs mounts fresh state and runs fresh effects.
const store = new Map();
let hooks = [], hi = 0, rerender = null, live = new Set();
const React = {
  createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat(Infinity) }),
  Fragment: "FRAGMENT",
  useState(init) {
    const slot = hooks, i = hi++;
    if (!(i in slot)) slot[i] = typeof init === "function" ? init() : init;
    return [slot[i], (v) => { slot[i] = typeof v === "function" ? v(slot[i]) : v; if (rerender) queueMicrotask(rerender); }];
  },
  useRef(init) { const i = hi++; if (!(i in hooks)) hooks[i] = { current: init }; return hooks[i]; },
  useCallback(fn) { hi++; return fn; },
  useEffect(fn) { const i = hi++; if (!(i in hooks)) { hooks[i] = true; queueMicrotask(fn); } },
};
let Page = null;
const sandbox = {
  console, queueMicrotask, setInterval: () => 1, clearInterval: () => {}, Date, Math, JSON, String, Promise,
  document: { hidden: false },
  window: {
    __HERMES_PLUGINS__: { register: (name, c) => { if (name === "yadro-guard") Page = c; } },
    __HERMES_PLUGIN_SDK__: {
      React,
      fetchJSON: async (url, init) => {
        if (init && init.method === "POST") { posted.push({ url, body: JSON.parse(init.body) });
          return { status: "ok", next: "Ask the agent to try again." }; }
        if (url.endsWith("/incidents")) return incidents;
        if (url.endsWith("/vault")) return vault;
        if (url.includes("/exposure")) return exposure;
        throw new Error("unexpected GET " + url);
      },
    },
  },
};
vm.createContext(sandbox);
vm.runInContext(src, sandbox);
if (!Page) throw new Error("plugin did not register 'yadro-guard'");

function render() {
  live = new Set();
  const expand = (n, path) => {
    if (n == null || n === false || n === true) return [];
    if (typeof n === "string" || typeof n === "number") return [String(n)];
    if (Array.isArray(n)) return n.flatMap((c, i) => expand(c, path + "/" + i));
    if (typeof n.type === "function") {
      const id = path + ":" + (n.type.name || "anon") + ":" + (n.props.key ?? "");
      live.add(id);
      if (!store.has(id)) store.set(id, []);
      const prevHooks = hooks, prevHi = hi;
      hooks = store.get(id); hi = 0;
      const out = n.type({ ...n.props, children: n.children });
      hooks = prevHooks; hi = prevHi;
      return expand(out, id);
    }
    return [{ ...n, children: n.children.flatMap((c, i) => expand(c, path + "/" + i)) }];
  };
  const tree = expand(React.createElement(Page, null), "root");
  for (const id of [...store.keys()]) if (!live.has(id)) store.delete(id);   // unmount
  return tree;
}
const text = (nodes) => nodes.map((n) => (typeof n === "string" ? n : text(n.children))).join("");
const find = (nodes, pred, out = []) => { for (const n of nodes) if (typeof n !== "string") { if (pred(n)) out.push(n); find(n.children, pred, out); } return out; };
const tick = () => new Promise((r) => setTimeout(r, 5));

let tree = render(); rerender = () => { tree = render(); };
await tick(); await tick(); tree = render();
const all = text(tree);
const actCard = find(tree, (n) => n.props && n.props.className && n.props.className.startsWith("yg-inc ")
  && text(n.children).includes("YG-ACT777"))[0];
if (!actCard) throw new Error("action incident not rendered");
const actText = text(actCard.children);
for (const m of ["Starts a server open to the whole network", "ollama serve --host 0.0.0.0", "Safer: Use --host 127.0.0.1", "⛔ Block", "Allow once"])
  if (!actText.includes(m)) throw new Error("action card missing: " + m);
if (actText.includes("Protect & send")) throw new Error("action incident must not offer Protect & send");
const must = ["YADRO GUARD", "Live protection (2)", "2 actions blocked", "YG-1A2B3C", "GitHub access token", GH_PREVIEW,
  "terminal", "shell: curl", "sess-123", "Protect & send", "Block & quarantine", "Allow once", "pid 4242",
  "Blocked, secret quarantined", "Secret values are never shown or sent"];
for (const m of must) if (!all.includes(m)) throw new Error("missing text: " + m);
if (/[\u0400-\u04FF]/.test(all)) throw new Error("UI must be English only");

const btn = find(tree, (n) => n.type === "button" && text(n.children).includes("Protect & send"))[0];
btn.props.onClick(); await tick(); await tick(); tree = render();
if (!posted.length || posted[0].url !== "/api/plugins/yadro-guard/incidents/decide"
    || posted[0].body.incident !== "YG-1A2B3C" || posted[0].body.choice !== "protect")
  throw new Error("decision not posted correctly: " + JSON.stringify(posted));
if (!text(tree).includes("Ask the agent to try again.")) throw new Error("decision feedback not shown");

for (const [label, needle] of [["Exposure", "PostgreSQL database"], ["Check code", "Paste a program"], ["Vault", "Protect this secret"]]) {
  find(tree, (n) => n.type === "button" && text(n.children).startsWith(label))[0].props.onClick();
  await tick(); tree = render();
  await tick(); tree = render();
  if (!text(tree).includes(needle)) throw new Error(`tab ${label} did not render`);
  if (label === "Exposure") {
    const t = text(tree);
    for (const m of ["Exposure score 70/100", "Open to every network", "postgres.exe", "What to do: Set listen_addresses", "Honest limits of this scan"])
      if (!t.includes(m)) throw new Error("exposure tab missing: " + m);
  }
}
// ---- Russian UI: same page with a Russian system language ----
{
  let PageRu = null;
  const ru = vm.createContext({ ...sandbox, navigator: { language: "ru-RU", languages: ["ru-RU"] },
    window: { ...sandbox.window, __HERMES_PLUGINS__: { register: (n, c) => { PageRu = c; } } } });
  vm.runInContext(src, ru);
  Page = PageRu; store.clear(); rerender = null;
  let t = render(); rerender = () => { t = render(); };
  await tick(); await tick(); t = render();
  const s = text(t);
  for (const m of ["Защита", "Сейф"]) if (!s.includes(m)) throw new Error("Russian UI missing: " + m + " :: " + s.slice(0, 300));
}
console.log("OK guard page rendered, decision posted, tabs work, Russian UI");
