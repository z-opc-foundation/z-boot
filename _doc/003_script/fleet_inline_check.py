#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fleet_inline_check.py —— 逐件回读 starter **发布件**里内联的兄弟仓版本，
与 z-boot-fleet 源码当前的族格（<z-*.version>）对账。

为什么需要这一段（verify_central.sh 第 4 段「发布件内容比对」盖不住）：
  第 4 段比的是「同一个构件：线上 pom vs 本地源 pom」，而它比的两个维度是
  <dependencyManagement> 的受管坐标集合与 <properties> 的键值。叶子 starter 的
  源 pom 里这两样都**没有版本可管**——它写 <dependency> 不写 <version>（版本由
  import 进来的 z-boot-fleet 供），发布件里才由 flatten 把算出的版本**内联成字面量**。
  于是源 pom 无 DM 无 props、发布件也无 DM 无 props ⇒ 第 4 段对 starter 恒判 SAME。

后果是这一类欠账闸门永远看不见：
  fleet 把 <z-kb.version> 从 1.0.5 抬到 1.0.7（614e6b5），
  但 22 件 starter 的发布件里内联的字面量还是 1.0.5 ——
  Central 不许覆盖旧版本，要生效必须重发这些 starter；只抬 fleet 号 = **只做一半**。
  消费者拉到的 starter 仍会带走旧兄弟仓，而闸门全绿。

⚠ 口径必须是 repo1 的发布件，不能是本地 .flattened-pom.xml：
  本地扁平件是任何人跑一次 mvn 就从同一份源码重算出来的，跟源码同源自洽 ⇒ 恒等式成立、
  闸门锁死也抓不到任何东西。「发布件里到底写着什么号」只有 repo1 说了算。

用法:
  ./fleet_inline_check.py                # 对 repo1 回读，逐件对账
  ./fleet_inline_check.py --self-test     # 跑内置阳性对照 + 缺 version 反向对照
  ./fleet_inline_check.py --only z-boot-gw-starter

