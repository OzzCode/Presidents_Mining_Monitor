import importlib
import pkgutil
import pathlib
import sys
import types


def iter_py_modules(root=".", pkg_name=None):
    root_path = pathlib.Path(root).resolve()
    sys.path.insert(0, str(root_path))
    for module in pkgutil.walk_packages([str(root_path)]):
        name = module.name
        if name.startswith((".venv", "venv")):
            continue
        try:
            yield importlib.import_module(name)
        except Exception:
            # Best effort: ignore import errors unrelated to datetime
            pass


def test_no_datetime_shadowing():
    for m in iter_py_modules():
        if isinstance(m, types.ModuleType) and m.__name__.endswith("datetime"):
            # If you truly have a local module named datetime, fail this test
            assert False, f"Local module named 'datetime' found: {m.__name__}"


def test_datetime_usage_examples():
    # Sanity check the stdlib works as expected in this environment
    import datetime as dt
    assert hasattr(dt, "datetime")
    assert hasattr(dt.datetime, "utcnow")
