# -*- coding: utf-8 -*-
"""Detectors for secrets and sensitive data inside agent tool-call arguments.

Pure Python, no dependencies, no network. Every finding carries:
    kind     machine id          ("github_token", "card_number", ...)
    label    data category       (Credentials / Financial / PII / Health / Location)
    title    human text          ("GitHub access token")
    start/end offsets inside the scanned string
    preview  MASKED value only   ("ghp_…4f2a") — raw values never leave this module
             except via `value`, which callers must not log or display.
Design notes:
- Precision over recall for structured kinds (checksums: Luhn, IBAN mod-97).
- High-entropy strings are only reported when they look like keys AND sit next to
  a secret-ish word, to keep false positives manageable.
- Exact matches against secrets stored in the vault have the highest confidence.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

MAX_SCAN_CHARS = 512 * 1024


@dataclass
class Finding:
    kind: str
    label: str
    title: str
    start: int
    end: int
    value: str = field(repr=False)
    confidence: str = "high"
    path: str = ""          # where in the args: e.g. "command" or "headers.Authorization"

    @property
    def preview(self) -> str:
        return mask(self.value)

    def public(self) -> dict:
        """Safe-to-display dict: no raw value."""
        return {"kind": self.kind, "label": self.label, "title": self.title,
                "preview": self.preview, "confidence": self.confidence, "path": self.path}


def mask(value: str) -> str:
    v = value.strip()
    if len(v) <= 8:
        return "•" * len(v)
    return f"{v[:4]}…{v[-4:]}"


# ---------------------------------------------------------------- patterns
_RULES = [
    # kind, label, title, regex, confidence
    ("private_key", "Credentials", "Private key (PEM)",
     r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY(?: BLOCK)?-----[\s\S]{20,}?-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----", "high"),
    ("github_token", "Credentials", "GitHub access token",
     r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{60,255})\b", "high"),
    ("gitlab_token", "Credentials", "GitLab access token", r"\bglpat-[A-Za-z0-9_\-]{20,}\b", "high"),
    # All AWS unique-ID prefixes (redteam review by DeepSeek V4: only AKIA/ASIA were covered).
    ("aws_access_key", "Credentials", "AWS access key ID",
     r"\b(?:AKIA|ASIA|ABIA|ACCA|AGPA|AIDA|AIPA|ANPA|ANVA|APKA|AROA|ASCA)[0-9A-Z]{16}\b", "high"),
    ("aws_secret_key", "Credentials", "AWS secret access key",
     r"(?i)aws[_\-]?secret[_\-]?(?:access[_\-]?)?key[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9/+=]{40})(?![A-Za-z0-9/+=])", "high"),
    ("google_api_key", "Credentials", "Google API key", r"\bAIza[0-9A-Za-z_\-]{35}\b", "high"),
    ("openai_key", "Credentials", "OpenAI API key", r"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{20,}T3BlbkFJ[A-Za-z0-9_\-]{20,}\b|\bsk-proj-[A-Za-z0-9_\-]{40,}\b", "high"),
    ("anthropic_key", "Credentials", "Anthropic API key", r"\bsk-ant-[A-Za-z0-9_\-]{30,}\b", "high"),
    ("slack_token", "Credentials", "Slack token", r"\bxox[abposr]-[A-Za-z0-9\-]{10,}\b", "high"),
    ("stripe_key", "Credentials", "Stripe secret key", r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}\b", "high"),
    ("telegram_bot_token", "Credentials", "Telegram bot token", r"\b\d{8,10}:AA[A-Za-z0-9_\-]{33}\b", "high"),
    ("jwt", "Credentials", "JSON Web Token", r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b", "medium"),
    ("password_in_url", "Credentials", "Password inside a URL", r"\b[a-z][a-z0-9+.\-]*://[^\s:/@]+:([^\s@/]{3,})@", "high"),
    ("email", "PII", "Email address", r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", "medium"),
]
_COMPILED = [(k, l, t, re.compile(r), c) for k, l, t, r, c in _RULES]

_CARD = re.compile(r"(?<![\d-])\d(?:[ -]?\d){12,18}(?![\d-])")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b")
_ASSIGN = re.compile(
    r"(?i)(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|access[_-]?key|auth|bearer|private[_-]?key|client[_-]?secret)"
    r"[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_\-+/=.]{16,})")
_BEARER = re.compile(r"(?i)\bbearer\s+([A-Za-z0-9_\-+/=.]{20,})")


def luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def iban_ok(raw: str) -> bool:
    s = raw.replace(" ", "")
    if not 15 <= len(s) <= 34:
        return False
    moved = s[4:] + s[:4]
    try:
        return int("".join(str(int(ch, 36)) for ch in moved)) % 97 == 1
    except ValueError:
        return False


def entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    return -sum(n / len(s) * math.log2(n / len(s)) for n in counts.values())


def _overlaps(a: Finding, taken: List[Finding]) -> bool:
    return any(a.path == b.path and a.start < b.end and b.start < a.end for b in taken)


def scan_text(text: str, path: str = "", known_secrets: Iterable[tuple] = ()) -> List[Finding]:
    """All findings in one string. known_secrets: iterable of (value, label, title)."""
    if not isinstance(text, str) or not text:
        return []
    text = text[:MAX_SCAN_CHARS]
    found: List[Finding] = []

    def add(f: Finding):
        if not _overlaps(f, found):
            found.append(f)

    # 1) exact vault matches first: highest confidence, they define what is "yours"
    for value, label, title in known_secrets:
        if value and len(value) >= 4:
            i = text.find(value)
            while i >= 0:
                add(Finding("vault_secret", label, title or "A secret from your vault", i, i + len(value),
                            value, "certain", path))
                i = text.find(value, i + len(value))
    # 2) structured detectors
    for kind, label, title, rx, conf in _COMPILED:
        for m in rx.finditer(text):
            g = 1 if kind in ("password_in_url", "aws_secret_key") else 0
            add(Finding(kind, label, title, m.start(g), m.end(g), m.group(g), conf, path))
    for m in _CARD.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and luhn_ok(digits) and len(set(digits)) > 1:
            add(Finding("card_number", "Financial", "Payment card number", m.start(), m.end(), m.group(0), "high", path))
    for m in _IBAN.finditer(text):
        if iban_ok(m.group(0)):
            add(Finding("iban", "Financial", "Bank account (IBAN)", m.start(), m.end(), m.group(0), "high", path))
    # 2b) crypto wallets: seed phrases, private keys, keystores (what stealers hunt for)
    from . import crypto_detect
    for kind, label, title, s, e, conf in crypto_detect.scan(text):
        add(Finding(kind, label, title, s, e, text[s:e], conf, path))
    # 3) secret-looking assignments / bearer headers with high entropy
    for rx, title in ((_ASSIGN, "Secret value assigned to a password/token field"),
                      (_BEARER, "Bearer token in an Authorization header")):
        for m in rx.finditer(text):
            v = m.group(1)
            if entropy(v) >= 3.3 and not v.lower().startswith(("http", "your", "example", "xxxx", "changeme")):
                add(Finding("generic_secret", "Credentials", title, m.start(1), m.end(1), v, "medium", path))
    found.sort(key=lambda f: f.start)
    return found


def walk_args(args, prefix: str = ""):
    """Yield (path, string) for every string inside nested tool arguments."""
    if isinstance(args, str):
        yield prefix or "value", args
    elif isinstance(args, dict):
        for k, v in args.items():
            yield from walk_args(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(args, (list, tuple)):
        for i, v in enumerate(args):
            yield from walk_args(v, f"{prefix}[{i}]")


def scan_args(args, known_secrets: Iterable[tuple] = ()) -> List[Finding]:
    known = list(known_secrets)
    out: List[Finding] = []
    for path, text in walk_args(args):
        out.extend(scan_text(text, path, known))
    return out


def redact_args(args, findings: List[Finding], replacement_for):
    """Return a deep copy of args with every finding replaced by replacement_for(finding)."""
    by_path = {}
    for f in findings:
        by_path.setdefault(f.path, []).append(f)

    def rewrite(node, prefix=""):
        if isinstance(node, str):
            key = prefix or "value"
            for f in sorted(by_path.get(key, []), key=lambda x: x.start, reverse=True):
                node = node[:f.start] + replacement_for(f) + node[f.end:]
            return node
        if isinstance(node, dict):
            return {k: rewrite(v, f"{prefix}.{k}" if prefix else str(k)) for k, v in node.items()}
        if isinstance(node, list):
            return [rewrite(v, f"{prefix}[{i}]") for i, v in enumerate(node)]
        if isinstance(node, tuple):
            return tuple(rewrite(v, f"{prefix}[{i}]") for i, v in enumerate(node))
        return node
    return rewrite(args)
