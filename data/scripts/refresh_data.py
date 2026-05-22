#!/usr/bin/env python3
"""
数据预热 refresh_data —— 把慢的取数提前跑掉，灌满缓存。

为什么：weekly_pick 每次重新取数，全市场增强约 30 分钟。这种摩擦会扼杀
"每周跑 + 验证命中率"的习惯。预热不会让取数变快，但把那 30 分钟从
"你坐着等"挪到"无人值守时跑掉"——之后分析秒级读缓存。

用法（每天手动跑一次，建议盘后）：
  python scripts/refresh_data.py            # 全量（含全市场增强，约 30 分钟）
  python scripts/refresh_data.py --quick    # 只预热快数据（宏观/政策/大盘/行业/预告）
  python scripts/refresh_data.py --only screen   # 只跑某一项

预热覆盖阶段 1-3 的数据；阶段 4-5 的逐股深度数据（财报/cninfo/行情）在候选
确定后才能取，保持按需，不在此预取。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent          # data/
LOG_DIR = DATA_DIR / ".cache"

# (key, 名称, 命令参数, 是否快任务, 超时秒)
JOBS = [
    ("macro",    "宏观面板",       ["scripts/snapshot_macro.py"],                  True,  300),
    ("policy",   "政策事件",       ["scripts/policy_track.py"],                    True,  300),
    ("market",   "大盘快照",       ["scripts/snapshot_market.py"],                 True,  300),
    ("industry", "行业体检",       ["scripts/snapshot_industry.py", "--top", "15"], True,  600),
    ("earnings", "业绩预告",       ["scripts/earnings_radar.py", "--top", "1"],    True,  300),
    ("health",   "数据体检",       ["scripts/data_health.py"],                     True,  300),
    ("screen",   "全市场增强(慢)", ["scripts/screen_all_market.py", "--enrich", "0", "--top", "40"],
                 False, 3600),
]


def parse_args():
    p = argparse.ArgumentParser(description="数据预热编排")
    p.add_argument("--quick", action="store_true", help="只预热快数据，跳过全市场增强")
    p.add_argument("--only", help="只跑指定任务（key：macro/policy/market/industry/earnings/health/screen）")
    return p.parse_args()


def _run_job(name: str, args: list[str], timeout: int, logf) -> tuple[bool, float]:
    """跑一个子任务，输出进日志。返回 (成功, 耗时秒)。"""
    t0 = time.time()
    logf.write(f"\n{'='*60}\n[{name}] {datetime.now():%H:%M:%S} {' '.join(args)}\n{'='*60}\n")
    logf.flush()
    try:
        r = subprocess.run(
            [sys.executable, *args],
            cwd=DATA_DIR, stdout=logf, stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return r.returncode == 0, time.time() - t0
    except subprocess.TimeoutExpired:
        logf.write(f"\n[{name}] ❌ 超时（>{timeout}s）\n")
        return False, time.time() - t0
    except Exception as e:
        logf.write(f"\n[{name}] ❌ 异常：{e}\n")
        return False, time.time() - t0


def main():
    args = parse_args()
    jobs = JOBS
    if args.only:
        jobs = [j for j in JOBS if j[0] == args.only]
        if not jobs:
            print(f"未知任务 key：{args.only}（可选：{', '.join(j[0] for j in JOBS)}）")
            return
    elif args.quick:
        jobs = [j for j in JOBS if j[3]]   # 仅快任务

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"refresh_{date.today():%Y%m%d}.log"

    print(f"# 数据预热 refresh_data（{datetime.now():%Y-%m-%d %H:%M}）\n")
    if date.today().weekday() >= 5:
        print("> 提示：今天是周末，A股不交易；行情类数据为最近交易日收盘值。\n")
    print(f"- 任务数：{len(jobs)}　|　日志：{log_path}")
    if any(j[0] == "screen" for j in jobs):
        print("- ⏳ 含「全市场增强」约 30 分钟，可离开；另开终端 `tail -f` 上面日志看进度")
    print()

    results = []
    with open(log_path, "a", encoding="utf-8") as logf:
        logf.write(f"\n\n########## refresh {datetime.now():%Y-%m-%d %H:%M:%S} ##########\n")
        for i, (key, name, cmd, _quick, timeout) in enumerate(jobs, 1):
            print(f"[{i}/{len(jobs)}] {name} ... ", end="", flush=True)
            ok, secs = _run_job(name, cmd, timeout, logf)
            results.append((name, ok, secs))
            print(f"{'✅' if ok else '❌'} {secs:.1f}s")

    # 汇总
    ok_n = sum(1 for _, ok, _ in results if ok)
    total = sum(s for _, _, s in results)
    print(f"\n## 汇总\n")
    print(f"- {ok_n}/{len(results)} 成功，总耗时 {total/60:.1f} 分钟")
    failed = [n for n, ok, _ in results if not ok]
    if failed:
        print(f"- ❌ 失败：{', '.join(failed)} —— 详见日志 {log_path}")
    else:
        print(f"- ✅ 缓存已预热，后续 weekly_pick / 分析可秒级读取")
    print(f"- 日志：{log_path}")


if __name__ == "__main__":
    main()
