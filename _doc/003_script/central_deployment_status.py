#!/usr/bin/env python3
"""
central_deployment_status.py — 读 Central 的 deployments 清单，只看状态，不打印任何凭证。

为什么要有它：`mvn deploy` 的 BUILD SUCCESS 只代表"包送到了"。Central 之后还要异步校验整批
组件，任何一处不合格**整批 FAILED**（实测过：某个 component 的 pom 缺 <name> 就够）；而
repo1 上点 404 既可能是"还在排队"也可能是"被判死了"，一小时量级的滞后里两者长得一样。
所以判"这批到底发出去没有"要两处看：/deployments 给状态与原因，repo1_census 给最终可见性。

只用 GET /api/v1/publisher/deployments —— /status 那个端点实测恒 500（换写法也没用）。

用法：
  python3 z-boot/_doc/003_script/central_deployment_status.py                 # 按创建时间列最近 15 条
  python3 z-boot/_doc/003_script/central_deployment_status.py --id 9f95       # 只看某个 deploymentId 前缀
  python3 z-boot/_doc/003_script/central_deployment_status.py --ids a,b,c     # 一次采样对多个批次（整批发完就这么核）
  python3 z-boot/_doc/003_script/central_deployment_status.py --repo z-cache  # 只看含该 artifactId 的批次
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

ZBOOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
API = "https://central.sonatype.com/api/v1/publisher/deployments"


def creds():
    env = {}
    p = os.path.join(ZBOOT, ".env")
    if not os.path.isfile(p):
        sys.exit("✗ z-boot/.env 不存在")
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    if not env.get("CENTRAL_USERNAME") or not env.get("CENTRAL_TOKEN"):
        sys.exit("✗ .env 缺 CENTRAL_USERNAME / CENTRAL_TOKEN")
    return env["CENTRAL_USERNAME"], env["CENTRAL_TOKEN"]


def fetch(u, t, page, size):
    req = urllib.request.Request(f"{API}?page={page}&size={size}")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{u}:{t}".encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"✗ /deployments?page={page}&size={size} http={e.code}（只报状态码，不回显内容）")
    return body if isinstance(body, list) else body.get("deployments", [])


def sample(u, t):
    """这个端点不老实：size>100 直接 400；给了 size=100 也只回 ~69 条，且**不按时序排**，
    page=2 又是空——所以"这一轮没读到"绝不等于"这条不存在"（实测同一条 deployment
    在 size=40 的清单里没有、size=3 的清单里排第一）。多取几种 (page,size) 形状去并集，
    并把"没覆盖到"如实报出来，而不是假装清单是全的。"""
    seen = {}
    for page, size in [(1, 3), (1, 5), (1, 20), (1, 40), (1, 100), (2, 5), (3, 5), (2, 20), (2, 100)]:
        for d in fetch(u, t, page, size):
            did = str(d.get("deploymentId") or "")
            if did:
                seen[did] = d
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default="", help="只看这个 deploymentId 前缀")
    ap.add_argument("--ids", default="", help="逗号分隔的多个前缀（一次采样对多个批次，别一 id 打一遍端点）")
    ap.add_argument("--repo", default="", help="只看 purl 里含这个 artifactId 前缀的组件所在批次")
    ap.add_argument("--latest", type=int, default=15, help="按创建时间列最近 N 条")
    a = ap.parse_args()
    u, t = creds()
    seen = sample(u, t)
    if not seen:
        print("⚠ /deployments 一条都没读到 —— 是没读到，不是没有发布（零命中与零输入长得一样）")
        return 2
    print(f"并集读到 {len(seen)} 条 deployment（清单不全是被端点的截断行为限制的，不是没发）")

    # createTimestamp/updateTimestamp 是 ISO UTC 串（'2026-09-29T00:07:50.086Z'），不是 epoch —— 别当数字用
    rows = sorted(seen.values(), key=lambda d: str(d.get("createTimestamp") or ""), reverse=True)
    want = [p for p in a.ids.split(",") if p]
    bad = 0
    shown = 0
    found = set()
    for d in rows:
        did = str(d.get("deploymentId") or "")
        comps = d.get("deploymentComponents") or []
        purls = {c.get("purl") or "" for c in comps}
        paths = {c.get("path") or "" for c in comps}
        errs = [(c.get("purl") or c.get("name"), e) for c in comps for e in (c.get("errors") or [])]
        if want:
            hit = next((p for p in want if did.startswith(p)), None)
            if hit is None:
                continue
            found.add(hit)
        elif a.id:
            if not did.startswith(a.id):
                continue
        elif a.repo:
            hit = any(f"/{a.repo}@" in p for p in purls) or any(f"/{a.repo}/" in pa for pa in paths)
            if not hit:
                continue
        elif shown >= a.latest:
            continue
        shown += 1
        state = str(d.get("deploymentState") or "?").upper()
        print(f"  {did[:8]}  {state:<11} {str(d.get('createTimestamp') or '')[:19]}Z  "
              f"组件={len(comps)} 件/坐标={len(purls)}  错误={len(errs)}")
        if state not in ("PUBLISHED", "VALIDATED", "RUNNING", "QUEUED", "PENDING"):
            bad += 1
            for p, e in errs[:8]:
                print(f"        ✗ {p}  {str(e)[:150]}")
    if a.id and shown == 0:
        print(f"  ⚠ 并集里没有 {a.id} 开头的批次 —— 端点清单是不全的，隔几分钟重采；别据此判失败")
    missing = [p for p in want if p not in found]
    if missing:
        print(f"  ⚠ 这 {len(missing)} 个前缀本轮没读到：{' '.join(missing)}")
        print("     端点的清单是不全的（size=100 也只回 ~69 条、page=2 换个批次），**没读到 ≠ 没发布 ≠ 失败**，隔几分钟重采")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
