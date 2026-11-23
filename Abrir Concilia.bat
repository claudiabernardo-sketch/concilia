@echo off
title Concilia
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
  python abrir_concilia.py
) else (
  py abrir_concilia.py
)
if errorlevel 1 (
  echo.
  echo Nao consegui abrir o Concilia. Peca ao Claude ou ao ChatGPT: "Instale o Concilia nesta pasta".
  pause
)
