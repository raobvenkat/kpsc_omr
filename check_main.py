import ast, re

src = open('main.py', encoding='utf-8-sig').read()

# Syntax
ast.parse(src)
print('main.py SYNTAX: OK')

# self.reports_btn defined
has_reports_btn = 'self.reports_btn' in src
print(f'self.reports_btn defined: {has_reports_btn}')

# _open_reports method defined
has_open_reports = bool(re.search(r'def _open_reports\b', src))
print(f'_open_reports method: {has_open_reports}')

# from DiscrepancyReports import DiscrepancyReports inside _open_reports
# Find the method body
m = re.search(r'def _open_reports\b.*?(?=\n    def |\Z)', src, re.DOTALL)
if m:
    body = m.group()
    has_import = 'from DiscrepancyReports import DiscrepancyReports' in body
    print(f'  import inside _open_reports: {has_import}')
    print(f'  _open_reports body snippet:')
    print('  ' + '\n  '.join(body.strip().splitlines()[:12]))
else:
    print('_open_reports: NOT FOUND')
