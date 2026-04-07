@echo off
cd /d "%~dp0eldaana"
echo Démarrage d'Eldaana...
python -m streamlit run app.py
pause
