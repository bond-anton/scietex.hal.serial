"""Test package version is correctly set"""

import pytest

try:
    from src.scietex.hal.serial import __version__ as version
except ModuleNotFoundError:
    from scietex.hal.serial import __version__ as version


def test_check_version_numbering():
    """
    Version must be a string with the three integers separated by a dot.
    Example: `0.1.4` or `2.0.0`.
    All three digits must not negative and must not be equal to zero at the same time.
    """
    # Assert version is a string.
    assert isinstance(version, str)

    # Assert no extra space present. Example: " 0.1.1  " is not correct, "0.1.1" is correct.
    assert len(version) == len(version.strip())

    # Assert all three parts are present
    v_l = version.split(".")
    assert len(v_l) == 3

    # Assert no extra space present in each part.
    # Example: "0. 1 .1" is not correct, "0.1.1" is correct
    for i in range(3):
        assert len(v_l[i]) == len(v_l[i].strip())

    # Convert all parts of the version to int values
    v_maj = int(v_l[0])
    v_min = int(v_l[1])
    v_patch = int(v_l[2])

    # Assert all version numbers are not negative
    assert v_maj >= 0
    assert v_min >= 0
    assert v_patch >= 0

    # Assert all version numbers are not equal to zero at the same time
    assert v_maj + v_min + v_patch > 0


if __name__ == "__main__":
    pytest.main()
