import requests
import uuid


def get_mini_wallet_api():
    return


class InitializeResponse:
    pass


# https://pypi.org/project/pytest-base-url/

def test_end_to_end():
    """
    This is run against a live server.

    initialize account for customer

    view wallet balance, verify fails
    deposit, verify fails

    enable wallet, verify enabled
    enable wallet again, verify fails

    view wallet balance, verify 0
    withdraw, verify fails

    deposit, verify balance updated
    view wallet balance, verify 0
    """

    # Given customer never have a wallet,
    # when hitting the initialize account endpoint,
    # then a functional token is created
    base_url = "http://127.0.0.1:5000"
    endpoint = base_url + "/api/v1/init"
    customer_id = str(uuid.uuid4())
    response = requests.post(endpoint, json={"customer_xid": customer_xid})
    content = response.json()
    actual_token = content["data"]["token"]
    assert len(actual_token) == 41

    # Given a functional token,
    # when hitting the balance endpoint or depositing funds
    # then error response is returned
    endpoint = base_url + "/api/v1/wallet"
    customer_xid = str(uuid.uuid4())
    response = requests.get(endpoint, headers={"Authorization": "Token {token}".format(token=actual_token)})
    content = response.json()
    error = content["data"]["error"]
    assert error == "Disabled"

    endpoint = base_url + "/api/v1/wallet/deposits"
    reference_id = str(uuid.uuid4())
    response = requests.get(endpoint, headers={"Authorization": "Token {token}".format(token=actual_token)})
    content = response.json()
    error = content["data"]["error"]
    assert error == "Disabled"

