import ast, re

src = open('DiscrepancyReports.py', encoding='utf-8-sig').read()

# 1. Syntax
ast.parse(src)
print('SYNTAX: OK')

# 2. Report IDs
ids = [int(x) for x in re.findall(r'"id": (\d+)', src)]
print(f'Report IDs: {ids}')
print(f'All 11 present (1-11): {sorted(ids) == list(range(1,12))}')

# 3. edit_fields non-empty
ef_blocks = re.findall(r'"edit_fields": \[(.*?)\]', src, re.DOTALL)
print(f'edit_fields blocks: {len(ef_blocks)}')
empty_ef = [ids[i] for i, b in enumerate(ef_blocks) if not b.strip()]
print(f'Empty edit_fields: {empty_ef} (expected: [])')

# 4. cols non-empty
cols_blocks = re.findall(r'"cols": \[(.*?)\]', src, re.DOTALL)
print(f'cols blocks: {len(cols_blocks)}')
empty_cols = [ids[i] for i, b in enumerate(cols_blocks) if not b.strip()]
print(f'Empty cols: {empty_cols} (expected: [])')

# 5. crops checks
crops_blocks = re.findall(r'"crops": \{(.*?)\}', src, re.DOTALL)
print(f'crops blocks: {len(crops_blocks)}')
empty_crops = [ids[i] for i, b in enumerate(crops_blocks) if not b.strip()]
print(f'Empty crops at report IDs: {empty_crops} (expected: [9, 10, 11])')

# 6. _dispatch_update branches
branches = re.findall(r'report\["id"\]\s*(?:==|in)\s*[\(\d,\s\)]+', src)
print(f'\n_dispatch_update branches found:')
for b in branches:
    print(f'  {b.strip()}')

# 7. DiscrepancyReports class methods
methods = re.findall(r'def (_build_ui|_select_report|_load_report|_refresh_current|_on_row_selected|_on_save|_on_reset)\b', src)
print(f'\nDiscrepancyReports methods found: {sorted(set(methods))}')
required = {'_build_ui','_select_report','_load_report','_refresh_current','_on_row_selected','_on_save','_on_reset'}
missing = required - set(methods)
print(f'Missing methods: {missing} (expected: set())')
