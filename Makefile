.PHONY: all generate build test quality clean install

PYTHON := python3
GENERATOR := $(PYTHON) -m bakec.cli

all: generate build test quality

install:
	pip install -e ".[dev]"

generate:
	$(GENERATOR) generate --model models/lung_mnarx.yaml \
		--platform platforms/desktop.yaml \
		--output generated/desktop/
	$(GENERATOR) generate --model models/lung_mnarx.yaml \
		--platform platforms/cortex_m4.yaml \
		--output generated/cortex_m4/
	$(GENERATOR) generate --model models/pid_controller.yaml \
		--platform platforms/desktop.yaml \
		--output generated/desktop/

build:
	cmake -B build/out -S build -DPLATFORM=desktop
	cmake --build build/out

test: test-python test-c

test-python:
	$(PYTHON) -m pytest tests/ -v --tb=short

test-c:
	@if [ -d "build/out" ]; then ctest --test-dir build/out --output-on-failure; fi

quality:
	$(PYTHON) quality/check_generated.py generated/

clean:
	rm -rf build/out generated/desktop generated/cortex_m4 __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
