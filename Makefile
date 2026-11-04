.PHONY: run test web

ifeq ($(OS),Windows_NT)
PYTHON := .venv/Scripts/python.exe
else
PYTHON := .venv/bin/python
endif

run:
	$(PYTHON) -m uvicorn --app-dir backend app.main:app --reload

test:
	$(PYTHON) -m pytest backend/tests

web:
	npm --prefix web run dev
