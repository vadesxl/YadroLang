# -*- coding: utf-8 -*-
"""Crypto-wallet secret detectors: what a stealer looks for, and what an agent must never send.

    seed phrases (BIP39)   12-24 words from the official list, CHECKSUM VERIFIED     -> certain
                           12/24-word run without a valid checksum (Electrum, typos) -> medium
    WIF private keys       base58check verified (Bitcoin and forks)                   -> certain
    extended private keys  xprv/yprv/zprv/tprv..., base58check verified               -> certain
    hex private keys       64 hex chars ONLY next to a key-like word (hashes look alike) -> high
    Solana keypair arrays  [n, n, ...] with exactly 64 bytes (id.json)                -> high
    Solana base58 secrets  base58 decoding to 64 bytes, next to a key-like word       -> medium
    wallet keystore JSON   ciphertext + cipherparams + kdf (Ethereum / MetaMask vault) -> high

The BIP39 word list ships with the engine and is verified by SHA-256 at import: a
tampered list raises, so the runtime hook fails CLOSED (block), never open.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import List, Tuple

_WORDLIST_SHA256 = "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"
_WORDLIST_FILE = Path(__file__).resolve().parent / "data" / "bip39_english.txt"


def _load_wordlist():
    # Normalise line endings first: git/zip on Windows may turn LF into CRLF, which must
    # not change the verdict (a false integrity failure would block every agent action).
    raw = _WORDLIST_FILE.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != _WORDLIST_SHA256:
        raise RuntimeError("BIP39 word list failed its integrity check")
    words = raw.decode("ascii").split()
    if len(words) != 2048:
        raise RuntimeError("BIP39 word list has the wrong size")
    return words, {w: i for i, w in enumerate(words)}


WORDS, INDEX = _load_wordlist()
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {c: i for i, c in enumerate(_B58)}
_KEY_WORD = re.compile(r"(?i)(private|priv|secret|seed|mnemonic|wallet|signer|pk|sk|key)\w*[\"']?\s*[:=]?\s*[\"']?$")

Hit = Tuple[str, str, str, int, int, str]   # kind, label, title, start, end, confidence


def bip39_valid(words: List[str]) -> bool:
    n = len(words)
    if n not in (12, 15, 18, 21, 24) or any(w not in INDEX for w in words):
        return False
    bits = "".join(format(INDEX[w], "011b") for w in words)
    cs_len = n // 3
    entropy_bits, checksum = bits[:-cs_len], bits[-cs_len:]
    entropy = int(entropy_bits, 2).to_bytes(len(entropy_bits) // 8, "big")
    digest = hashlib.sha256(entropy).digest()
    return format(int.from_bytes(digest, "big") >> (256 - cs_len), f"0{cs_len}b") == checksum


def b58decode(s: str) -> bytes:
    n = 0
    for c in s:
        if c not in _B58_INDEX:
            raise ValueError("not base58")
        n = n * 58 + _B58_INDEX[c]
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + body


def b58check_ok(s: str) -> bool:
    try:
        raw = b58decode(s)
    except ValueError:
        return False
    if len(raw) < 5:
        return False
    return hashlib.sha256(hashlib.sha256(raw[:-4]).digest()).digest()[:4] == raw[-4:]


_WORD = re.compile(r"[A-Za-z]+")
_GAP_OK = re.compile(r"^[\s,;.\-\d)(\]\[\"'|/:]*$")


def _seed_hits(text: str) -> List[Hit]:
    """Runs of BIP39 words separated only by spaces/punctuation/numbering ("1. abandon 2. ability")."""
    hits: List[Hit] = []
    run: List[Tuple[str, int, int]] = []

    def flush():
        if len(run) < 12:
            return
        words = [w for w, _, _ in run]
        for size in (24, 21, 18, 15, 12):
            for i in range(len(words) - size + 1):
                if bip39_valid(words[i:i + size]):
                    hits.append(("seed_phrase", "Credentials", "Crypto wallet seed phrase (BIP39)",
                                 run[i][1], run[i + size - 1][2], "certain"))
                    return
        if len(words) in (12, 24):
            hits.append(("seed_phrase_unverified", "Credentials", "Possible crypto seed phrase",
                         run[0][1], run[-1][2], "medium"))

    for m in _WORD.finditer(text):
        w, s, e = m.group(0).lower(), m.start(), m.end()
        if w in INDEX and run and s - run[-1][2] <= 12 and _GAP_OK.match(text[run[-1][2]:s]):
            run.append((w, s, e))
            continue
        flush()
        run = [(w, s, e)] if w in INDEX else []
    flush()
    return hits


def _near_key_word(text: str, start: int) -> bool:
    return bool(_KEY_WORD.search(text[max(0, start - 40):start]))


_B58C = "1-9A-HJ-NP-Za-km-z"
_WIF = re.compile(rf"(?<![{_B58C}])[5KLc9][{_B58C}]{{50,51}}(?![{_B58C}])")
_XPRV = re.compile(rf"\b[xyztuv]prv[{_B58C}]{{107,108}}\b")
_HEX64 = re.compile(r"(?<![0-9a-fA-Fx])(?:0x)?[0-9a-fA-F]{64}(?![0-9a-fA-F])")
_SOL_ARRAY = re.compile(r"\[\s*(?:\d{1,3}\s*,\s*){63}\d{1,3}\s*\]")
_SOL_B58 = re.compile(rf"(?<![{_B58C}])[{_B58C}]{{86,88}}(?![{_B58C}])")
_KEYSTORE = re.compile(r'"ciphertext"\s*:', re.I)


def scan(text: str) -> List[Hit]:
    if not text:
        return []
    hits = _seed_hits(text)
    for m in _XPRV.finditer(text):
        if b58check_ok(m.group(0)):
            hits.append(("xprv", "Credentials", "Extended private key (HD wallet master key)", m.start(), m.end(), "certain"))
    for m in _WIF.finditer(text):
        try:
            raw = b58decode(m.group(0))
        except ValueError:
            continue
        if b58check_ok(m.group(0)) and raw[0] in (0x80, 0xEF, 0xB0, 0x9E) and len(raw) in (37, 38):
            hits.append(("wif_private_key", "Credentials", "Bitcoin private key (WIF)", m.start(), m.end(), "certain"))
    for m in _HEX64.finditer(text):
        if _near_key_word(text, m.start()):
            hits.append(("hex_private_key", "Credentials", "Crypto private key (hex)", m.start(), m.end(), "high"))
    for m in _SOL_ARRAY.finditer(text):
        nums = [int(x) for x in re.findall(r"\d+", m.group(0))]
        if len(nums) == 64 and all(0 <= x <= 255 for x in nums):
            hits.append(("solana_keypair", "Credentials", "Solana private key (keypair file)", m.start(), m.end(), "high"))
    for m in _SOL_B58.finditer(text):
        try:
            if len(b58decode(m.group(0))) == 64 and _near_key_word(text, m.start()):
                hits.append(("solana_secret", "Credentials", "Solana private key (base58)", m.start(), m.end(), "medium"))
        except ValueError:
            pass
    k = _KEYSTORE.search(text)
    if k and re.search(r'"cipherparams"\s*:', text, re.I) and re.search(r'"kdf"\s*:|"scrypt"|"pbkdf2"', text, re.I):
        hits.append(("wallet_keystore", "Credentials", "Encrypted crypto wallet file (keystore / vault)",
                     k.start(), min(len(text), k.end() + 64), "high"))
    return hits
