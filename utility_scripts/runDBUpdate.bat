:: ###############################################################
:: ############# BATCH SCRIPT FOR JOB RUNNER #####################
:: ###############################################################

:: FIND DBUPDATESCRIPT.PY
cd "%~dp0..\src"

:: RUN SCRIPT
python DBUpdateScript.py %*
PAUSE