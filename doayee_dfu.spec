# -*- mode: python -*-

block_cipher = None


a = Analysis(['doayee_dfu.py'],
             pathex=['/Users/Tom/Documents/GitRepos/Doayee-dev/esp32bta/dfu'],
             binaries=[],
             datas=[],
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
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='DoayeeESP32DFU',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False , icon='logo.ico')
app = BUNDLE(exe,
             name='DoayeeESP32DFU.app',
             icon='logo.png.icns',
             bundle_identifier='com.doayee.esp32dfu',
             info_plist={
            'NSHighResolutionCapable': 'True'
            },)
