#!/usr/bin/env python3
"""把 AgentRoute 发布的 mihomo YAML 规则集转成 mrs，供 iOS 等内存受限的客户端使用。

流程：读 index.json → 下载 private / proxy / direct / cn-ip → 核对 sha256 与条目数
→ 用官方 mihomo convert-ruleset 转换 → mihomo -t 加载检查 → 写入 dist/。
任何一步失败都非零退出，工作流不发布，线上保留上一版。
不处理 reject（广告名单），与 Mac 端接入范围一致。
"""
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

INDEX_URL = "https://raw.githubusercontent.com/ryuu-restart/agent-route/release/index.json"
DATASETS = ["private", "proxy", "direct", "cn-ip"]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "agentroute-mrs"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def count_entries(raw: bytes) -> int:
    return sum(1 for line in raw.decode("utf-8").splitlines() if line.lstrip().startswith("- "))


def main(mihomo: str, out: str) -> None:
    out_dir = Path(out)
    work = Path("work")
    shutil.rmtree(work, ignore_errors=True)
    (work / "rules").mkdir(parents=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    index = json.loads(fetch(INDEX_URL))
    by_id = {d["id"]: d for d in index["datasets"]}
    manifest = {
        "source": "https://github.com/ryuu-restart/agent-route",
        "source_generated_at_utc": index["generated_at_utc"],
        "datasets": {},
    }
    for name in DATASETS:
        ds = by_id[name]
        res = ds["resources"]["mihomo"]
        raw = fetch(res["url"])
        digest = hashlib.sha256(raw).hexdigest()
        if digest != res["sha256"]:
            sys.exit(f"{name}: sha256 与 index 不一致（上游可能正在切换发布），本次不发布")
        entries = count_entries(raw)
        if entries != res["entries"] or entries == 0:
            sys.exit(f"{name}: 条目数 {entries} 与 index {res['entries']} 不一致或为空")
        src = work / "rules" / f"{name}.yaml"
        dst = work / "rules" / f"{name}.mrs"
        src.write_bytes(raw)
        behavior = ds["mihomo_behavior"]
        subprocess.run([mihomo, "convert-ruleset", behavior, "yaml", str(src), str(dst)], check=True)
        if dst.stat().st_size == 0:
            sys.exit(f"{name}: 转换结果为空")
        manifest["datasets"][name] = {
            "behavior": behavior,
            "entries": entries,
            "yaml_sha256": digest,
            "mrs_sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
            "mrs_bytes": dst.stat().st_size,
        }

    # 用同一个 mihomo 实际加载 4 个 mrs，确认能被内核读取
    lines = ["mode: rule", "log-level: silent", "rule-providers:"]
    for name in DATASETS:
        b = manifest["datasets"][name]["behavior"]
        lines.append(f"  sr-{name}: {{type: file, behavior: {b}, format: mrs, path: ./rules/{name}.mrs}}")
    lines.append("rules:")
    lines += [f"  - RULE-SET,sr-{n},DIRECT" for n in DATASETS] + ["  - MATCH,DIRECT"]
    (work / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    test = subprocess.run([mihomo, "-t", "-d", str(work), "-f", str(work / "config.yaml")],
                          capture_output=True, text=True)
    if "test is successful" not in test.stdout + test.stderr:
        sys.exit("mihomo -t 加载 mrs 失败：" + (test.stdout + test.stderr).strip()[-300:])

    for name in DATASETS:
        shutil.copy2(work / "rules" / f"{name}.mrs", out_dir / f"{name}.mrs")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: (v["entries"], v["mrs_bytes"]) for k, v in manifest["datasets"].items()}, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("用法：build.py <mihomo 可执行文件> <输出目录>")
    main(sys.argv[1], sys.argv[2])
