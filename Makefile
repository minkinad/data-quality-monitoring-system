PYTHON ?= python3

.PHONY: install infra pipeline dashboard test clean

install:
	$(PYTHON) -m pip install -e ".[dev]"

infra:
	docker compose up -d postgres grafana

pipeline:
	$(PYTHON) scripts/run_pipeline.py --days 30 --reset

dashboard:
	streamlit run app/dashboard.py

test:
	$(PYTHON) -m pytest -q

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
