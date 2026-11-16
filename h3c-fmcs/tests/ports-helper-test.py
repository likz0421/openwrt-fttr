#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Run the installed helper with isolated /run, fake UCI and kmodloader."""
from pathlib import Path
import os
import subprocess
import tempfile
import textwrap

HELPER = Path(__file__).resolve().parents[1] / 'files/fttr-ports'
FAKE_UCI = '''#!/usr/bin/python3
import json, pathlib, sys
args=sys.argv[1:]
p=pathlib.Path(args[args.index('-c')+1])/'fttr'
d=json.loads(p.read_text())
if d.get('error'): sys.exit(1)
if 'show' in args:
    print(d.get('show', 'fttr.ports=ports'))
else:
    key=args[-1].rsplit('.',1)[-1]
    if key not in d or key in d.get('get_error', []): sys.exit(1)
    print(d[key])
'''
FAKE_KMOD = '''#!/bin/sh
[ "$#" = 1 ] || exit 8
case "$1" in */modules/) ;; *) exit 9 ;; esac
cat "$1/19-h3c-fmcs" >> "$FTTR_PORTS_ROOT/calls"
[ ! -f "$FTTR_PORTS_ROOT/fail" ] || exit 1
[ ! -f "$FTTR_PORTS_ROOT/no-load" ] || exit 0
mkdir -p "$FTTR_PORTS_ROOT/sys/module/h3c_fmcs/parameters"
IFS= read -r line < "$1/19-h3c-fmcs"
printf '%s\\n' "${line##*=}" > "$FTTR_PORTS_ROOT/sys/module/h3c_fmcs/parameters/port_count"
'''
import json

def run_case(name, config=None, expect=16, loaded=None, action='load', bad=False, mode=None):
    with tempfile.TemporaryDirectory(prefix='fmcs-ports-test-') as d:
        r=Path(d)
        for sub in ['sbin', 'etc/config', 'run', 'sys/module']:
            (r/sub).mkdir(parents=True, exist_ok=True)
        for tool, source in [('uci', FAKE_UCI), ('kmodloader', FAKE_KMOD)]:
            (r/'sbin'/tool).write_text(source)
            (r/'sbin'/tool).chmod(0o755)
        if config is not None:
            (r/'etc/config/fttr').write_text(json.dumps(config))
        p=r/'sys/module/h3c_fmcs/parameters/port_count'
        if loaded is not None:
            p.parent.mkdir(parents=True)
            p.write_text(str(loaded)+'\n')
        if mode:
            (r/mode).touch()
        env=dict(os.environ, FTTR_PORTS_ROOT=d)
        res=subprocess.run(['sh', str(HELPER), action], env=env, capture_output=True, text=True)
        assert (res.returncode != 0) == bad, (name, res.stdout, res.stderr)
        calls=(r/'calls').read_text() if (r/'calls').exists() else ''
        if bad and not mode:
            assert calls == '', (name, calls)
            assert not (r/'run/fttr-ports/modules/19-h3c-fmcs').exists(), name
        elif not bad:
            want=f'h3c-fmcs port_count={expect}\n'
            assert (r/'run/fttr-ports/modules/19-h3c-fmcs').read_text()==want, name
            assert calls == (want if action=='load' and loaded is None else ''), (name, calls)
            if loaded is not None:
                assert p.read_text().strip()==str(loaded), name
                assert f'pending={int(loaded != expect)}' in res.stdout, res.stdout
        print('PASS', name)

for n in [1,4,16]:
    run_case(f'count-{n}', {'count':str(n)}, expect=n)
run_case('disabled-count-4', {'enabled':'0','count':'4'}, expect=0)
run_case('disabled-default-count', {'enabled':'false'}, expect=0)
run_case('leading-zero-decimal', {'count':'0004'}, expect=4)
run_case('legacy-no-file')
run_case('legacy-no-section', {'show':'fttr.optical=optical'})
run_case('missing-options-defaults', {})
run_case('prepare-no-load', {'count':'4'}, expect=4, action='prepare')
run_case('live-change-pending', {'count':'4'}, expect=4, loaded=16)
run_case('live-same', {'count':'4'}, expect=4, loaded=4)
run_case('live-disabled', {'enabled':'off','count':'4'}, expect=0, loaded=4)
for value in ['0','17','-1','x','4 5','0x04','4;touch /tmp/never','9999999999999999']:
    run_case('invalid-count-'+value, {'count':value}, bad=True)
run_case('invalid-disabled-count', {'enabled':'0','count':'0'}, bad=True)
run_case('invalid-enabled', {'enabled':'maybe'}, bad=True)
run_case('uci-parse-failure', {'error':True}, bad=True)
run_case('wrong-section-type', {'show':'fttr.ports=optical'}, bad=True)
run_case('anonymous-section', {'show':'fttr.@ports[0]=ports'}, bad=True)
run_case('extra-ports-section', {'show':'fttr.ports=ports\nfttr.other=ports'}, bad=True)
run_case('unknown-option', {'show':"fttr.ports=ports\nfttr.ports.typo='1'"}, bad=True)
run_case('kmodloader-failure', {'count':'4'}, bad=True, mode='fail')
run_case('kmodloader-false-success', {'count':'4'}, bad=True, mode='no-load')
print('helper tests passed')
