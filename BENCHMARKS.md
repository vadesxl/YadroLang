# Benchmarks

Измерено на GitHub-hosted Ubuntu, Python 3.11.15, pinned llvmlite 0.43.0:

| Путь | Median | p95 | Rounds |
|---|---:|---:|---:|
| Компиляция до verified LLVM IR | 1.3997 ms | 2.3209 ms | 40 |
| Ethical Analyzer | 0.1574 ms | 0.2369 ms | 80 |
| MCP graph scan | 0.3683 ms | 0.4935 ms | 120 |

Воспроизведение: `python -m benchmarks.run`. Это инженерный baseline, не hardware-independent обещание. Данные: `benchmarks/baseline.json`, schema `yadro-benchmark-1.0`.