退出码: 0 全绿 / 1 有不一致、取不到发布件、或对照本身坏了
"""

import argparse
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

NS = '{http://maven.apache.org/POM/4.0.0}'
GROUP = 'io.github.yuku123'
CENTRAL = os.environ.get('CENTRAL_BASE', 'https://repo1.maven.org/maven2')
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# 临时件落工作区根、带 _tmp- 前缀（本机 /tmp 会在会话中途被清，不能拿它当下载目录）
SCRATCH_DIR = os.path.dirname(REPO_ROOT)
AGGREGATORS = ('z-boot-starter', 'z-boot-integration-starters')
FLEET_POM = os.path.join(REPO_ROOT, 'z-boot-fleet', 'pom.xml')


def txt(elem, tag):
    c = elem.find(NS + tag)
    return (c.text or '').strip() if c is not None and c.text else None


def parse_xml(blob):
    return ET.fromstring(blob)


def fleet_slots():
    """fleet 源码里的族格：{z-gw: 1.0.6, ...}（properties 里所有 *.version 键）"""
    root = parse_xml(open(FLEET_POM, 'rb').read())
    props = root.find(NS + 'properties')
    if props is None:
        die('读不到 %s 的 <properties> —— fleet 源码坏了，本闸无从判起' % FLEET_POM)
    out = {}
    for c in props:
        k = c.tag.replace(NS, '')
        if k.endswith('.version'):
            out[k[:-len('.version')]] = (c.text or '').strip()
    return out


def starter_modules():
    """按 folder 盘出全部 starter 源 pom 的 (artifactId, version, path)。"""
    mods = []
    for agg in AGGREGATORS:
        d = os.path.join(REPO_ROOT, agg)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            sp = os.path.join(d, name, 'pom.xml')
            if not os.path.isfile(sp):
                continue
            root = parse_xml(open(sp, 'rb').read())
            aid, ver = txt(root, 'artifactId'), txt(root, 'version')
            if not aid or not ver:
                die('%s 缺 <artifactId>/<version>（版本字面量是发版尺的依据，不能省）' % sp)
            mods.append((aid, ver, sp))
    return mods


def family_of(aid, fam):
    """把依赖坐标归到 fleet 族：取最长匹配前缀（z-agent-kernel 优先于 z-agent）。"""
    cands = [f for f in fam if aid == f or aid.startswith(f + '-')]
    return max(cands, key=len) if cands else None


def fetch_pom(aid, ver):
    """⚠ 走 curl 而不是 urllib：本机的 python 系统证书链拉不动 repo1（SSLCertVerificationError），
    verify_central.sh 全篇也用 curl。404 与网络故障要分得开，所以判 http_code 而不是「有没有内容」。
    body 落临时文件、状态码走 stdout，不去猜 curl 的输出先后。"""
    url = '%s/%s/%s/%s/%s-%s.pom' % (CENTRAL, GROUP.replace('.', '/'), aid, ver, aid, ver)
    fd, tmp = tempfile.mkstemp(prefix='_tmp-fleet-inline-', suffix='.pom', dir=SCRATCH_DIR)
    os.close(fd)
    try:
        p = subprocess.run(['curl', '-sS', '--max-time', '45', '-w', '%{http_code}',
                            '-o', tmp, url], capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError('curl rc=%d %s' % (p.returncode, (p.stderr or '').strip()[:80]))
        code = p.stdout.strip()
        if code != '200':
            raise RuntimeError('HTTP %s' % code)
        with open(tmp, 'rb') as fh:
            return fh.read()
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def compare(published_root, fam):
    """返回 (checks, violations)。checks = [(dep, family, fleet 格, 发布件内联值)]"""
    checks, viol = [], []
    deps = root_deps(published_root)
    for dep in deps:
        if txt(dep, 'groupId') != GROUP:
            continue
        daid = txt(dep, 'artifactId')
        if daid is None:
            continue
        fam_key = family_of(daid, fam)
        if fam_key is None:
            continue
        inline = txt(dep, 'version')
        slot = fam[fam_key]
        checks.append((daid, fam_key, slot, inline))
        if inline is None:
            viol.append('%s 的发布件里 %s 没有 <version> —— flatten 没把版本内联成字面量，'
                        '消费者拿不到版本' % (aid_of(published_root), daid))
        elif '${' in inline:
            viol.append('%s 的发布件里 %s 版本仍是占位符 %s —— 属性在发布件里无从解析'
                        % (aid_of(published_root), daid, inline))
        elif inline != slot:
            viol.append('%s 发布件内联 %s=%s，fleet 当前格 %s.version=%s'
                        ' —— fleet 抬了号但这件 starter 没重发（Central 不许覆盖，必须抬 starter 版本重发）'
                        % (aid_of(published_root), daid, inline, fam_key, slot))
    return checks, viol


def aid_of(root):
    return txt(root, 'artifactId') or '?'


def root_deps(root):
    e = root.find(NS + 'dependencies')
    return list(e) if e is not None else []


def die(msg):
    print('✗ %s' % msg)
    sys.exit(1)


# ---------------- 对照（gate 自身的刀） ----------------

MINI_PUBLISHED = """<project xmlns="http://maven.apache.org/POM/4.0.0"><artifactId>z-boot-demo-starter</artifactId>
<dependencies>
  <dependency><groupId>%s</groupId><artifactId>z-gw-spring-boot-starter</artifactId><version>1.0.6</version></dependency>
  <dependency><groupId>%s</groupId><artifactId>z-kb-spring-boot-starter</artifactId></dependency>
  <dependency><groupId>%s</groupId><artifactId>z-mq-spring-boot-starter</artifactId><version>${z-mq.version}</version></dependency>
  <dependency><groupId>%s</groupId><artifactId>z-util-core</artifactId><version>1.0.19</version></dependency>
  <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter</artifactId><version>2.7.18</version></dependency>
