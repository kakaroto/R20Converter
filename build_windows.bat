set /p version_py=<src\version.py
set version=%version_py:~11,-1%
rd /s /q dist
rd /s /q windows
rd /s /q "releases\R20Converter-%version%"

"C:\Users\kakaroto\AppData\Local\Programs\Python\Python38-32\Scripts\pyinstaller.exe" R20Converter.spec

mkdir "releases\R20Converter-%version%"
xcopy /s src "releases\R20Converter-%version%\src\"
xcopy /s templates "releases\R20Converter-%version%\templates\"
copy Changelog.md "releases\R20Converter-%version%\"
copy README.md "releases\R20Converter-%version%\"
copy README.html "releases\R20Converter-%version%\"
rd /s /q "releases\R20Converter-%version%\src\__pycache__"
rd /s /q "releases\R20Converter-%version%\src\entities\__pycache__"
move dist\R20Converter "releases\R20Converter-%version%\windows"
rd /s /q dist


"C:\Users\kakaroto\AppData\Local\Programs\Python\Python38-32\python.exe" setup.py build

mkdir "releases\R20Converter-%version%-cx"
xcopy /s src "releases\R20Converter-%version%-cx\src\"
xcopy /s templates "releases\R20Converter-%version%-cx\templates\"
copy Changelog.md "releases\R20Converter-%version%-cx\"
copy README.md "releases\R20Converter-%version%-cx\"
copy README.html "releases\R20Converter-%version%-cx\"
rd /s /q "releases\R20Converter-%version%-cx\src\__pycache__"
rd /s /q "releases\R20Converter-%version%-cx\src\entities\__pycache__"
move "build\exe.win32-3.8" "releases\R20Converter-%version%-cx\windows"
xcopy /s templates "releases\R20Converter-%version%-cx\windows\templates\"
pause
