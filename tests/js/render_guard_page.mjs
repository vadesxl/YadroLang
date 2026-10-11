// Headless smoke test for the Guard tab: a tiny fake React renders the real
// component tree with realistic backend data, clicks the decision buttons and
// checks what was sent. Run: node tests/js/render_guard_page.mjs <index.js>
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(process.argv[2], "utf8");
const posted = [];
const GH_PREVIEW = "ghp_…ab12";
const incidents = {
  status: "ok", pending: 1, items: [
    { id: "YG-1A2B3C", status: "pending", at: Math.floor(Date.now() / 1000) - 30, attempts: 2,
      tool: "terminal", destination: "shell: curl",
      agent: { session_id: "sess-123", task_id: "task-9" }, process: { pid: 4242, name: "hermes" },
      findings: [{ kind: "github_token", label: "Credentials", title: "GitHub access token", preview: GH_PREVIEW,
                   path: "command", token: "yg_tok_Credentials_0123456789abcdef" }] },
    { id: "YG-OLD001", status: "quarantined", at: 1, attempts: 1, tool: "http_request",
      destination: "https://x.example", agent: {}, findings: [] }] };
const vault = { status: "ok", items: [{ token: "yg_tok_PII_aa", label: "PII", title: "Email", created: 1, source: "manual" }] };

// ---- fake React with hooks (single render pass, re-render on state change) ----
let hooks = [], hi = 0, rerender = null;
const React = {
  createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat(Infinity) }),
  Fragment: "FRAGMENT",
  useState(init) {
    const i = hi++;
    if (!(i in hooks)) hooks[i] = typeof init === "function" ? init() : init;
    return [hooks[i], (v) => { hooks[i] = typeof v === "function" ? v(hooks[i]) : v; if (rerender) queueMicrotask(rerender); }];
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
        throw new Error("unexpected GET " + url);
      },
    },
  },
};
vm.createContext(sandbox);
vm.runInContext(src, sandbox);
if (!Page) throw new Error("plugin did not register 'yadro-guard'");

function render() {
  hi = 0;
  const expand = (n) => {
    if (n == null || n === false || n === true) return [];
    if (typeof n === "string" || typeof n === "number") return [String(n)];
    if (Array.isArray(n)) return n.flatMap(expand);
    if (typeof n.type === "function") return expand(n.type({ ...n.props, children: n.children }));
    return [{ ...n, children: n.children.flatMap(expand) }];
  };
  return expand(React.createElement(Page, null));
}
const text = (nodes) => nodes.map((n) => (typeof n === "string" ? n : text(n.children))).join("");
const find = (nodes, pred, out = []) => { for (const n of nodes) if (typeof n !== "string") { if (pred(n)) out.push(n); find(n.children, pred, out); } return out; };
const tick = () => new Promise((r) => setTimeout(r, 5));

let tree = render(); rerender = () => { tree = render(); };
await tick(); await tick(); tree = render();
const all = text(tree);
const must = ["YADRO GUARD", "Live protection (1)", "1 action blocked", "YG-1A2B3C", "GitHub access token", GH_PREVIEW,
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

for (const [label, needle] of [["Check code", "Paste a program"], ["Vault", "Protect this secret"]]) {
  find(tree, (n) => n.type === "button" && text(n.children).startsWith(label))[0].props.onClick();
  await tick(); tree = render();
  if (!text(tree).includes(needle)) throw new Error(`tab ${label} did not render`);
}
console.log("OK guard page rendered, decision posted, tabs work");
