.PHONY: setup fmt lint typecheck test gate doctor lab-up lab-down test-int

PYTHON ?= python

setup:
	$(PYTHON) -m pip install -e ".[dev]"

fmt:
	ruff format .
	ruff check --fix .

lint:
	ruff check .

typecheck:
	mypy src/venice_pt

test:
	pytest tests/unit

gate: lint typecheck test
	@echo "All gate checks passed successfully."

doctor:
	$(PYTHON) -m venice_pt.cli doctor

lab-up:
	docker compose -f lab/docker-compose.yml up -d

lab-down:
	docker compose -f lab/docker-compose.yml down

test-int:
	pytest tests/integration
