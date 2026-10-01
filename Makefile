# moto-vehicle-defs: generate code from the definitions and check them.
# Needs uv (https://docs.astral.sh/uv/). `gen/` output is committed (D-003).
# `make misra` also needs cppcheck with its MISRA addon.

UV       ?= uv
CODEGEN  := $(UV) run --locked --project tools/codegen
CPPCHECK ?= cppcheck
# gen/c runs on 32-bit MCUs (H7, G4, G0, F4, ESP32-S3), so cppcheck models ILP32 (unix32).
MISRA_FLAGS := --std=c99 --language=c --platform=unix32 --enable=style --addon=misra \
	--inline-suppr --quiet --suppress=missingIncludeSystem

.PHONY: all gen check parse lint test drift misra clean

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

## misra: cppcheck style + MISRA C:2012 on each gen/c node, blocking (D-046; misra/README.md)
# The canary proves that the addon runs. A directory scan only sees headers that some .c
# includes, so each node's header-only files (e.g. platform_limits.h) are added by name.
misra:
	@$(CPPCHECK) --version
	@out=$$($(CPPCHECK) $(MISRA_FLAGS) --template='{id}' misra/canary.c 2>&1); \
	for id in 10.8 15.6 17.7; do \
		echo "$$out" | grep -qx "misra-c2012-$$id" || { echo "misra: the addon did not report $$id on misra/canary.c"; exit 1; }; \
	done
	@if grep -rn 'cppcheck-suppress' gen/c | grep -v 'DEV-[0-9]'; then \
		echo "inline cppcheck suppressions must name a deviation (DEV-xxx) from misra/README.md"; exit 1; \
	fi
	@status=0; for node in gen/c/*/; do \
		headers=; for h in $$node*.h; do \
			grep -qs "#include \"$${h##*/}\"" $$node*.c $$node*.h || headers="$$headers $$h"; \
		done; \
		echo "misra: $$node (header-only:$${headers:- none})"; \
		$(CPPCHECK) $(MISRA_FLAGS) --error-exitcode=1 --suppressions-list=misra/suppressions.txt \
			-I $$node $$node $$headers || status=1; \
	done; \
	if [ $$status -ne 0 ]; then echo "misra: findings above are not in misra/README.md"; exit 1; fi; \
	echo "misra: gen/c clean"

clean:
	rm -rf tools/codegen/.cache tools/codegen/.pytest_cache tools/codegen/.ruff_cache
