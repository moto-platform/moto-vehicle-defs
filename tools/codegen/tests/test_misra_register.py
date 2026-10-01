"""misra/: every cppcheck suppression is a registered deviation for that rule (D-046)."""

import re

from moto_codegen import config

MISRA_DIR = config.REPO_ROOT / "misra"
# MISRA C:2012 (with Amendment 1) mandatory rules: never deviated (MISRA Compliance:2020).
MANDATORY = {
    "9.1", "12.5", "13.6", "17.3", "17.4", "17.6", "19.1",
    "21.13", "21.17", "21.18", "21.19", "21.20", "22.2", "22.4", "22.5", "22.6",
}  # fmt: skip


def _register() -> dict[str, set[str]]:
    """DEV-xxx -> the rule numbers named in its register row."""
    rows = {}
    for line in (MISRA_DIR / "README.md").read_text(encoding="utf-8").splitlines():
        if m := re.match(r"\| (DEV-\d{3}) \| ([^|]+) \|", line):
            rows[m[1]] = set(re.findall(r"\b\d{1,2}\.\d{1,2}\b", m[2]))
    return rows


def _check(rule: str, dev: str | None, rows: dict[str, set[str]], where: str) -> None:
    assert rule not in MANDATORY, f"{where}: mandatory rule {rule} cannot be deviated"
    assert dev in rows, f"{where}: {dev} has no row in misra/README.md"
    assert rule in rows[dev], f"{where}: {dev} does not cover rule {rule}"


def test_suppressions_list_is_registered():
    rows, dev = _register(), None
    lines = (MISRA_DIR / "suppressions.txt").read_text(encoding="utf-8").splitlines()
    for n, line in enumerate(lines, 1):
        if m := re.fullmatch(r"# (DEV-\d{3})", line):
            dev = m[1]
        elif line and not line.startswith("#"):
            m = re.fullmatch(r"misra-c2012-(\d+\.\d+)(:\S+)?", line)
            assert m, f"suppressions.txt:{n}: only file-scoped MISRA rules belong here: {line}"
            _check(m[1], dev, rows, f"suppressions.txt:{n}")


def test_inline_suppressions_are_registered():
    rows = _register()
    for path in sorted((config.GEN_DIR / "c").rglob("*.[ch]")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "cppcheck-suppress" in line:
                m = re.search(r"cppcheck-suppress misra-c2012-(\d+\.\d+) ; (DEV-\d{3}):", line)
                where = f"{path.relative_to(config.REPO_ROOT)}:{n}"
                assert m, f"{where}: use `cppcheck-suppress misra-c2012-<rule> ; DEV-xxx: <why>`"
                _check(m[1], m[2], rows, where)
