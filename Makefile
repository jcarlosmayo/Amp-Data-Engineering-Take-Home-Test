.PHONY: lint format test

lint:
	ruff check .

format:
	ruff format .

test:
	API_KEY=test-key pytest -v
