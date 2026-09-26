# moto-vehicle-defs: generate code from the definitions and check them.
# Needs uv (https://docs.astral.sh/uv/). `gen/` output is committed (D-003).

UV      ?= uv
CODEGEN := $(UV) run --locked --project tools/codegen

.PHONY: all gen check parse lint test drift clean

all: check

## gen: regenerate gen/ (C per node, Python constants, VSS JSON)
gen:
	$(CODEGEN) moto-codegen gen

## check: strict DBC parse + consistency checks + lint + tests
check: parse lint test

parse:
	$(CODEGEN) python -c "import cantools; [cantools.database.load_file(f, strict=True) for f in ('dbc/platform.dbc', 'dbc/cl250.dbc')]; print('strict parse: OK')"
	$(CODEGEN) moto-codegen check

lint:
	$(CODEGEN) ruff check tools/codegen
	$(CODEGEN) ruff format --check tools/codegen

test:
	$(CODEGEN) pytest -q tools/codegen/tests

## drift: fail if gen/ differs from a fresh generation (what CI runs)
drift: gen
	@if [ -n "$$(git status --porcelain -- gen)" ]; then \
		git status --short -- gen; \
		echo "gen/ is out of date: run 'make gen' and commit"; exit 1; \
	fi; echo "drift: gen/ up to date"

clean:
	rm -rf tools/codegen/.cache tools/codegen/.pytest_cache tools/codegen/.ruff_cache
