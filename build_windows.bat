set /p version_py=<src\version.py
set version=%version_py:~11,-1%
rd /s /q dist
rd /s /q windows
rd /s /q "releases\R20Converter-%version%"
rd /s /q "releases\R20Converter-%version%-cx"

rem "C:\Users\kakaroto\AppData\Local\Programs\Python\Python38-32\Scripts\pyinstaller.exe" R20Converter.spec

rem mkdir "releases\R20Converter-%version%"
rem xcopy /s src "releases\R20Converter-%version%\src\"
rem xcopy /s templates "releases\R20Converter-%version%\templates\"
rem copy Changelog.md "releases\R20Converter-%version%\"
rem copy README.md "releases\R20Converter-%version%\"
rem copy README.html "releases\R20Converter-%version%\"
rem rd /s /q "releases\R20Converter-%version%\src\__pycache__"
rem rd /s /q "releases\R20Converter-%version%\src\entities\__pycache__"
rem move dist\R20Converter "releases\R20Converter-%version%\windows"
rem rd /s /q dist


start /d client npm run build
pause

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
mkdir "releases\R20Converter-%version%-cx\client"
mkdir "releases\R20Converter-%version%-cx\client\dist"
mkdir "releases\R20Converter-%version%-cx\windows\client"
mkdir "releases\R20Converter-%version%-cx\windows\client\dist"
xcopy /s client\dist "releases\R20Converter-%version%-cx\client\dist\"
xcopy /s client\dist "releases\R20Converter-%version%-cx\windows\client\dist"
pause
