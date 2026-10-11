# Helper models (the conductor's team)

Cline is the conductor. Cheaper or free models are helpers that the conductor calls
from the terminal for independent opinions:

| Role | What it does |
|------|--------------|
| `reviewer` | independent code review, real bugs only |
| `redteam` | tries to bypass Yadro Guard, gives concrete inputs |
| `architect` | checks design and threat model, what is missing |
| `tester` | proposes test inputs that expose false negatives/positives |

## One-time setup (choose at least one, all have free tiers)

Run in PowerShell, then restart Cline so it sees the variable.
Never paste keys into chat or files.

```powershell
# OpenRouter: https://openrouter.ai/keys  (free models end with ":free")
[Environment]::SetEnvironmentVariable("OPENROUTER_API_KEY", "YOUR_KEY", "User")

# Google AI Studio: https://aistudio.google.com/apikey  (create a NEW key)
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "YOUR_KEY", "User")

# Groq: https://console.groq.com/keys
[Environment]::SetEnvironmentVariable("GROQ_API_KEY", "YOUR_KEY", "User")

# Local llama-server (needs its --api-key if one is set)
[Environment]::SetEnvironmentVariable("LOCAL_LLM_URL", "http://127.0.0.1:18434/v1", "User")
[Environment]::SetEnvironmentVariable("LOCAL_LLM_KEY", "YOUR_LOCAL_KEY", "User")
```

Model names can be overridden with `OPENROUTER_MODEL`, `GEMINI_MODEL`, `GROQ_MODEL`,
`LOCAL_LLM_MODEL`. Free model lists change; check the provider's site if a call fails.

## Usage (by the conductor)

```
python tools/helpers/ask.py --list
python tools/helpers/ask.py --role redteam --files src/runtime/detectors.py --question "Find bypasses"
```

Answers land in `tools/helpers/out/` (git-ignored).

## Safety

- Every file is scanned with Yadro Guard's own detectors before sending; any secret aborts the call.
- `.env`, vault, incident journals, config and key files can never be sent.
- Only files inside the repository can be sent.
- Free tiers may use prompts for training: send only code that is already public.
