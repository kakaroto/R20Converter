#!/bin/bash
set -e

if [[ ! -d Electron.app ]] ; then
    echo "Make sure you install and copy (cp -R) the Electron.app directory here"
    exit 255
fi

rm -rf build
# (cd client && npm run build)

python3 setup.py bdist_mac
cp -R Electron.app build/R20Converter-*.app/Contents/Resources/
codesign --remove-signature build/R20Converter-*.app/Content/MacOS/Python
python3 setup.py bdist_dmg
