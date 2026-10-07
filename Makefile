test:
	python -m pytest shop/test_shop.py -v
bench:
	python benchmarks/bench.py
demo:
	python scripts/demo.py
live:
	python experiments/verify_live.py
up:
	docker compose up --build
