#!/usr/bin/env python3
"""
central_pom_scan.py — 上传前静态点伤：把 Central 会"整批判 FAILED"的 pom 缺陷扫出来。

背景：central-publishing 插件的上传回执只说明包送到了，Central 之后还会异步校验整批组件，
任何一处不合格整批 FAILED，而 mvn 侧早已 BUILD SUCCESS； deployments 清单又有一小时量级的
滞后。所以下面这几类缺陷必须在上传前用静态扫描看清，而不是等队列回来。

只认"会被打 bundle 的 pom"：从仓根 pom 的 `central` profile + central-publishing-maven-plugin
出发，按 Maven 自己的口径解析 <modules> 递归出 reactor（被注释掉的 module 因为 XML 解析天然
跳过 —— 这正是踩过的坑：靠 grep 判断模块在不在 reactor 里会误报）。z-boot 那种"根 pom 无
<modules>、五个文件夹各自独立成工程、central profile 只在根上被继承"的拓扑也认。

缺陷类：
  A  无 central profile / 不发 Central            → 只报 excludeArtifacts 清单，不判缺陷
  B  maven.deploy.skip=true 但没进 excludeArtifacts —— 该插件不认 skip，模块照样进 bundle
  C  发布的 pom 缺自己的 <name>                   → Central: Project name is missing
                                                    （parent 的 name 不会被解析过来，实测）
  D  <dependencyManagement> 里的条目没有 <version>  → BOM 发出去是空/半空，外部 import 才炸
  E  build/plugins 里的插件无 version 且无处兜底    → 浮到"当前最新"，构建随时间漂移

用法：
  python3 central_pom_scan.py                 # 扫 ../ 下所有带 central profile 的仓
  python3 central_pom_scan.py --repo z-ctc    # 只扫一个仓
  python3 central_pom_scan.py --base /path    # 换 foundation 根（默认取本脚本所在仓的 ../）
  python3 central_pom_scan.py --path "$PWD"   # 只点这一个仓根（CI 里没有兄弟仓时用）
退出码：0=无缺陷，1=有缺陷，2=扫描本身失败（pom 解析不了）。
"""
import os
import sys
import glob
import argparse
import xml.etree.ElementTree as ET

NS = '{http://maven.apache.org/POM/4.0.0}'

# 权威可读性模块的缓存句柄（懒加载，_readability() 负责填）。
_READABILITY = None


def txt(e):
    return None if e is None else (e.text or '').strip()


def fc(e, name):
    return e.find(NS + name) if e is not None else None


def fcs(e, name):
    return e.findall(NS + name) if e is not None else []


def parse(p):
    """解析一个 pom。读不了返回 None（调用方各自处理，这是本模块的既有契约）。

    用 lead 仓的权威判据 pom_readability 而不是裸 ET：ET 放行但 Maven 拒收的三类
    （XML 1.1 声明 / 根元素缺 POM 命名空间 / 根元素非 project）只有那里能抓住。
    找不到该模块时退回裸 ET —— 判据退化成"ET 说了算"，但不会崩。
    """
    try:
        mod = _readability()
    except ImportError:
        mod = None
    if mod is None:
        try:
            return ET.parse(p).getroot()
        except Exception:
            return None
    try:
        return mod.check_file(p)
    except Exception:
        return None


def parse_reason(p):
    """读不了的原因（给缺陷报告用）。读得了返回 None。"""
    try:
        mod = _readability()
    except ImportError:
        mod = None
    if mod is None:
        try:
            ET.parse(p)
            return None
        except Exception as ex:
            return str(ex)
    try:
        mod.check_file(p)
        return None
    except Exception as ex:
        return str(ex)


def _readability():
    """按需加载 lead 仓的 pom_readability 模块（单仓 CI 里可能没有 lead 仓）。"""
    global _READABILITY
    if _READABILITY is None:
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        # 候选路径：从本仓 _doc/003_script/ 往上找 lead 仓。
        cands = []
        up = here
        for _ in range(6):
            up = os.path.dirname(up)
            cands.append(os.path.join(up, 'z-opc-foundation-lead', '003_辅助能力',
                                      'maven-inventory', 'script', 'pom_readability.py'))
        for c in cands:
            if os.path.isfile(c):
                spec = importlib.util.spec_from_file_location('pom_readability', c)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _READABILITY = mod
                return mod
        raise ImportError('找不到 pom_readability.py')
    return _READABILITY


