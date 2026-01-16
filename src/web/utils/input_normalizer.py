# src/web/utils/input_normalizer.py
from __future__ import annotations

from typing import Optional


class InputNormalizer:
    @staticmethod
    def normalize_str(value: Optional[str]) -> Optional[str]:
        """
        If value is None -> None
        Else trim; if empty after trim -> None
        Else -> trimmed string
        """
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed if trimmed else None

    @staticmethod
    def normalize_float(value: Optional[float]) -> Optional[float]:
        """
        If value is None -> None
        Else -> abs(float(value))
        """
        if value is None:
            return None
        return abs(float(value))
