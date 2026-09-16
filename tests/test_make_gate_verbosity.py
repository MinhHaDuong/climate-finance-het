"""Keep routine test gates concise while retaining failure diagnostics."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_routine_make_gates_use_quiet_pytest_output():
    lines = (ROOT / "Makefile").read_text().splitlines()
    targets = {"check-package", "check", "check-fast", "lint"}
    recipes = {}
    current = None
    for line in lines:
        if line and not line.startswith(("\t", " ")) and ":" in line:
            current = line.split(":", 1)[0] if line.split(":", 1)[0] in targets else None
        elif current and line.startswith("\t"):
            recipes.setdefault(current, []).append(line)
    assert set(recipes) == targets
    for target, recipe in recipes.items():
        command = " ".join(recipe)
        assert " -q" in command, f"{target} should use concise pytest output"
        assert " -v" not in command, f"{target} should not stream one line per test"
