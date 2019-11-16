from pycon_2019_demo import __version__
from pycon_2019_demo import models

import logging


LOGGER = logging.getLogger(__name__)


def test_version():
    LOGGER.info("$" * 80)
    assert __version__ == "0.1.0"


# def test_version1():
#     assert __version__ == "0.1.0"
#     # assert False


# def test_version2():
#     import time

#     assert __version__ == "0.1.0"
#     time.sleep(3.2)


# def test_models():
#     assert models.get_all()


# def test_none():
#     assert models.get_none()
