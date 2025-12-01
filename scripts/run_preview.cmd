@echo off
REM Run preview mode on Windows (camera will stub if unavailable)
set PYTHONPATH=.
python -m src.connectvision.app --config configs\default.yaml --preview
