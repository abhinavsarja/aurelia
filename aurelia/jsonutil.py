"""Convert numpy / nested tool payloads into JSON-safe Python values."""
from __future__ import annotations

from typing import Any

import numpy as np


def jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return jsonable(obj.tolist())
    if isinstance(obj, np.str_):
        return str(obj)
    # pandas Timestamp etc.
    if hasattr(obj, "item") and callable(obj.item):
        try:
            return jsonable(obj.item())
        except Exception:
            pass
    return obj
