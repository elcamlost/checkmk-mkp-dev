import inspect
import sys


def main() -> None:
    pkg_name = sys.argv[1] if len(sys.argv) > 1 else None
    if not pkg_name:
        print(f"Usage: {sys.argv[0]} <pkg_name>", file=sys.stderr)
        sys.exit(1)

    try:
        from cmk.discover_plugins import discover_all_plugins
    except ImportError:
        from cmk.discover_plugins import discover_plugins as discover_all_plugins

    from cmk.discover_plugins import PluginGroup
    from cmk.rulesets.v1 import entry_point_prefixes

    kwargs: dict = {"raise_errors": False}
    if "skip_wrong_types" in inspect.signature(discover_all_plugins).parameters:
        kwargs["skip_wrong_types"] = True

    result = discover_all_plugins(PluginGroup.RULESETS, entry_point_prefixes(), **kwargs)

    errors = [str(e) for e in result.errors if pkg_name in str(e)]
    for e in errors:
        print("ERROR:", e)

    found = [loc.module for loc in result.plugins if pkg_name in loc.module]
    for f in found:
        print("Found:", f)

    if errors:
        print(f"FAIL: plugin has {len(errors)} error(s)")
        sys.exit(1)
    if not found:
        print(f"FAIL: {pkg_name} not found in discovered plugins")
        sys.exit(1)

    print("OK")


if __name__ == "__main__":
    main()
