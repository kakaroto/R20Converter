set /p version_py=<src\version.py
set version=%version_py:~11,-1%
rd /s /q dist
rd /s /q windows
rd /s /q build
rd /s /q "releases\R20Converter-%version%"
rd /s /q "releases\R20Converter-%version%-windows"

start /d client npm run build
pause

rd /s /q "releases\R20Converter-%version%-cx\src\__pycache__"
rd /s /q "releases\R20Converter-%version%-cx\src\entities\__pycache__"

mkdir "releases\R20Converter-%version%"
mkdir "releases\R20Converter-%version%\client"
mkdir "releases\R20Converter-%version%\client\dist"
copy Changelog.md "releases\R20Converter-%version%\"
copy README.md "releases\R20Converter-%version%\"
copy README.html "releases\R20Converter-%version%\"
xcopy /s src "releases\R20Converter-%version%\src\"
xcopy /s templates "releases\R20Converter-%version%\templates\"
xcopy /s client\dist "releases\R20Converter-%version%\client\dist\"

"C:\Users\kakaroto\AppData\Local\Programs\Python\Python38-32\python.exe" setup.py build

move "build\exe.win32-3.8" "releases\R20Converter-%version%-windows"
pause
