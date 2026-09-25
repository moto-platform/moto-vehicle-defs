# moto-vehicle-defs — generate and verify gen/ from the sources.
UV       ?= uv
CODEGEN  := $(UV) run --project tools/codegen
CFLAGS_GEN := -std=c99 -Wall -Wextra -Werror -pedantic -Wconversion -Wshadow

.PHONY: gen check test lint clean

gen:            ## validate sources, then regenerate gen/ (commit the result)
	$(CODEGEN) moto-codegen gen --root .

check:          ## CI: sources valid, gen/ in sync, generated C compiles
	$(CODEGEN) moto-codegen gen --root .
	git diff --exit-code --stat -- gen/
	@test -z "$$(git status --porcelain --untracked-files=all -- gen/)" || \
		(echo "gen/ has untracked files: run make gen and commit" && git status --short -- gen/ && exit 1)

test:           ## codegen unit tests (incl. compiling and running the generated C)
	$(CODEGEN) pytest -q tools/codegen/tests

lint:
	$(CODEGEN) ruff check tools/codegen gen/python
	$(CODEGEN) ruff format --check tools/codegen

clean:
	rm -rf .cache
