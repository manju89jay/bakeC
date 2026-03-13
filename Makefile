.PHONY: all generate build test validate clean install

PYTHON := python3
GENERATOR := $(PYTHON) -m bakec.cli

all: generate build test validate

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
	$(GENERATOR) generate --model models/pid_controller.yaml \
		--platform platforms/cortex_m4.yaml \
		--output generated/cortex_m4/
	$(GENERATOR) generate --model models/lung_mnarx.yaml \
		--platform platforms/aurix_tc397.yaml \
		--output generated/aurix_tc397/
	$(GENERATOR) generate --model models/pid_controller.yaml \
		--platform platforms/aurix_tc397.yaml \
		--output generated/aurix_tc397/

build:
	cmake -B build/out -S build -DPLATFORM=desktop
	cmake --build build/out

test: test-python test-c

test-python:
	$(PYTHON) -m pytest tests/ -v --tb=short --cov=bakec --cov-report=term-missing

test-c:
	@if [ -d "build/out" ]; then ctest --test-dir build/out --output-on-failure; fi

validate:
	$(GENERATOR) validate --target generated/desktop/ --rules src/bakec/checks/rules.yaml --platforms-dir platforms/
	$(GENERATOR) validate --target generated/cortex_m4/ --rules src/bakec/checks/rules.yaml --platforms-dir platforms/
	$(GENERATOR) validate --target generated/aurix_tc397/ --rules src/bakec/checks/rules.yaml --platforms-dir platforms/

clean:
	rm -rf build/out generated/desktop generated/cortex_m4 generated/aurix_tc397 __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
