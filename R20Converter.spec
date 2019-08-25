# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['src\\R20Converter.py'],
             pathex=['v:\\Projects\\FVTT\\R20Converter'],
             binaries=[],
             datas=[('fonts', 'fonts')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

def remove_from_list(binaries, keys):
    outlist = []
    for item in binaries:
        name, _, _ = item
        remove = False
        for key_word in keys:
            if key_word in name:
                remove = True
                break
        if not remove:
            outlist.append(item)
    return outlist

a.binaries = remove_from_list(a.binaries, ['mkl','libopenblas'])

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='R20Converter',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='R20Converter')
