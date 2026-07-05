@echo off
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PY=python"
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY=py"
    ) else (
        echo Python est introuvable sur cette machine.
        echo Installez-le depuis https://www.python.org/downloads/ ^(cochez "Add python.exe to PATH"^) puis relancez ce fichier.
        pause
        exit /b 1
    )
)

%PY% -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo Installation globale des dependances echouee, nouvel essai en mode utilisateur...
    %PY% -m pip install -q --user -r requirements.txt
    if errorlevel 1 (
        echo Impossible d'installer les dependances Python. Verifiez la connexion internet.
        pause
        exit /b 1
    )
)

%PY% fusionner.py
pause
