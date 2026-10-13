@echo off
REM ============================================================
REM  Kakuzu - Jiongu : compile les 4 modeles pour Garry's Mod
REM  Double-clique ce fichier. Si Garry's Mod n'est pas dans le
REM  dossier Steam par defaut, corrige la ligne GMOD ci-dessous.
REM ============================================================
setlocal
set "GMOD=C:\Program Files (x86)\Steam\steamapps\common\GarrysMod"
set "STUDIOMDL=%GMOD%\bin\studiomdl.exe"
set "HERE=%~dp0"

if not exist "%STUDIOMDL%" (
  echo [ERREUR] studiomdl.exe introuvable : "%STUDIOMDL%"
  echo Ouvre ce fichier avec le Bloc-notes et corrige la ligne "set GMOD=..."
  pause
  exit /b 1
)

for %%M in (katon futon raiton suiton) do (
  echo.
  echo ===== Compilation de jiongu_%%M =====
  "%STUDIOMDL%" -game "%GMOD%\garrysmod" -nop4 -nox360 "%HERE%modelsrc\jiongu_%%M\jiongu_%%M.qc"
  if errorlevel 1 (
    echo [ERREUR] La compilation de jiongu_%%M a echoue. Lis les messages ci-dessus.
    pause
    exit /b 1
  )
)

echo.
echo ===== Copie des modeles dans l'addon =====
if not exist "%HERE%addon\kakuzu_jiongu\models\kakuzu_jiongu" mkdir "%HERE%addon\kakuzu_jiongu\models\kakuzu_jiongu"
copy /Y "%GMOD%\garrysmod\models\kakuzu_jiongu\*.*" "%HERE%addon\kakuzu_jiongu\models\kakuzu_jiongu\" >nul
del /Q "%GMOD%\garrysmod\models\kakuzu_jiongu\*.*"
rmdir "%GMOD%\garrysmod\models\kakuzu_jiongu"

echo.
echo Termine ! Copie maintenant le dossier addon\kakuzu_jiongu dans :
echo   "%GMOD%\garrysmod\addons\"
echo (et dans garrysmod\addons de ton serveur).
pause
