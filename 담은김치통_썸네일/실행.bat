@echo off
chcp 65001 >nul
cd /d "%~dp0"
python make_dameun_thumbnails.py --root "D:\코워크\_누끼원본_추출"
pause
