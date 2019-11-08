import requests


def test_end_to_end():
    """
    create user

    view wallet balance, verify fails
    deposit, verify fails

    enable wallet, verify enabled
    enable wallet again, verify fails

    view wallet balance, verify 0
    withdraw, verify fails

    deposit, verify balance updated
    view wallet balance, verify 0


    """
    assert False