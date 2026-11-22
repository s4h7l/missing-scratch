PYTHON ?= .venv/bin/python
build:
	$(PYTHON) -m scratch.build
test:
	$(PYTHON) -m unittest discover -s tests
serve: build
	$(PYTHON) -m http.server 8000 --bind 127.0.0.1 --directory dist

freeze-docker:
	mkdir -p runs
	test ! -e runs/frozen
	docker compose cp playground:/public runs/frozen