def child_artifacts(pom_path):
    """直接子 pom（parent.artifactId == 本 pom artifactId）—— z-boot 按文件夹独立成工程靠这个识别。"""
    r = parse(pom_path)
    if r is None:
        raise ValueError('解析失败 %s：%s' % (pom_path, parse_reason(pom_path) or '未知原因'))
    me = txt(fc(r, 'artifactId'))
    out = []
    for cand in sorted(glob.glob(os.path.join(os.path.dirname(pom_path), '*', 'pom.xml'))):
        cr = parse(cand)
        par = fc(cr, 'parent') if cr is not None else None
        if par is not None and txt(fc(par, 'artifactId')) == me:
            out.append(os.path.normpath(cand))
    return out


def reactor(pom_path):
    """pom_path 及其 <modules> 下游（含自身）。注释掉的 module 因 XML 解析天然不在。"""
    r = parse(pom_path)
    if r is None:
        raise ValueError('解析失败 %s：%s' % (pom_path, parse_reason(pom_path) or '未知原因'))
    out, seen = [], {os.path.normpath(pom_path)}

    def walk(cur):
        rr = parse(cur)
        if rr is None:
            raise ValueError('解析失败 %s：%s' % (cur, parse_reason(cur) or '未知原因'))
        out.append(cur)
        m = fc(rr, 'modules')
        if m is None:
            return
        for c in m.findall(NS + 'module'):
            np = os.path.normpath(os.path.join(os.path.dirname(cur), txt(c), 'pom.xml'))
            if np in seen or not os.path.isfile(np):
                continue
            seen.add(np)
            walk(np)

    walk(pom_path)
    return out


def plugin_pins(*roots):
    """这些 pom 里（含 profiles、含 pluginManagement）钉了 version 的插件集合 —— E 的兜底口径。"""
    have = set()
    for p in roots:
        r = parse(p)
        if r is None:
            continue
        holders = []
        b = fc(r, 'build')
        if b is not None:
            holders += [fc(b, 'plugins'), fc(fc(b, 'pluginManagement'), 'plugins')]
        for pf in fcs(fc(r, 'profiles'), 'profile'):
            pb = fc(pf, 'build')
            if pb is not None:
                holders += [fc(pb, 'plugins'), fc(fc(pb, 'pluginManagement'), 'plugins')]
        for bl in holders:
            if bl is None:
                continue
            for pl in bl.findall(NS + 'plugin'):
                if fc(pl, 'version') is not None:
                    have.add(txt(fc(pl, 'artifactId')))
    return have


def parent_chain(pom_path, base):
    """沿 <parent> 往上走，收集**真实可达**的父 pom 文件（含仓内的）。

    为什么必须追这条链：E 类的判据是"插件无 version 且父链无兜底"。而插件版本的兜底
    往往在 z-boot-parent 1.2.0 的 pluginManagement 里（surefire 2.22.2 /
    spring-boot-maven-plugin ${spring-boot.version}）。z-config / z-mq / z-oss / z-team /
    z-wf 这些仓根 pom 的 <parent> 都写了 z-boot-parent 且 <relativePath></relativePath>（空），
    **解析时该父来自本地仓**，不在当前仓目录里 —— 只看"本仓内的 pom"会全线误判 E。

    相对路径解析规则照 Maven 的来：
      · relativePath 缺省 = ../pom.xml
      · relativePath 为空串 = 不从文件系统找，直接用仓库坐标（但 z-boot-parent 是同工作区里的
        独立工程，坐标能对上 ⇒ 仍要按坐标在工作区内找到它，否则兜底判断就是假的）
      · relativePath 显式给路径 = 按它找
    坐标兜底：在**工作区根**（foundation 根）下按 artifactId 找同名工程（z-boot-parent 就在
    <workspace>/z-boot/z-boot-parent）。注意传的必须是 foundation 根而不是仓根 —— 仓根下找不到
    兄弟仓里的独立工程，兜底就断在这里，E 类全线误报。
    """
    chain, seen = [], set()
    cur = os.path.abspath(pom_path)
    while cur and cur not in seen:
        seen.add(cur)
        r = parse(cur)
        if r is None:
            break
        chain.append(cur)
        par = fc(r, 'parent')
        if par is None:
            break
        pa = txt(fc(par, 'artifactId'))
        rp = txt(fc(par, 'relativePath'))
        if rp is None:
            rp = '../pom.xml'
        nxt = None
        if rp.strip():
            cand = os.path.normpath(os.path.join(os.path.dirname(cur), rp))
            if os.path.isdir(cand):
                cand = os.path.join(cand, 'pom.xml')
            if os.path.isfile(cand):
                nxt = cand
        if nxt is None and pa:
            # 坐标兜底：在**工作区根**下按 artifactId 找同名工程（z-boot-parent 这类独立工程）。
            # 索引是全局懒建的，避免每个 pom 都全盘 glob + parse。
            nxt = coord_index(base).get(pa)
        if nxt is None:
            break
        cur = nxt
    return chain


