# Benchmarks

`python benchmarks/run.py` измеряет median и p95 в миллисекундах для compile-to-verified-IR, Ethical Analyzer и MCP graph scan. CI использует GitHub-hosted Ubuntu, Python 3.11 и pinned llvmlite 0.43.0.

Цифры являются инженерным baseline, а не hardware-independent обещанием. JSON schema: `yadro-benchmark-1.0`; измеренный baseline фиксируется после CI.
