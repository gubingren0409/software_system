"""Narrow offline checks for this report release; no experimental runner imports."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import textwrap
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
BASE = '0050066fd748c0fa5c06475eaa3b8a12e5e07ece'
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists(): raise ValueError('New acceptance output required')
data = json.loads((Path(__file__).parent/'derived-release/summary.json').read_text(encoding='utf-8'))
report = (ROOT/'report.md').read_text(encoding='utf-8')
checks = {}


def require(name, condition):
    checks[name] = bool(condition)
    if not condition: raise AssertionError(name)


def table(section, start, end):
    body = report.split(section, 1)[1].split(end, 1)[0]
    return [[cell.strip() for cell in line.strip().strip('|').split('|')]
            for line in body.splitlines() if line.startswith(start)]


def same(actual, expected, digits=9):
    return f'{float(actual):.{digits}f}' == f'{float(expected):.{digits}f}'


require('seven_sections', re.findall(r'^## (\d)\.', report, re.M) == list('1234567'))
for path in ('scripts/report_offline.py','evidence/report_release/20261021/check_report.py',
             'evidence/report_release/20261021/record_operation.py'):
    ast.parse((ROOT/path).read_text(encoding='utf-8'))
    require('python_syntax_'+path,True)
require('derived_script_identity',data['script_sha256']==hashlib.sha256((ROOT/'scripts/report_offline.py').read_bytes()).hexdigest())
configurations=json.loads((Path(__file__).parent/'operations/wsl_list_configs.stdout.txt').read_text(encoding='utf-8'))
require('actual_cli_20_unique',len(configurations)==len({json.dumps(c,sort_keys=True) for c in configurations})==20)
grid_rows = table('### 4.1', '| O', '### 4.2')
require('all_20_grid_cells', len(grid_rows) == 4 and all(len(row) == 6 for row in grid_rows))
for i, row in enumerate(grid_rows):
    for j, cell in enumerate(row[1:]):
        require(f'grid_{i}_{j}', same(cell.rstrip('*'), data['grid'][i*5+j]['median']))
trace_rows = table('## 5.', '| ', '## 6.')[1:]
require('trace_rows_12', len(trace_rows) == 12)
for i,row in enumerate(trace_rows):
    for a,offset in (('random',1),('greedy',3)):
        expected=data['trajectories'][a][i]
        require(f'trace_{a}_{i}', row[offset] == expected['config'] and same(row[offset+1],expected['median']))
validation_rows = table('### 4.3', '| O3/', '## 5.')
require('validation_rows_3',len(validation_rows)==3)
for row,g in zip(validation_rows,data['validation']):
    require('validation_'+g['config'], row[0]==g['config'] and same(row[2],g['median'])
            and same(row[4].rstrip('%'),g['cv_percent'],4) and same(row[5],g['mad']))
prefix_rows=table('### 6.2', '| Random', '### 6.3') + table('### 6.2', '| Greedy', '### 6.3')
require('six_prefix_rows',len(prefix_rows)==6)
for row,g in zip(prefix_rows,data['prefixes']):
    own_cv, ret_cv = row[5].split('/')
    own_mad, ret_mad = row[6].split('/')
    require(f'prefix_{g["algorithm"]}_{g["budget"]}',row[0].lower()==g['algorithm']
        and row[1]==f'{g["budget"]}/{g["budget"]}' and row[2]==g['selected_config']
        and same(row[3],g['search_median']) and same(row[4],g['independent_median'])
        and same(own_cv,g['search_cv_percent'],4) and same(ret_cv,g['independent_cv_percent'],4)
        and same(own_mad,g['search_mad']) and same(ret_mad,g['independent_mad'])
        and same(row[7],g['configuration_evaluation_raw_seconds']))
main_rows=table('### 6.1', '| Grid', '### 6.2')+table('### 6.1', '| Random，', '### 6.2')+table('### 6.1', '| Greedy，', '### 6.2')
require('comparison_rows_3',len(main_rows)==3)
for row,algorithm in zip(main_rows,('grid','random','greedy')):
    cost=data['costs']['grid'] if algorithm=='grid' else data['costs']['search'][algorithm]
    require('main_cost_'+algorithm,same(row[-1],cost))
for key in ('random','greedy'):
    require('retest_cost_'+key, f'{data["costs"]["retest"][key]:.9f}' in report)
require('activity_cost',f'{data["costs"]["activity_qpc_seconds"]:.7f}' in report)
reduction=100*(1-data['costs']['search']['greedy']/data['costs']['search']['random'])
require('37_32_is_local_not_end_to_end',f'{reduction:.2f}%' in report and '不等于端到端提速37.32%' in report)
grid_lookup={g['config']:g['median'] for g in data['grid']}
for value in (100*(grid_lookup['O2/s8']/grid_lookup['O1/s8']-1),
              100*(grid_lookup['O2/s128']/grid_lookup['O1/s128']-1),
              100*(1-grid_lookup['O1/s128']/grid_lookup['O1/s8']),
              100*(1-grid_lookup['O3/s128']/grid_lookup['O3/s8']),
              100*(grid_lookup['O2/s128']/grid_lookup['O2/s64']-1),
              100*(1-grid_lookup['O3/s128']/grid_lookup['O3/s64'])):
    require('percentage_'+f'{value:.2f}',f'{value:.2f}%' in report)
require('no_measurement_clipped_in_variation',all(abs(100*(v/g['median']-1))<6 for g in data['grid'] for v in g['values']))

# Match excerpts to source, ignoring indentation/whitespace, not semantics.
normalize=lambda s: re.sub(r'\s+',' ',s).strip()
sources='\n'.join((ROOT/p).read_text(encoding='utf-8') for p in
    ('autotuner/core.py','autotuner/raw_comparison.py','autotuner/measurement.py','code/working/matrix_multiplication.c'))
for i,(language,body) in enumerate(re.findall(r'```(python|c)\n(.*?)\n```',report,re.S)):
    require(f'code_excerpt_{i}',normalize(textwrap.dedent(body)) in normalize(sources))

documents=('report.md','README.md','docs/REPORT_ACCEPTANCE.md','docs/AUDIT_HANDOFF.md',
           'docs/P3_RAW_GRID.md','evidence/report_release/20261021/README.md')
links=[]
for name in documents:
    text=(ROOT/name).read_text(encoding='utf-8')
    require('balanced_fences_'+name,text.count('```')%2==0)
    for address in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
        address=address.strip('<>')
        parsed=urlsplit(address)
        if parsed.scheme: continue
        path=(ROOT/name).parent/unquote(parsed.path)
        require('link_'+name+'_'+address,path.exists())
        if parsed.fragment:
            contents=path.read_text(encoding='utf-8')
            headings=re.findall(r'^#{1,6} (.+)$',contents,re.M)
            slugs={re.sub(r'[^\w\- ]','',h.lower()).replace(' ','-') for h in headings}
            require('anchor_'+address,unquote(parsed.fragment) in slugs)
        links.append({'document':name,'target':address})
for name,expected in data['input_sha256'].items():
    require('input_bytes_'+name,hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected)
expected_original='188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15'
require('teacher_original_exact',hashlib.sha256((ROOT/'code/original/matrix_multiplication.c').read_bytes()).hexdigest()==expected_original)
if (ROOT.parent/'P1/matrix_multiplication.c').is_file():
    require('local_attachment_exact',hashlib.sha256((ROOT.parent/'P1/matrix_multiplication.c').read_bytes()).hexdigest()==expected_original)
pdf=ROOT.parent/'P1/P1 Matrix Multiplication Autotuner.pdf'
require('teacher_pdf_identity',hashlib.sha256(pdf.read_bytes()).hexdigest()=='ffe21db96ab0af28ff2f329f6d0a03b61fac577e530e8649c375ce13bf74eafe')
allowed={'report.md','README.md','scripts/report_offline.py','docs/REPORT_ACCEPTANCE.md',
         'docs/AUDIT_HANDOFF.md','docs/P3_RAW_GRID.md','docs/P3_AUDIT_HANDOFF.md','docs/WORK_LOG.md'}
changed=subprocess.check_output(['git','diff','--name-only',BASE,'--'],cwd=ROOT,text=True).splitlines()
require('scoped_tracked_changes',all(p in allowed or p.startswith(('evidence/report_release/','images/report_raw_20261021_final/')) for p in changed))
baseline_bytes=subprocess.check_output(['git','show',BASE+':report.md'],cwd=ROOT)
require('report_shorter',len(report.encode('utf-8'))<len(baseline_bytes)/2)
require('single_seed_limits','五种子整体完成与比较状态仍为false' in report and '合盖Modern Standby' in report)
result=dict(all_pass=True,checks=checks,links=links,changed_tracked_files=changed,
    report_bytes=len(report.encode('utf-8')),baseline_report_bytes=len(baseline_bytes),
    input_files_unchanged=len(data['input_sha256']),new_performance_executions=0,
    scope='Report/derived checks, not a replacement historical experimental audit')
args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('checks','links')},ensure_ascii=False))
