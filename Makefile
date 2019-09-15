format:
	poetry run black -v --skip-string-normalization .

lint:
	poetry run mypy pytracing/pytracing.py test_pytracing.py

test_pytracing:
	poetry run python test_pytracing.py