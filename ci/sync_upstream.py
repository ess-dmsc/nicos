#!/usr/bin/env python3
"""Merge upstream NICOS (mlz-ictrl/nicos) into the current branch.

Only the paths in UPSTREAM_PATHS are taken from upstream; every other path
stays exactly as it is on our side, and upstream-only paths (other facilities,
packaging, upstream CI) are dropped.  The merge is left uncommitted so that
conflicts and follow-ups can be handled before committing.  See UPSTREAM.md.
"""

import argparse
import subprocess
import sys

UPSTREAM_URL = "https://github.com/mlz-ictrl/nicos.git"
UPSTREAM_PATHS = {
    "bin",
    "conftest.py",
    "nicos",
    "nicos_demo",
    "nicos_mlz",
    "nicostools",
    "resources",
    "test",
    "tools",
}
UPSTREAM_DEPENDENCY_FILES = [
    "setup.py",
    "requirements.txt",
    "requirements-gui.txt",
    "requirements-opt.txt",
    "requirements-dev.txt",
]
QRC = "resources/nicos-gui.qrc"


def git(*args, check=True):
    return subprocess.run(
        ["git", *args], check=check, capture_output=True, text=True
    ).stdout


def toplevel(ref):
    return set(git("ls-tree", "--name-only", ref).split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", default="upstream")
    parser.add_argument("--branch", default="master")
    opts = parser.parse_args()

    if git("status", "--porcelain", "--untracked-files=no").strip():
        sys.exit("working tree has uncommitted changes, aborting")
    if opts.remote not in git("remote").split():
        git("remote", "add", opts.remote, UPSTREAM_URL)
    git("fetch", opts.remote, opts.branch)
    ref = f"{opts.remote}/{opts.branch}"
    previous = git("merge-base", "HEAD", ref).strip()
    if previous == git("rev-parse", ref).strip():
        print(f"already up to date with {ref}")
        return 0

    subprocess.run(
        ["git", "merge", "--no-ff", "--no-commit", ref],
        check=False,
        capture_output=True,
    )
    for name in sorted((toplevel("HEAD") | toplevel("MERGE_HEAD")) - UPSTREAM_PATHS):
        git("rm", "-r", "-q", "-f", "--ignore-unmatch", "--", name)
        if name in toplevel("HEAD"):
            git("checkout", "HEAD", "--", name)

    conflicts = git("diff", "--name-only", "--diff-filter=U").split()
    changed = git("diff", "--name-only", previous, ref, "--").split()
    deps = git("diff", previous, ref, "--", *UPSTREAM_DEPENDENCY_FILES)

    print(
        f"merged {ref} ({git('rev-parse', '--short', ref).strip()}), "
        f"{len(changed)} files changed upstream since "
        f"{git('rev-parse', '--short', previous).strip()}"
    )
    if conflicts:
        print("\nconflicts to resolve by hand:")
        print("\n".join(f"  {c}" for c in conflicts))
    if deps:
        print("\nupstream dependency changes, port them to pyproject.toml:")
        print(deps)
    if QRC in changed:
        print(
            f"\n{QRC} changed: regenerate nicos/guisupport/gui_rc_qt*.py "
            "(see UPSTREAM.md)"
        )
    print(
        "\nnext: resolve conflicts, run tools/check-setups on all "
        "nicos_ess setups and the test suite, then commit the merge "
        "(never squash it)."
    )
    return 1 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
