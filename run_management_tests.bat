@echo off
REM Activate virtual environment and run management dialog tests
call onetask_env\Scripts\activate.bat
python -m pytest tests\ui\test_management_dialogs.py -v --tb=short