</dependencies></project>""" % (GROUP, GROUP, GROUP, GROUP)


def self_test():
    """对照：喂一份已知带三种病灶 + 一条正常格 + 一条外部坐标的发布件，
    闸门必须逐条抓到病灶、且不误报正常的那两条。漏一条或误报一条都是闸坏了。"""
    fam = {'z-gw': '9.9.9', 'z-kb': '1.0.7', 'z-mq': '1.3.1', 'z-util': '1.0.19'}
    root = parse_xml(MINI_PUBLISHED)
    checks, viol = compare(root, fam)
    got = '\n'.join(viol)
    want = [('陈旧未重发(z-gw)', '内联 z-gw-spring-boot-starter=1.0.6'),
            ('缺 <version>(z-kb)', 'z-kb-spring-boot-starter 没有 <version>'),
            ('占位符未解析(z-mq)', '${z-mq.version}')]
    bad = [label for label, needle in want if needle not in got]
    # 受管集合必须正好是 4 条兄弟仓依赖（外部 spring-boot-starter 不该进尺），
    # 报警必须正好是 3 条（正常格 z-util 与外部坐标都不能报）
    shape = len(checks) != 4 or len(viol) != 3
    print('  对照计数: 应比 4 条(实得 %d)、应报 3 条(实得 %d)、三类病灶命中 %d/3'
          % (len(checks), len(viol), len(want) - len(bad)))
    for label in bad:
        print('    ✗ 没抓到: %s' % label)
    if shape:
        for c in checks:
            print('      check: %s' % (c,))
        for v in viol:
            print('      viol : %s' % v)
        print('✗ 对照本身坏了 —— 尺的口径不对（误报外部坐标、或漏抓一类病灶）')
        return 1
    if bad:
        print('✗ 对照本身坏了 —— 有病灶没抓到')
        return 1
    print('  ✓ 对照通过：陈旧/缺版本/占位符三类都抓得到，一致面值与外部坐标不误报')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true', help='只跑内置对照')
    ap.add_argument('--only', default=None, help='只验这些构件（逗号分隔）')
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())

    fam = fleet_slots()
    mods = starter_modules()
    wanted = None
    if args.only:
        wanted = {x.strip() for x in args.only.split(',') if x.strip()}
        mods = [m for m in mods if m[0] in wanted]
    print('fleet 族格 %d 个 · 待验 starter %d 件（源 pom 的 <version> 即「应该是哪一发布件」）'
          % (len(fam), len(mods)))

    all_checks, all_viol, skipped = [], [], []
    for aid, ver, _ in mods:
        try:
            root = parse_xml(fetch_pom(aid, ver))
        except Exception as e:                                    # noqa: BLE001
            skipped.append('%s:%s 取不到发布件（%s）' % (aid, ver, type(e).__name__))
            continue
        checks, viol = compare(root, fam)
        all_checks.extend((aid, *c) for c in checks)
        all_viol.extend(viol)
        mark = '✓' if not viol and checks else ('✗' if viol else '·')
        detail = ', '.join('%s=%s' % (c[0], c[3]) for c in checks) or '无兄弟仓依赖'
        print('  %s %-32s %-7s %s' % (mark, aid, ver, detail))

    print('')
    if not all_checks:
        die('一条都没比对成（取件全败或 fleet 族格与 starter 依赖无交集）——'
            '空断言不算绿，本结论不作数')
    for s in skipped:
        print('  ! %s' % s)
    policed = {c[2] for c in all_checks}
    uncovered = sorted(set(fam) - policed)
    print('对账 %d 条；fleet %d 格里被 starter 覆盖 %d 格，未覆盖 %d 格%s'
          % (len(all_checks), len(fam), len(policed), len(uncovered),
             '（%s）' % ', '.join(uncovered) if uncovered else ''))
    if all_viol:
        print('\n'.join('✗ %s' % v for v in all_viol))
        print('❌ %d 项不一致 / 共对账 %d 条' % (len(all_viol), len(all_checks)))
        sys.exit(1)
    if skipped:
        print('❌ 有 %d 件发布件取不到，判不了 ⇒ 不算绿' % len(skipped))
        sys.exit(1)
    print('✅ 全绿：%d 件 starter 的发布件内联兄弟版本 == fleet 当前格' % len(mods))
    sys.exit(0)


if __name__ == '__main__':
    main()
