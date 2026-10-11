/* Yadro Guard — вкладка дашборда Hermes.
 * Plain IIFE без сборки (как плагин kanban). React и fetchJSON берутся у хоста
 * через window.__HERMES_PLUGIN_SDK__. Весь текст выводится через React
 * (автоэкранирование); dangerouslySetInnerHTML не используется. HTML-отчёт
 * открывается в sandbox-iframe без права исполнять скрипты. */
(function () {
  "use strict";
  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK || !SDK.React) return;
  const React = SDK.React;
  const h = React.createElement;
  const { useState, useEffect, useCallback } = React;
  const API = "/api/plugins/yadro-guard";

  function post(path, body) {
    return SDK.fetchJSON(API + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  function Card(p) {
    return h("div", { className: "yg-card " + (p.className || "") },
      h("b", { className: "yg-hd" }, p.title), p.children);
  }

  function Chip(p) {
    const l = p.label || {};
    return h("span", { className: "yg-chip", style: { background: l.color || "#555" } },
      (l.icon || "") + " " + (l.label || l.id || ""));
  }

  function Verdict(p) {
    const r = p.result;
    if (!r) return h("div", { className: "yg-dim" }, "● no data — укажите файл и нажмите scan");
    if (r.status === "error") return h("div", { className: "yg-err" }, "● " + (r.message || "ошибка"));
    if (r.status === "ok") return h("div", { className: "yg-verdict ok" },
      h("span", { className: "yg-big" }, "✓ ЧИСТО"),
      h("span", { className: "yg-dim" }, "  утечек не найдено · " + (r.lines || 0) + " строк"));
    return h("div", { className: "yg-verdict bad" },
      h("span", { className: "yg-big" }, "⛔ УТЕЧКА"),
      h("span", { className: "yg-code" }, r.code),
      h("div", { className: "yg-why" }, r.why));
  }

  function Flow(p) {
    const r = p.result;
    if (!r || r.status !== "leak") return null;
    const nodes = (r.sources || []).map(function (s, i) {
      return h(React.Fragment, { key: "s" + i },
        h("div", { className: "yg-node src" },
          h("div", { className: "yg-lbl" }, "строка " + s.line),
          h("div", { className: "yg-mono" }, s.name + "()"),
          h(Chip, { label: s.label })),
        h("div", { className: "yg-arrow" }, "→"));
    });
    nodes.push(h("div", { key: "sink", className: "yg-node sink" },
      h("div", { className: "yg-lbl" }, "строка " + r.line + " · утечка"),
      h("div", { className: "yg-mono" }, r.sink.name),
      h("div", { className: "yg-lbl" }, r.sink.human)));
    return h(Card, { title: "путь данных" }, h("div", { className: "yg-flow" }, nodes));
  }

  function Quarantine(p) {
    const r = p.result;
    if (!r || r.status !== "leak") return null;
    return h(Card, { title: "карантин · как отправить легально" },
      (r.quarantine || []).map(function (q, i) {
        return h("div", { className: "yg-row", key: i },
          h("span", { className: "yg-k" }, q.label),
          h("span", null, (q.options || []).length
            ? q.options.map(function (o) { return o.human + " " + o.fn + "()"; }).join(" · ")
            : "нет разрешённой обёртки — наружу нельзя"));
      }));
  }

  function Autofix(p) {
    const r = p.result;
    if (!r || r.status !== "leak" || !r.autofix) return null;
    const a = r.autofix;
    return h(Card, { title: "автоисправление · было / стало" },
      h("div", { className: "yg-diff old" }, "− " + a["было"].trim()),
      h("div", { className: "yg-diff new" }, "+ " + a["стало"].trim()),
      h("div", { className: "yg-actions" },
        a["проверено"] ? h("span", { className: "yg-ok" }, "✓ проверено движком")
          : h("span", { className: "yg-warn" }, "⚠ нужна ручная проверка"),
        h("button", { className: "yg-btn", disabled: !a["проверено"], onClick: p.onFix }, "применить → .fixed"),
        p.fixed ? h("span", { className: "yg-dim" }, p.fixed) : null));
  }

  function History(p) {
    const items = p.items || [];
    return h(Card, { title: "история сканов" },
      items.length ? items.slice(0, 8).map(function (it, i) {
        return h("div", { className: "yg-row yg-click", key: i, onClick: function () { p.onPick(it.path); } },
          h("span", { className: it.status === "ok" ? "yg-ok" : "yg-err" }, it.status === "ok" ? "● ok" : "● leak"),
          h("span", { className: "yg-path" }, String(it.path).split(/[\\/]/).pop()),
          h("span", { className: "yg-dim" }, (it.labels || []).join(", ")));
      }) : h("div", { className: "yg-dim" }, "● no data"));
  }

  function Vault(p) {
    const items = p.items;
    return h(Card, { title: "сейф · токены вместо секретов" },
      !items ? h("div", { className: "yg-dim" }, "loading…")
        : items.length ? items.slice(0, 6).map(function (v, i) {
          return h("div", { className: "yg-row", key: i },
            h("span", { className: "yg-mono yg-tok" }, String(v.token).slice(0, 34) + "…"),
            h("span", { className: "yg-dim" }, v.label));
        }) : h("div", { className: "yg-dim" }, "● пусто · python -m src.vault put --label …"),
      h("div", { className: "yg-dim yg-note" }, "оригиналы зашифрованы DPAPI и через веб не выдаются"));
  }
  function GuardPage() {
    const [path, setPath] = useState("");
    const [busy, setBusy] = useState(false);
    const [result, setResult] = useState(null);
    const [fixed, setFixed] = useState("");
    const [report, setReport] = useState("");
    const [history, setHistory] = useState([]);
    const [vault, setVault] = useState(null);

    const refresh = useCallback(function () {
      SDK.fetchJSON(API + "/history").then(function (d) { setHistory(d.items || []); }).catch(function () {});
      SDK.fetchJSON(API + "/vault").then(function (d) { setVault(d.items || []); }).catch(function () { setVault([]); });
    }, []);
    useEffect(function () { refresh(); }, [refresh]);

    function scan(p) {
      const target = String(p || path).trim();
      if (!target) return;
      setPath(target); setBusy(true); setFixed(""); setReport("");
      post("/scan", { path: target })
        .then(setResult)
        .catch(function () { setResult({ status: "error", message: "бэкенд плагина недоступен" }); })
        .finally(function () { setBusy(false); refresh(); });
    }
    function fix() {
      post("/fix", { path: path.trim() })
        .then(function (d) { setFixed(d.written ? "записано: " + d.written : (d.message || "не исправлено")); })
        .catch(function () { setFixed("ошибка"); });
    }
    function openReport() {
      post("/report", { path: path.trim() })
        .then(function (d) { setReport(d.html || ""); })
        .catch(function () {});
    }

    return h("div", { className: "yg-root" },
      h("div", { className: "yg-top" },
        h("span", { className: "yg-brand" },
          h("span", { className: "yg-dot " + (result && result.status === "leak" ? "bad" : "ok") }), "YADRO GUARD"),
        h("input", {
          className: "yg-input", value: path, placeholder: "C:\\путь\\к\\программе.яд",
          onChange: function (e) { setPath(e.target.value); },
          onKeyDown: function (e) { if (e.key === "Enter") scan(); },
        }),
        h("button", { className: "yg-btn", disabled: busy, onClick: function () { scan(); } }, busy ? "scan…" : "scan"),
        h("button", { className: "yg-btn ghost", disabled: !result || result.status === "error", onClick: openReport }, "отчёт")),
      h("div", { className: "yg-grid" },
        h(Card, { title: "вердикт", className: "wide" },
          h(Verdict, { result: result }),
          result && result.labels ? h("div", { className: "yg-chips" },
            result.labels.map(function (l, i) { return h(Chip, { key: i, label: l }); })) : null),
        h(Flow, { result: result }),
        h(Quarantine, { result: result }),
        h(Autofix, { result: result, onFix: fix, fixed: fixed }),
        h(History, { items: history, onPick: scan }),
        h(Vault, { items: vault })),
      report ? h("div", { className: "yg-modal", onClick: function () { setReport(""); } },
        h("iframe", { className: "yg-frame", sandbox: "", srcDoc: report, title: "отчёт" })) : null);
  }

  if (window.__HERMES_PLUGINS__ && typeof window.__HERMES_PLUGINS__.register === "function") {
    window.__HERMES_PLUGINS__.register("yadro-guard", GuardPage);
  }
})();
