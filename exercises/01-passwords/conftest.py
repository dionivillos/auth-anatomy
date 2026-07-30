"""Put the repository root on sys.path so exercises can import `authcore`/`app`.

When pytest is pointed at this directory it adds *this* directory to sys.path
(for the `eN_*` modules) but not the repository root, so `import authcore` would
fail without this shim.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
