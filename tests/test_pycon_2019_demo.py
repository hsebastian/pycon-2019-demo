from pycon_2019_demo import __version__
from pycon_2019_demo import models


def test_version():
    assert __version__ == "0.1.0"


def test_version1():
    assert __version__ == "0.1.0"
    assert False


def test_version2():
    import time

    assert __version__ == "0.1.0"
    time.sleep(4)


def test_models():
    assert models.get_all()


def test_none():
    assert models.get_none()
