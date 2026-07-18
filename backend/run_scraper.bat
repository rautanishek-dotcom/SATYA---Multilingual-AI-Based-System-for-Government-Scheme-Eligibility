@echo off
:: ============================================================
:: SATYA – Scheme Scraper Launcher
:: Schedule this file in Windows Task Scheduler (daily/weekly)
:: ============================================================

:: Change to the backend directory
cd /d "d:\MAJOR PROJECT(SATYA) (Final) (curr)\backend"

:: Activate virtual environment (adjust path if yours differs)
call "..\venv\Scripts\activate.bat"

:: Run the scraper
python scheme_scraper.py

:: Deactivate venv
deactivate

echo Scraper run completed at %DATE% %TIME%
