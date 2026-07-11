# DREAM Qwen Experience Memory Stability

- Run: `20260711T023507Z`
- Provider/model: `qwen-cloud` / `qwen3.7-plus`
- Repetitions: 3
- All runs passed: yes

| Metric | Result |
|---|---:|
| Passed runs | 3/3 |
| Consistently passed cases | 24/24 |
| Step action agreement | 100.0% |
| Qwen receipt coverage | 100.0% |
| Qwen decisions | 111 |
| Qwen tokens | 86,147 |

## Limitations

- Repeated synthetic scenarios measure consistency, not production impact.
- Temperature zero reduces but does not eliminate provider-side variation.
