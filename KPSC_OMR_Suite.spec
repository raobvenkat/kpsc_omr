# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.hooks import collect_all

datas = [('core\\mnist-8.onnx', 'core'), ('sql', 'sql'), ('KPSC_DB_Script_14072026.sql', '.'), ('OMR', 'OMR'), ('OMR_1', 'OMR_1'), ('OMRs2', 'OMRs2'), ('Attendance Sheet1', 'Attendance Sheet1'), ('Attendance Sheet2', 'Attendance Sheet2')]
binaries = []
hiddenimports = ['CounterFoilScanning', 'CounterFoilSubBSNoEdit', 'CounterFoilDataEdit', 'NominalRolls', 'NominalRoll1DataEdit', 'NominalRoll2DataEdit', 'OMRInkDetection', 'DiscrepancyReports', 'AllDiscrepancyGeneration', 'CopyDiscrepancySheets', 'core.omr', 'core.omr_bw', 'core.omr_color', 'core.nominal_roll', 'core.nominal_roll_type1', 'core.nominal_roll_type2']
binaries += collect_dynamic_libs('onnxruntime')
binaries += collect_dynamic_libs('pyzbar')
tmp_ret = collect_all('easyocr')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('tkcalendar')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('babel')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KPSC_OMR_Suite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KPSC_OMR_Suite',
)
