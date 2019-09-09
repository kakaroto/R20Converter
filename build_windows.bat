rd /s /q dist
rd /s /q windows
"C:\Users\kakaroto\AppData\Local\Programs\Python\Python37-32\Scripts\pyinstaller.exe" R20Converter.spec
move dist\R20Converter windows
rd /s /q dist
pause