_COORD_INDEX = {}


def coord_index(workspace):
    """{artifactId: pom 绝对路径} —— 工作区内所有独立工程的坐标索引（懒建一次）。

    为什么需要它：z-boot-parent 是**独立工程**（foundation/z-boot/z-boot-parent），不在任何
    消费仓的目录里，而 z-config / z-mq / z-oss / z-team / z-wf 的 <parent> 都写了
    `<relativePath></relativePath>`（空 ⇒ Maven 不从文件系统找）。不按坐标回工作区找它，
    父链就断在这儿，pluginManagement 的兜底版本看不到 ⇒ E 类全线误报。
    """
    key = os.path.abspath(workspace)
    if key in _COORD_INDEX:
        return _COORD_INDEX[key]
    idx = {}
    pats = [
        os.path.join(key, 'pom.xml'),
        os.path.join(key, '*', 'pom.xml'),
        os.path.join(key, '*', '*', 'pom.xml'),
    ]
    for pat in pats:
        for guess in glob.glob(pat):
            if 'node_modules' in guess:
                continue
            try:
                gr = ET.parse(guess).getroot()
            except Exception:
                continue  # 静默：坏 pom 由调用方自己的 parse 报，避免索引时刷屏
            a = txt(fc(gr, 'artifactId'))
            if a:
                idx.setdefault(a, os.path.abspath(guess))
    _COORD_INDEX[key] = idx
    return idx


