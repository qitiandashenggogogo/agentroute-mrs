# NOTICE

本仓库 release 分支里的 `*.mrs` 由 [ryuu-restart/agent-route](https://github.com/ryuu-restart/agent-route) 发布的 mihomo YAML 规则集（private / proxy / direct / cn-ip）原样转换格式而来，未增删条目。

- 转换工具：官方 [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo) `convert-ruleset`，版本与 SHA-256 固定在 `.github/workflows/build.yml`
- 每次转换的上游发布时间、各文件 sha256 与条目数见 release 分支的 `manifest.json`
- 规则数据沿用上游许可证 GPL-3.0（见 `LICENSE`）；上游数据来源见其 `docs/MAINTAINING.md`
- 不包含 reject（广告名单）
