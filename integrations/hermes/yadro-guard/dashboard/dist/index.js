/* Yadro Guard — Hermes dashboard tab.
 * Plain IIFE, no build step. React + fetchJSON come from the host via
 * window.__HERMES_PLUGIN_SDK__. All text is rendered through React (auto-escaped);
 * no innerHTML anywhere. HTML reports open in a sandboxed iframe (no scripts). */
(function (SDK, onReady) {
  "use strict";
  if (!SDK || !SDK.React) return;
  const React = SDK.React;
  const h = React.createElement;
  const { useState, useEffect, useCallback, useRef } = React;
  const API = "/api/plugins/yadro-guard";
  const POLL_MS = 4000;

  function post(path, body) {
    return SDK.fetchJSON(API + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }
  function ago(ts) {
    if (!ts) return "";
    const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
    if (s < 60) return s + "s ago";
    if (s < 3600) return Math.floor(s / 60) + " min ago";
    if (s < 86400) return Math.floor(s / 3600) + " h ago";
    return Math.floor(s / 86400) + " d ago";
  }
  const LABEL_COLOR = { Credentials: "#8a5cf6", Financial: "#e8a33d", PII: "#e0533d", Health: "#d14fa0", Location: "#2f9fd8" };
  const STATUS_TEXT = { pending: "Waiting for your decision", protected: "Sent with protection",
    quarantined: "Blocked, secret quarantined", allowed: "Allowed once" };

  function Card(p) {
    return h("div", { className: "yg-card " + (p.className || "") },
      h("b", { className: "yg-hd" }, p.title), p.children);
  }
  function Chip(p) {
    const l = p.label || {};
    return h("span", { className: "yg-chip", style: { background: l.color || LABEL_COLOR[l.id] || "#555" } },
      (l.icon ? l.icon + " " : "") + (l.label || l.id || ""));
  }
  function Pill(p) {
    return h("span", { className: "yg-pill " + p.kind }, p.children);
  }
  function Empty(p) { return h("div", { className: "yg-dim" }, "● " + p.text); }
  function IncidentCard(p) {
    const inc = p.inc;
    const [busy, setBusy] = useState("");
    const [note, setNote] = useState("");
    const pending = inc.status === "pending";
    function choose(choice) {
      setBusy(choice);
      post("/incidents/decide", { incident: inc.id, choice: choice })
        .then(function (r) { setNote(r.status === "ok" ? r.next : (r.message || "Could not save the decision.")); p.onChanged(); })
        .catch(function () { setNote("Could not reach the Guard backend."); })
        .finally(function () { setBusy(""); });
    }
    const who = inc.agent && inc.agent.session_id ? "session " + inc.agent.session_id.slice(0, 12) : "an agent";
    return h("div", { className: "yg-inc " + (pending ? "pending" : "done") },
      h("div", { className: "yg-inc-top" },
        h("span", { className: "yg-inc-id" }, inc.id),
        h(Pill, { kind: pending ? "bad" : inc.status === "quarantined" ? "warn" : "ok" }, STATUS_TEXT[inc.status] || inc.status),
        h("span", { className: "yg-dim yg-right" }, ago(inc.at) + (inc.attempts > 1 ? " · " + inc.attempts + " attempts" : ""))),
      (inc.findings || []).length ? h("div", { className: "yg-inc-story" },
        "Agent ", h("b", null, who), " tried to use the tool ", h("b", { className: "yg-mono" }, inc.tool),
        " to send data to ", h("b", { className: "yg-mono" }, inc.destination), ".") : null,
      (inc.risks || []).map(function (r, i) {
        return h("div", { className: "yg-risk", key: "r" + i },
          h("div", null, "Agent ", h("b", null, who), " tried to: ", h("b", null, r.title), "."),
          h("div", { className: "yg-dim" }, r.why),
          h("div", { className: "yg-diff old" }, r.snippet),
          h("div", { className: "yg-ok yg-small" }, "Safer: " + r.safer));
      }),
      h("div", { className: "yg-inc-what" },
        (inc.findings || []).map(function (f, i) {
          return h("div", { className: "yg-row", key: i },
            h(Chip, { label: { id: f.label, label: f.title } }),
            h("span", { className: "yg-mono yg-dim" }, f.preview + (f.path ? "  in " + f.path : "")),
            f.token ? h("span", { className: "yg-dim" }, "→ " + f.token.slice(0, 24) + "…") : null);
        })),
      inc.process ? h("div", { className: "yg-dim yg-small" },
        "Process: " + (inc.process.name || "?") + " (pid " + inc.process.pid + ")" +
        (inc.agent && inc.agent.task_id ? " · task " + inc.agent.task_id.slice(0, 12) : "")) : null,
      pending ? h("div", { className: "yg-actions" },
        (inc.findings || []).length && !(inc.risks || []).length ? h("button", { className: "yg-btn good", disabled: !!busy,
          onClick: function () { choose("protect"); },
          title: "Replace the secret with a vault token and let the action go through" }, busy === "protect" ? "…" : "🛡 Protect & send") : null,
        h("button", { className: "yg-btn bad", disabled: !!busy, onClick: function () { choose("block"); },
          title: "Keep the action blocked" + ((inc.findings || []).length ? " and store the secret encrypted" : "") },
          busy === "block" ? "…" : ((inc.findings || []).length ? "⛔ Block & quarantine" : "⛔ Block")),
        h("button", { className: "yg-btn ghost", disabled: !!busy, onClick: function () { choose("allow"); },
          title: "Let this exact action run one time (expires in 15 minutes)" }, busy === "allow" ? "…" : "Allow once")) : null,
      note ? h("div", { className: "yg-note-line" }, note) : null);
  }

  function LivePanel(p) {
    const data = p.data;
    if (!data) return h(Card, { title: "live protection", className: "wide" }, h(Empty, { text: "loading…" }));
    if (data.status === "error") return h(Card, { title: "live protection", className: "wide" },
      h("div", { className: "yg-err" }, "● " + data.message));
    const items = data.items || [];
    const pending = items.filter(function (i) { return i.status === "pending"; });
    const done = items.filter(function (i) { return i.status !== "pending"; });
    return h(React.Fragment, null,
      h(Card, { title: "live protection", className: "wide" },
        h("div", { className: "yg-shield " + (pending.length ? "bad" : "ok") },
          h("span", { className: "yg-big" }, pending.length ? "⛔ " + pending.length + " action" + (pending.length > 1 ? "s" : "") + " blocked" : "✓ Protected"),
          h("span", { className: "yg-dim" }, pending.length
            ? "  An agent tried to send sensitive data. Decide below what should happen."
            : "  Every agent action is checked for secrets before it runs.")),
        pending.length ? pending.map(function (inc) { return h(IncidentCard, { key: inc.id, inc: inc, onChanged: p.onChanged }); }) : null),
      h(Card, { title: "incident history", className: "wide" },
        done.length ? done.slice(0, 12).map(function (inc) { return h(IncidentCard, { key: inc.id, inc: inc, onChanged: p.onChanged }); })
          : h(Empty, { text: "No decided incidents yet." })));
  }
  const SAMPLE = "fn main() requires [NetworkAccess] {\n  let key = env.secret()\n  return net.send(key)\n}\n";

  function CheckPanel() {
    const [code, setCode] = useState(SAMPLE);   // prefilled so "Check code" works on first click
    const [title, setTitle] = useState("");
    const [busy, setBusy] = useState(false);
    const [r, setR] = useState(null);
    const [report, setReport] = useState("");
    function analyze() {
      setBusy(true); setReport("");
      post("/analyze", { code: code, title: title })
        .then(setR).catch(function () { setR({ status: "error", message: "Could not reach the Guard backend." }); })
        .finally(function () { setBusy(false); });
    }
    function applyFix() { if (r && r.autofix) { setCode(r.autofix.fixed_code); setR(null); } }
    function openReport() { post("/report", { code: code }).then(function (d) { setReport(d.html || ""); }).catch(function () {}); }
    return h(Card, { title: "check agent code before it runs", className: "wide" },
      h("div", { className: "yg-dim yg-small" }, "Paste a program written in YadroLang (English or Russian keywords). " +
        "Guard proves where sensitive data can leak, before the code ever runs."),
      h("input", { className: "yg-input", placeholder: "Name (optional), e.g. payment agent", value: title,
        onChange: function (e) { setTitle(e.target.value); } }),
      h("textarea", { className: "yg-code-in", spellCheck: false, placeholder: "Paste YadroLang code here", value: code,
        onChange: function (e) { setCode(e.target.value); } }),
      h("div", { className: "yg-actions" },
        h("button", { className: "yg-btn", disabled: busy || !code.trim(), onClick: analyze }, busy ? "Checking…" : "Check code"),
        h("button", { className: "yg-btn ghost", onClick: function () { setCode(SAMPLE); setR(null); } }, "Load example"),
        r && r.status !== "error" ? h("button", { className: "yg-btn ghost", onClick: openReport }, "Open full report") : null),
      r ? h(Result, { r: r, onFix: applyFix }) : null,
      // Inline, not a fixed modal: cards use backdrop-filter, which makes position:fixed
      // relative to the card, so a modal got clipped (seen in Hermes Desktop).
      report ? h("div", { className: "yg-report" },
        h("div", { className: "yg-actions" },
          h("span", { className: "yg-sub" }, "Full report"),
          h("button", { className: "yg-btn ghost yg-right", onClick: function () { setReport(""); } }, "Close report")),
        h("iframe", { className: "yg-frame", sandbox: "", srcDoc: report, title: "report" })) : null);
  }

  function Result(p) {
    const r = p.r;
    if (r.status === "error") return h("div", { className: "yg-err yg-gap" }, "● " + r.message);
    if (r.status === "ok") return h("div", { className: "yg-gap" },
      h("div", { className: "yg-shield ok" }, h("span", { className: "yg-big" }, "✓ No leaks found"),
        h("span", { className: "yg-dim" }, "  in " + r.lines + " lines")),
      (r.sanitized || []).map(function (s, i) {
        return h("div", { className: "yg-row", key: i }, h(Chip, { label: s.label }),
          h("span", { className: "yg-dim" }, "protected on line " + s.line + " with " + s.wrapper + "()"));
      }), h(Gaps, { gaps: r.known_gaps }));
    const a = r.autofix;
    return h("div", { className: "yg-gap" },
      h("div", { className: "yg-shield bad" }, h("span", { className: "yg-big" }, "⛔ Leak on line " + r.line),
        h("span", { className: "yg-code" }, r.code)),
      h("div", { className: "yg-inc-story" }, r.why),
      h("div", null, (r.labels || []).map(function (l, i) { return h(Chip, { key: i, label: l }); })),
      h("div", { className: "yg-inc-story" },
        (r.sources || []).length ? "The data comes from " : "Sensitive data ",
        (r.sources || []).map(function (s, i) { return h("b", { key: i, className: "yg-mono" }, (i ? ", " : "") + s.name + "() on line " + s.line); }),
        " and leaves through ", h("b", { className: "yg-mono" }, r.sink.name), " (" + r.sink.human + ")."),
      h("div", { className: "yg-sub" }, "How to send it legally"),
      (r.quarantine || []).map(function (q, i) {
        return h("div", { className: "yg-row", key: i }, h("span", { className: "yg-k" }, q.label),
          h("span", null, q.options.length ? q.options.map(function (o) { return o.human + " (" + o.fn + ")"; }).join(" · ")
            : "no allowed protection: this data must not leave the program"));
      }),
      a ? h("div", null, h("div", { className: "yg-sub" }, "Automatic fix"),
        h("div", { className: "yg-diff old" }, "− " + a.before.trim()),
        h("div", { className: "yg-diff new" }, "+ " + a.after.trim()),
        h("div", { className: "yg-actions" },
          a.verified ? h("span", { className: "yg-ok" }, "✓ verified: the fixed code passes the check") :
            h("span", { className: "yg-warn" }, "⚠ needs manual review"),
          h("button", { className: "yg-btn good", disabled: !a.verified, onClick: p.onFix }, "Apply fix to the code above"))) :
        h("div", { className: "yg-dim yg-small" }, "No safe automatic fix for this leak. Use one of the protections above."),
      h(Gaps, { gaps: r.known_gaps }));
  }

  function Gaps(p) {
    if (!p.gaps || !p.gaps.length) return null;
    return h("details", { className: "yg-gaps" }, h("summary", null, "Honest limits of this check"),
      h("ul", null, p.gaps.map(function (g, i) { return h("li", { key: i }, g); })));
  }
  const SEV = { critical: ["Critical", "bad"], high: ["High", "bad"], medium: ["Medium", "warn"], low: ["Low", "ok"], info: ["Safe", "ok"] };
  const REACH = { all_networks: "Open to every network", local_network: "Open to this local network", this_computer: "Only this computer" };

  function ExposurePanel() {
    const [data, setData] = useState(null);
    const [busy, setBusy] = useState(false);
    const [showSafe, setShowSafe] = useState(false);
    function load(force) {
      setBusy(true);
      SDK.fetchJSON(API + "/exposure" + (force ? "?refresh=1" : ""))
        .then(setData).catch(function () { setData({ status: "error", message: "Guard backend is not reachable." }); })
        .finally(function () { setBusy(false); });
    }
    useEffect(function () { load(false); }, []);
    if (!data) return h(Card, { title: "network exposure", className: "wide" }, h(Empty, { text: "Scanning ports… this takes about 10 seconds." }));
    if (data.status === "error") return h(Card, { title: "network exposure", className: "wide" }, h("div", { className: "yg-err" }, "● " + data.message));
    const items = data.listeners || [];
    const risky = items.filter(function (l) { return l.severity !== "info"; });
    const safe = items.filter(function (l) { return l.severity === "info"; });
    const c = data.counts || {};
    const bad = (c.critical || 0) + (c.high || 0);
    return h(React.Fragment, null,
      h(Card, { title: "network exposure", className: "wide" },
        h("div", { className: "yg-shield " + (bad ? "bad" : "ok") },
          h("span", { className: "yg-big" }, (bad ? "⛔ " : "✓ ") + "Exposure score " + data.score + "/100"),
          h("span", { className: "yg-dim" }, "  " + (c.critical || 0) + " critical · " + (c.high || 0) + " high · " +
            (c.medium || 0) + " medium · " + (c.low || 0) + " low")),
        h("div", { className: "yg-dim yg-small" }, "Programs on this computer that accept network connections, and who can reach them. Nothing is changed by this scan."),
        h("div", { className: "yg-actions" },
          h("button", { className: "yg-btn", disabled: busy, onClick: function () { load(true); } }, busy ? "Scanning…" : "Check again"),
          h("span", { className: "yg-dim yg-small" }, "Last check " + ago(data.scanned_at))),
        risky.length ? risky.map(function (l, i) { return h(PortRow, { key: i, l: l }); })
          : h(Empty, { text: "Nothing risky is open to the network." }),
        h("details", { className: "yg-gaps" }, h("summary", null, "Honest limits of this scan"),
          h("ul", null, (data.limits || []).map(function (g, i) { return h("li", { key: i }, g); })))),
      h(Card, { title: "safe listeners", className: "wide" },
        h("button", { className: "yg-btn ghost", onClick: function () { setShowSafe(!showSafe); } },
          (showSafe ? "Hide " : "Show ") + safe.length + " safe listeners"),
        showSafe ? safe.map(function (l, i) { return h(PortRow, { key: i, l: l, compact: true }); }) : null));
  }

  function addrText(l) {
    const a = l.addresses && l.addresses.length ? l.addresses : [l.address];
    return a.map(function (x) { return x === "::" ? "[::]" : x; }).join(" + ");
  }
  const FW_TEXT = { allowed: "firewall lets it in", blocked: "firewall blocks it", off: "firewall is OFF",
    "not verified": "firewall: not verified", "not needed": "" };
  const FW_SCOPE = { everyone: "from anyone", "local network": "from your local network only",
    "some addresses": "from some addresses", "default": "by default", "group policy": "(managed by your organisation)" };
  function fwText(l) {
    let t = FW_TEXT[l.firewall] != null ? FW_TEXT[l.firewall] : "firewall: " + l.firewall;
    if (l.firewall_scope && FW_SCOPE[l.firewall_scope]) t += " " + FW_SCOPE[l.firewall_scope];
    if (l.firewall_rule) t += " (rule \u201c" + l.firewall_rule + "\u201d)";
    return t;
  }

  function PortRow(p) {
    const l = p.l, s = SEV[l.severity] || ["?", "warn"];
    return h("div", { className: "yg-inc " + (l.severity === "critical" || l.severity === "high" ? "pending" : "done") },
      h("div", { className: "yg-inc-top" },
        h(Pill, { kind: s[1] }, s[0]),
        h("b", null, l.service),
        h("span", { className: "yg-dim yg-right yg-mono" }, l.proto + " " + addrText(l) + " port " + l.port)),
      h("div", { className: "yg-inc-story" },
        h("b", { className: "yg-mono" }, l.process), " (pid " + l.pid + ") · " + (REACH[l.reach] || l.reach) +
        (l.reach === "this_computer" ? "" : " · " + fwText(l)),
        (l.tags || []).indexOf("public-tunnel") >= 0 ? h("span", { className: "yg-err" }, " · public internet tunnel") : null),
      p.compact ? null : h("div", { className: "yg-dim" }, l.why),
      p.compact || l.fix === "Nothing to do." ? null : h("div", { className: "yg-ok yg-small" }, "What to do: " + l.fix));
  }

  const KINDS = [["Credentials", "Password, API key or token"], ["Financial", "Card or bank account"],
    ["PII", "Personal data (name, phone, email)"], ["Health", "Medical data"], ["Location", "Location data"]];

  function VaultPanel(p) {
    const [secret, setSecret] = useState("");
    const [label, setLabel] = useState("Credentials");
    const [msg, setMsg] = useState(null);
    const [busy, setBusy] = useState(false);
    function save() {
      setBusy(true); setMsg(null);
      post("/vault", { secret: secret, label: label })
        .then(function (r) {
          if (r.status === "ok") { setSecret(""); setMsg({ ok: true, text: "Saved. Agents now get the token " + r.token.slice(0, 26) + "… instead of the real value, and any attempt to send the real value is blocked." }); p.onChanged(); }
          else setMsg({ ok: false, text: r.message || "Could not save." });
        })
        .catch(function () { setMsg({ ok: false, text: "Could not reach the Guard backend." }); })
        .finally(function () { setBusy(false); });
    }
    const items = (p.vault && p.vault.items) || [];
    return h(Card, { title: "vault · your secrets, encrypted" },
      h("div", { className: "yg-dim yg-small" }, "Add a secret you want to protect. It is encrypted with your Windows account " +
        "and never shown again here. Guard blocks any agent that tries to send it."),
      h("input", { className: "yg-input", type: "password", autoComplete: "off", placeholder: "Paste the secret value",
        value: secret, onChange: function (e) { setSecret(e.target.value); } }),
      // Buttons instead of a native <select>: its dropdown is drawn by the OS (white list,
      // blue text) and ignores the dark theme.
      h("div", { className: "yg-kinds", role: "radiogroup", "aria-label": "Kind of secret" },
        KINDS.map(function (k) {
          return h("button", { key: k[0], type: "button", role: "radio", "aria-checked": label === k[0],
            className: "yg-kind" + (label === k[0] ? " on" : ""), onClick: function () { setLabel(k[0]); } }, k[1]);
        })),
      h("div", { className: "yg-actions" },
        h("button", { className: "yg-btn", disabled: busy || !secret, onClick: save }, busy ? "Encrypting…" : "Protect this secret")),
      msg ? h("div", { className: msg.ok ? "yg-ok yg-small" : "yg-err yg-small" }, msg.text) : null,
      h("div", { className: "yg-sub" }, items.length + " protected secret" + (items.length === 1 ? "" : "s")),
      items.slice(0, 8).map(function (v, i) {
        return h("div", { className: "yg-row", key: i },
          h(Chip, { label: { id: v.label, label: v.title || v.label } }),
          h("span", { className: "yg-dim yg-small" }, v.source === "runtime-quarantine" ? "quarantined from an agent" : "added by you"),
          h("span", { className: "yg-dim yg-small" }, ago(v.created)));
      }));
  }

  function GuardPage() {
    const [tab, setTab] = useState("live");
    const [incidents, setIncidents] = useState(null);
    const [vault, setVault] = useState(null);
    const alive = useRef(true);
    const refresh = useCallback(function () {
      SDK.fetchJSON(API + "/incidents").then(function (d) { if (alive.current) setIncidents(d); })
        .catch(function () { if (alive.current) setIncidents({ status: "error", message: "Guard backend is not reachable." }); });
      SDK.fetchJSON(API + "/vault").then(function (d) { if (alive.current) setVault(d); }).catch(function () {});
    }, []);
    useEffect(function () {
      alive.current = true; refresh();
      const t = setInterval(function () { if (!document.hidden) refresh(); }, POLL_MS);
      return function () { alive.current = false; clearInterval(t); };
    }, [refresh]);
    const pending = incidents && incidents.pending ? incidents.pending : 0;
    function TabBtn(id, text) {
      return h("button", { className: "yg-tab" + (tab === id ? " on" : ""), onClick: function () { setTab(id); } }, text);
    }
    return h("div", { className: "yg-root" },
      h("div", { className: "yg-top" },
        h("span", { className: "yg-brand" }, h("span", { className: "yg-dot " + (pending ? "bad" : "ok") }), "YADRO GUARD"),
        h("div", { className: "yg-tabs" },
          TabBtn("live", "Live protection" + (pending ? " (" + pending + ")" : "")),
          TabBtn("exposure", "Exposure"),
          TabBtn("check", "Check code"),
          TabBtn("vault", "Vault"))),
      h("div", { className: "yg-grid" },
        tab === "live" ? h(LivePanel, { data: incidents, onChanged: refresh }) : null,
        tab === "exposure" ? h(ExposurePanel, null) : null,
        tab === "check" ? h(CheckPanel, null) : null,
        tab === "vault" ? h(VaultPanel, { vault: vault, onChanged: refresh }) : null),
      h("div", { className: "yg-foot" }, "🔒 Everything runs on this computer. Secret values are never shown or sent."));
  }

  onReady(GuardPage);
})(window.__HERMES_PLUGIN_SDK__, function (GuardPage) {
  if (window.__HERMES_PLUGINS__ && typeof window.__HERMES_PLUGINS__.register === "function") {
    window.__HERMES_PLUGINS__.register("yadro-guard", GuardPage);
  }
});
