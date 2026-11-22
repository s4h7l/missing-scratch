PYTHON ?= .venv/bin/python
build:
	$(PYTHON) -m scratch.build
test:
	$(PYTHON) -m unittest discover -s tests
serve: build
	$(PYTHON) -m http.server 8000 --bind 127.0.0.1 --directory dist

FREEZE_DIR ?= runs/frozen-200-v4
freeze-docker:
	mkdir -p runs
	test ! -e "$(FREEZE_DIR)"
	docker compose cp playground:/public "$(FREEZE_DIR)"
