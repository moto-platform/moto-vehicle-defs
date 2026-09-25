# moto-codegen

Generator and consistency checks for moto-vehicle-defs. Run it through the repo `Makefile` (`make check`, `make gen`). Modules: `dbc_checks` (ID plan, E2E layout, DataIDs, naming), `yaml_checks` (CL250 YAML incl. D-020, `uds/dids.yaml`), `gen_c` (cantools per node + E2E + DID table), `gen_python`, `gen_vss` (pinned COVESA VSS 6.0 + vss-tools 6.0), `e2e` (reference implementation the C code is tested against). Node targets and the ID plan live in `config.py`.
