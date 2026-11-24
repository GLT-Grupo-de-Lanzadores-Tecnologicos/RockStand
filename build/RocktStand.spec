# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\repos\\UTN-GLT\\RockStand\\src\\main.py'],
    pathex=['D:\\repos\\UTN-GLT\\RockStand\\src'],
    binaries=[],
    datas=[('D:\\repos\\UTN-GLT\\RockStand\\src\\ui\\main_window.ui', 'ui'), ('D:\\repos\\UTN-GLT\\RockStand\\src\\assets\\logo.png', 'assets'), ('D:\\repos\\UTN-GLT\\RockStand\\src\\translations\\rocktstand_es.qm', 'translations')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['IPython', 'matplotlib', 'PIL', 'pygments', 'pytest', 'scipy', 'setuptools', 'tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RocktStand',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:\\repos\\UTN-GLT\\RockStand\\src\\assets\\logo.ico'],
)
