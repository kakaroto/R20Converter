import sys
from cx_Freeze import setup, Executable

sys.path.append("src")
# Dependencies are automatically detected, but it might need
# fine tuning.
buildOptions = dict(packages = [])

base = 'Console'

executables = [
    Executable('src/main.py', base=base, targetName = 'R20Converter')
]

setup(name='R20Converter',
      version = '0.9-rc1',
      description = 'Convert a Roll 20 Campaign into a Foundry VTT world',
      options = dict(build_exe = buildOptions),
      executables = executables,
      data_files = [ "templates", "client/dist"]
      )
