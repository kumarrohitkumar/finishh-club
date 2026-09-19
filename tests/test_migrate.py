"""
TESTS FOR THE MIGRATION RUNNER.

WHAT IT CHECKS
    That .sql files are found, ordered by their number, that non-SQL files are
    ignored, and that already-applied migrations are not run again.

NO DATABASE NEEDED
    These test the file discovery and ordering only. Applying SQL is tested
    against the real database in the integration check.

    Run:  python tests/test_migrate.py
"""
import sys, os, tempfile, pathlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.migrate import Migration, discover, pending


def make_dir(names):
    d = pathlib.Path(tempfile.mkdtemp())
    for n in names:
        (d / n).write_text(f"-- {n}\nSELECT 1;")
    return d


def test_discovers_sql_files():
    d = make_dir(["001_initial.sql", "002_add_index.sql"])
    assert [m.version for m in discover(d)] == [1, 2]


def test_orders_numerically_not_alphabetically():
    """009 must come before 010. Sorting as text would put 010 first."""
    d = make_dir(["010_tenth.sql", "009_ninth.sql", "002_second.sql"])
    assert [m.version for m in discover(d)] == [2, 9, 10]


def test_ignores_non_sql_files():
    d = make_dir(["001_initial.sql", "README.md", "notes.txt"])
    assert len(discover(d)) == 1


def test_ignores_badly_named_files():
    d = make_dir(["001_initial.sql", "no_number.sql"])
    assert [m.version for m in discover(d)] == [1]


def test_name_is_parsed():
    d = make_dir(["001_initial_schema.sql"])
    assert discover(d)[0].name == "initial_schema"


def test_sql_is_loaded():
    d = make_dir(["001_initial.sql"])
    assert "SELECT 1;" in discover(d)[0].sql


def test_pending_excludes_applied():
    d = make_dir(["001_a.sql", "002_b.sql", "003_c.sql"])
    got = pending(discover(d), applied={1, 2})
    assert [m.version for m in got] == [3]


def test_pending_is_everything_on_a_fresh_database():
    d = make_dir(["001_a.sql", "002_b.sql"])
    assert len(pending(discover(d), applied=set())) == 2


def test_missing_directory_is_empty_not_an_error():
    assert discover(pathlib.Path("/tmp/does-not-exist-xyz")) == []


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    p = 0
    for n, f in fns:
        try:
            f(); print(f"  PASS  {n}"); p += 1
        except AssertionError as e: print(f"  FAIL  {n}: {e}")
        except Exception as e: print(f"  ERROR {n}: {type(e).__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed"); sys.exit(0 if p == len(fns) else 1)
