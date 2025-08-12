PY=python
UV=uvicorn
APP=rag.app.main:app

install:
	$(PY) -m pip install -r backend/requirements.txt -r rag/requirements-rag.txt

ingest:
	$(PY) rag/ingest/run_ingest.py data/

run:
	$(UV) $(APP) --reload

dev: install ingest run
