# Task 8.5 HTML-PPT 当前候选清单

状态：A/B/C 三份单文件候选已由锁定输入重新生成。结构/离线/逐字稿/字号/覆盖、Chromium+WebKit `file://` 以及 Chromium 1440×900 页几何合同已跑通。最大化窗口逐页视觉终验仍属 Task 8.6，本步不代替。

生成命令：

```text
uv run python tools/render_html_ppt.py --report A --output output/html-ppt/report-a.html
uv run python tools/render_html_ppt.py --report B --output output/html-ppt/report-b.html
uv run python tools/render_html_ppt.py --report C --output output/html-ppt/report-c.html
```

| 报告 | 路径 | 页数 | 输入 SHA-256 | 输出 SHA-256 | 字节 |
|---|---|---|---|---|---|
| A | `output/html-ppt/report-a.html` | 20 | `988c1607e08c7f9747a6feb493dcdaf66b6ccd7c26cafefe96e956622196fa1a` | `adcf8487aa85996d0d4886d7801a16a544f2b703cac5a331d4a7a7af085eb2e4` | 450545 |
| B | `output/html-ppt/report-b.html` | 24 | `eeae14ce581aeacc6c098cde5f45571e4d0f88d2cc5877cba5429654448381d1` | `087d04b0aa1ddb0da26c5370fcf26e8bb328efc4705136194bbe0ecdb5740b1d` | 460748 |
| C | `output/html-ppt/report-c.html` | 18 | `a59d7f88b3d8a2e163422c01f0d0981aa64bf2610cc6bb41852c58e9561ed2e6` | `fd2d47565bfdb1b12f6405c62ed53f9762eac67c92175302a5a6eba8d3064113` | 366570 |

清单 sidecar：`output/html-ppt/report-{a,b,c}.manifest.json`。

逐字稿汉字范围（构建时校验）：A 151–169；B 150–173；C 150–174。已去掉套话补足句。A 类矩阵使用两页覆盖全部 19 个配对产品；B 类疗效图同时标出治疗组和对照组数值，矩阵使用气泡图，安全性热图按事件维度归一化着色。C 类样本量页显示 740/445/941/331 例，并将比较符统一为中文数学符号；图表标签保留完整产品身份和逐项 `aria-label`，不再按固定字符数静默截断。
