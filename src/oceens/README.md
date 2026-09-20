# Package conventions in `oceens`

You should be able to learn everything a package here offers by reading **one**
file — its `__init__.py` — and to trust that reading. That is true because it is
checked: `tach check` fails on any import that reaches past a package's public
surface. This is a constraint, not a suggestion.

## The rule

**Private means a name starting with `_`.** From outside a package, you may
import a name only if every segment of its path starts with something other than
an underscore.

```python
from oceens.core import check_survey_access_and_status   # fine: the public surface
from oceens.core.database import SessionDep               # fine: a public entry point
from oceens.core.auth import _build_msal_app              # fails `tach check`
```

Inside a package, its own modules import each other however they like. The rule
governs what crosses the package boundary, not how the implementation behind it
is arranged.

## The shape

```
src/oceens/
  core/
    __init__.py     the public surface: named re-exports + __all__
    database.py     a further entry point — public, because no leading underscore
    _internal/      everything else, unreachable from outside
      _something.py
```

A package under `src/oceens/` is `core`, `models`, `routers`, `services`,
`seed_data` or `llm_utils` — an immediate subdirectory with an `__init__.py`.
`static/` and `templates/` hold no Python, so they are not packages. The modules
sitting beside them (`main.py`, `sondage_loader.py`...) are outside every
package: they may use any of them, and are bound by each one's interface like
anyone else.

No package here has an `_internal/` folder yet; `routers/llm/_access.py` is the
one private module, and `routers` is free to use it because it is its own.

Adding a package, or a private folder inside one, needs no edit to `tach.toml`.
The rule is written once, generically, and applies to whatever is there.

## Writing an interface

Re-export explicit names and list them in `__all__`:

```python
from oceens.core.security import check_survey_access_and_status

__all__ = ["check_survey_access_and_status"]
```

**Never `from ._internal import *`.** A star re-export makes the public surface
unenumerable, which defeats the one thing this whole arrangement buys: that a
reader — human or agent — learns the package from a single file. `tach` checks
the import boundary, not the re-export style, so this rule is yours to keep.

Keep the surface small. A package with thirty exported names is not a deep
module; it is a folder. When one gets that large, the question is what it is
hiding, and usually the answer is: not enough.

## Running the check

```sh
uv run tach check
uv run python scripts/check_cycles.py
```

The same two commands run in CI on every push and every pull request
(`.github/workflows/architecture.yml`), from a fresh checkout and against the
versions `uv.lock` pins — so a boundary broken locally is caught on the branch
whether or not anyone ran them by hand.

A clean exit means every import in the repo goes through a public surface and
no two packages depend on each other. On a violation there is nothing to hunt
for: `tach check` names the offending import, and `check_cycles.py` names the
two packages caught in the cycle.

A check that passes quietly is worth nothing until you have watched it fail, so
each half was proved against a real violation and the violation then reverted:

```sh
# tach check: reach for a private name from outside its package
echo 'from oceens.core.auth import _build_msal_app' >> src/oceens/main.py
uv run tach check        # names oceens.core.auth._build_msal_app
git checkout src/oceens/main.py

# check_cycles.py: point a lower package back up at a higher one
echo 'from oceens.services import helpers' >> src/oceens/core/settings_store.py
uv run python scripts/check_cycles.py   # names oceens.core <-> oceens.services
git checkout src/oceens/core/settings_store.py
```