def scan_repo(rp, verbose, workspace=None):
    root_pom = os.path.join(rp, 'pom.xml')
    root = parse(root_pom)
    if root is None:
        # 根 pom 读不了 ⇒ 整个仓的 pom 树都判不了。原写法在这里 return None，
        # CLI 会说"该仓没有 central profile"——那是**假绿**：仓有 central 配置，
        # 只是根 pom 坏了，于是所有 Central 缺陷都静默跳过。改成抛，让 CLI 转 exit 2
        # （扫描本身失败），并带上原因。
        raise ValueError('根 pom 读不了（Maven 读不了）：%s' % (parse_reason(root_pom) or '未知原因'))
    if 'central-publishing-maven-plugin' not in open(root_pom, encoding='utf-8').read():
        return None
    prof = next((p for p in fcs(fc(root, 'profiles'), 'profile')
                 if txt(fc(p, 'id')) == 'central'), None)
    if prof is None:
        return None

    # 父链搜索的工作区根：默认取仓根的上一级（foundation 根），这样 z-boot-parent 这类
    # 兄弟仓里的独立工程才找得到。调用方可显式传。
    ws = os.path.abspath(workspace or os.path.dirname(os.path.abspath(rp)))

    excludes = {txt(x) for x in prof.iter(NS + 'excludeArtifact')}
    me = txt(fc(root, 'artifactId'))

    # 发布集合按 Maven 口径取，不按目录取：根带 <modules> 时，被注释掉的 module 就是不发
    # （z-config-admin、z-oss/_frontend、z-gw-examples 实测都是这种"目录在、reactor 不在"）；
    # 根不带 <modules> 时（z-boot 1.0.19 的按文件夹拓扑），每个直接子工程各算一个 reactor。
    poms = []
    if fc(root, 'modules') is not None:
        poms = reactor(root_pom)
    else:
        poms.append(os.path.normpath(root_pom))
        for child in child_artifacts(root_pom):
            cr = parse(child)
            if fc(cr, 'modules') is not None:
                poms += reactor(child)                    # 文件夹根 + 它自己的 reactor
            else:
                poms.append(child)                        # 叶子（deps / fleet BOM 自身即一条坐标）
    # 去重保序
    uniq, seen = [], set()
    for p in poms:
        p = os.path.normpath(p)
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    poms = uniq

    # 插件版本兜底：走**真实父链**（含仓内相对路径父 pom 与工作区内的坐标父 pom），
    # 再并上本仓 reactor 里那些"是别人父"的 pom（子模块可继承父的 pluginManagement）。
    chain_poms = list(parent_chain(root_pom, ws))
    for p in poms:
        chain_poms += parent_chain(p, ws)
    pins = plugin_pins(*chain_poms)

    problems = []
    for p in poms:
        r = parse(p)
        if r is None:
            # 解析失败 = Maven 自己都读不了这个 pom（不是"我们读不出来"）。
            # 把原因带上，别只写"解析失败"三个字 —— 排查的人需要知道是注释里写了
            # `--`，还是缺命名空间，还是 XML 1.1。
            reason = parse_reason(p) or '未知原因'
            problems.append('! %s 解析失败（Maven 读不了）：%s' % (os.path.relpath(p, rp), reason))
            continue
        a = txt(fc(r, 'artifactId'))
        if a in excludes:
            continue
        rel = os.path.relpath(p, rp)
        prp = fc(r, 'properties')
        skip = txt(fc(prp, 'maven.deploy.skip')) if prp is not None else None
        if skip and skip.lower() == 'true':
            problems.append('B %s(%s) deploy.skip=true 但没进 excludeArtifacts —— 插件不看它，照样进 bundle'
                            % (a, rel))
        if fc(r, 'name') is None:
            problems.append('C %s(%s) 缺 <name> —— Central 报 Project name is missing' % (a, rel))
        dmn = fc(r, 'dependencyManagement')
        dml = fc(dmn, 'dependencies') if dmn is not None else None
        if dml is not None:
            for dep in dml.findall(NS + 'dependency'):
                if fc(dep, 'version') is None:
                    problems.append('D %s(%s) dependencyManagement 无 version: %s:%s'
                                    % (a, rel, txt(fc(dep, 'groupId')), txt(fc(dep, 'artifactId'))))
        b = fc(r, 'build')
        for pl in (fc(b, 'plugins').findall(NS + 'plugin') if b is not None and fc(b, 'plugins') is not None else []):
            pa = txt(fc(pl, 'artifactId'))
            if fc(pl, 'version') is None and pa not in pins:
                problems.append('E %s(%s) 插件 %s 无 version 且父链无兜底 —— 浮到最新，构建随时间漂移' % (a, rel, pa))
    if verbose:
        print('  reactor %d 个 pom，excludeArtifacts=%s' % (len(poms), ','.join(sorted(excludes)) or '-'))
    return sorted(set(problems))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description='Central 上传前静态点伤')
    # 本脚本住在 <foundation>/z-boot/_doc/003_script/ ⇒ foundation 是 up 三层
    ap.add_argument('--base', default=os.path.dirname(os.path.dirname(os.path.dirname(here))))
    ap.add_argument('--repo', default=None)
    # CI 里只 checkout 了本仓，没有"foundation 根"可上溯 ⇒ 直接点仓根
    ap.add_argument('--path', default=None, help='只扫这一个仓根（CI/单仓场景）')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

    if args.path:
        if not os.path.isfile(os.path.join(args.path, 'pom.xml')):
            print('找不到仓根 pom：%s' % os.path.join(args.path, 'pom.xml'), file=sys.stderr)
            return 2
        try:
            res = scan_repo(args.path, args.verbose, workspace=args.base)
        except Exception as ex:
            print('扫描失败: %s' % ex, file=sys.stderr)
            return 2
        if res is None:
            print('该仓没有 central profile / central-publishing 插件 —— 不判缺陷')
            return 0
        for line in res:
            print('    ' + line)
        print('\n带 central profile 的仓: 1  有缺陷的仓: %d' % (1 if res else 0))
        return 1 if res else 0

    if not os.path.isdir(args.base):
        print('找不到 foundation 根：%s' % args.base, file=sys.stderr)
        return 2
    names = [args.repo] if args.repo else sorted(os.listdir(args.base))
    n_repos = n_bad = 0
    for name in names:
        rp = os.path.join(args.base, name)
        if name.startswith('.') or not os.path.isfile(os.path.join(rp, 'pom.xml')):
            continue
        try:
            res = scan_repo(rp, args.verbose, workspace=args.base)
        except Exception as ex:
            print('%-14s ! 扫描失败: %s' % (name, ex), file=sys.stderr)
            n_bad += 1
            continue
        if res is None:
            continue
        n_repos += 1
        if res:
            n_bad += 1
            print('=== %s' % name)
            for line in res:
                print('    ' + line)
        elif args.verbose:
            print('OK  %s' % name)
    print('\n带 central profile 的仓: %d  有缺陷的仓: %d' % (n_repos, n_bad))
    return 1 if n_bad else 0


if __name__ == '__main__':
    sys.exit(main())
