set /p version_py=<src\version.py
set version=%version_py:~11,-1%
rd /s /q dist
rd /s /q windows
rd /s /q build
rd /s /q "releases\R20Converter-%version%-linux"
rd /s /q "releases\R20Converter-%version%-win32"
rd /s /q "releases\R20Converter-%version%-win64"

start /d client npm run build
pause

rd /s /q "src\__pycache__"
rd /s /q "src\*.pyc"
rd /s /q "src\entities\__pycache__"
rd /s /q "src\entities\*.pyc"
rd /s /q "src\entities\rolltemplates\__pycache__"
rd /s /q "src\entities\rolltemplates\*.pyc"

mkdir "releases\R20Converter-%version%-linux"
mkdir "releases\R20Converter-%version%-linux\client"
copy Changelog.md "releases\R20Converter-%version%-linux\"
copy README.md "releases\R20Converter-%version%-linux\"
copy README.html "releases\R20Converter-%version%-linux\"
copy Advanced.md "releases\R20Converter-%version%-linux\"
copy setup.py "releases\R20Converter-%version%-linux\"
xcopy /s src "releases\R20Converter-%version%-linux\src\"
xcopy /s templates "releases\R20Converter-%version%-linux\templates\"
copy client\*.* "releases\R20Converter-%version%-linux\client\"
xcopy /s client\dist "releases\R20Converter-%version%-linux\client\dist\"
xcopy /s client\public "releases\R20Converter-%version%-linux\client\public\"
xcopy /s client\src "releases\R20Converter-%version%-linux\client\src\"

rem "C:\Users\kakaroto\AppData\Local\Programs\Python\Python38-32\python.exe" setup.py build
rem timeout 1
rem move "build\exe.win32-3.8" "releases\R20Converter-%version%-win32"

"C:\Users\kakaroto\AppData\Local\Programs\Python\Python38\python.exe" setup.py build

rem sometimes it throws access denien, so we need to wait a second before move the folder
timeout 1
move "build\exe.win-amd64-3.8" "releases\R20Converter-%version%-win64"

pause
