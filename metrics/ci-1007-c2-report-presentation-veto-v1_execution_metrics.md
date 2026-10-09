# Execution Metrics: ci-1007-c2-report-presentation-veto-v1

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| primary initial | codebuddy-cli | deepseek-v4.1-flash requestedmax | partial; incomplete final replaced by fallback | first wrapper1261.910s | not attested | not accepted |
| runner fallback | openai-codex viaPi | gpt-6-luna requestedmax | actual; planning question only |17.418s inside first envelope|not needed|not accepted; reason contradicts primarysession |
| same primary continuation | codebuddy-cli | runtimeinit deepseek-v4.1-flash / adaptermax | actualresumed/exit0 |852.025s(runtime),852.146s(wrapper)|42|owner bounded code accept; not report/release |

Owner151relatedPASS4.39s, Ruff5/strict3; worker adjacent582PASS/2FAIL not promoted. Original7200s total, actual wrappers2114.056s; second timeout5900s. No latency polling, arbitrary force stop, new session or independent C3 review. Baseline ac492a2; exact source hashes and resume pins in owner receipt. No default model treated as verified; exact existing alternative selected before first dispatch.
