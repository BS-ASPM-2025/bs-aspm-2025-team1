# tests/unit/test_input_normalizer.py

import pytest

from src.web.utils.input_normalizer import InputNormalizer


class TestNormalizeStr:
    def test_none_returns_none(self):
        assert InputNormalizer.normalize_str(None) is None

    @pytest.mark.parametrize("value", ["", "   ", "\n\t  "])
    def test_blank_after_trim_returns_none(self, value):
        assert InputNormalizer.normalize_str(value) is None

    def test_trims_and_returns_string(self):
        assert InputNormalizer.normalize_str("  hello  ") == "hello"

    def test_preserves_inner_spaces(self):
        assert InputNormalizer.normalize_str("  hello   world  ") == "hello   world"


class TestNormalizeFloat:
    def test_none_returns_none(self):
        assert InputNormalizer.normalize_float(None) is None

    @pytest.mark.parametrize(
        "value, expected",
        [
            (0, 0.0),
            (1, 1.0),
            (-1, 1.0),
            (2.5, 2.5),
            (-2.5, 2.5),
            ("3.2", 3.2),
            ("-3.2", 3.2),
            (" 4 ", 4.0),
        ],
    )
    def test_converts_to_float_and_abs(self, value, expected):
        assert InputNormalizer.normalize_float(value) == expected

    def test_raises_on_non_numeric(self):
        with pytest.raises(ValueError):
            InputNormalizer.normalize_float("abc")
