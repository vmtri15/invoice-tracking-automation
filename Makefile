setup:
	python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt

run:
	.venv/bin/python -m src.run_pipeline

test:
	.venv/bin/python -m pytest -q

sample:
	.venv/bin/python -m src.generate_sample_data
