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
退出码：0=无缺陷，1=有缺陷，2=扫描本身失败（pom 解析不了）。
"""
import os
import sys
import glob
import argparse
import xml.etree.ElementTree as ET

NS = '{http://maven.apache.org/POM/4.0.0}'


def txt(e):
    return None if e is None else (e.text or '').strip()


def fc(e, name):
    return e.find(NS + name) if e is not None else None


def fcs(e, name):
    return e.findall(NS + name) if e is not None else []


def parse(p):
    try:
        return ET.parse(p).getroot()
    except Exception as ex:
        sys.stderr.write('PARSE-FAIL %s: %s\n' % (p, ex))
        return None


def child_artifacts(pom_path):
    """直接子 pom（parent.artifactId == 本 pom artifactId）—— z-boot 按文件夹独立成工程靠这个识别。"""
    r = parse(pom_path)
    if r is None:
        raise ValueError('解析失败 ' + pom_path)
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
        raise ValueError('解析失败 ' + pom_path)
    out, seen = [], {os.path.normpath(pom_path)}

    def walk(cur):
        rr = parse(cur)
        if rr is None:
            raise ValueError('解析失败 ' + cur)
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


def scan_repo(rp, verbose):
    root_pom = os.path.join(rp, 'pom.xml')
    root = parse(root_pom)
    if root is None:
        return None
    if 'central-publishing-maven-plugin' not in open(root_pom, encoding='utf-8').read():
        return None
    prof = next((p for p in fcs(fc(root, 'profiles'), 'profile')
                 if txt(fc(p, 'id')) == 'central'), None)
    if prof is None:
        return None

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

    # 插件版本兜底：父 pom 链 + 各 reactor 根（子模块可继承父的 pluginManagement）
    parent_chain = [root_pom]
    for p in poms:
        r = parse(p)
        par = fc(r, 'parent') if r is not None else None
        if par is not None and txt(fc(par, 'artifactId')) == me:
            parent_chain.append(p)
    pins = plugin_pins(*parent_chain)

    problems = []
    for p in poms:
        r = parse(p)
        if r is None:
            problems.append('! %s 解析失败' % os.path.relpath(p, rp))
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
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

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
            res = scan_repo(rp, args.verbose)
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
