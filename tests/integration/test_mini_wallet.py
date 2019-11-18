import requests
import uuid
import logging


def get_mini_wallet_api():
    return MiniWalletRequests()


class MiniWalletRequests:
    def __init__(self, base_url):
        self.base_url = base_url

    def initialize(customer_xid):
        pass

    def enable():
        pass

    def deposit(amount, reference_id):
        pass

    def withdraw(amount, reference_id):
        pass

    def disable():
        pass


class BaseMiniWalletResponse:
    pass


class InitializeResponse(BaseMiniWalletResponse):
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
    logging.info("$" * 80)
    base_url = "http://127.0.0.1:5000"
    endpoint = base_url + "/api/v1/init"
    customer_xid = str(uuid.uuid4())
    response = requests.post(endpoint, json={"customer_xid": customer_xid})
    content = response.json()
    actual_token = content["data"]["token"]
    assert len(actual_token) == 42

    # # Given a functional token,
    # # when hitting the balance endpoint or depositing funds
    # # then error response is returned
    # endpoint = base_url + "/api/v1/wallet"
    # customer_xid = str(uuid.uuid4())
    # response = requests.get(
    #     endpoint,
    #     headers={"Authorization": "Token {token}".format(token=actual_token)}
    # )
    # content = response.json()
    # error = content["data"]["error"]
    # assert error == "Disabled"

    # Given a functional token and wallet is disabled,
    # when enabling the wallet,
    # then the wallet is then marked enabled and the balance can be shown
    endpoint = base_url + "/api/v1/wallet"
    response = requests.post(
        endpoint, headers={"Authorization": "Token {token}".format(token=actual_token)}
    )
    assert response.status_code == 201
    content = response.json()
    assert content["status"] == "success"
    assert content["data"]["wallet"]["status"] == "enabled"
    assert content["data"]["wallet"]["balance"] == 0

    # Given a wallet that is enabled,
    # when depositing some funds,
    # then the balance is increased
    endpoint = base_url + "/api/v1/wallet/deposits"
    form_data = {"amount": 5000000, "reference_id": str(uuid.uuid4())}
    response = requests.post(
        endpoint,
        data=form_data,
        headers={"Authorization": "Token {token}".format(token=actual_token)},
    )
    assert response.status_code == 201
    content = response.json()
    assert content["status"] == "success"
    assert content["data"]["wallet"]["status"] == "success"
    assert "id" in content["data"]["wallet"]

    # Given some funds are in the wallet,
    # when withdrawing an amount within the balance amount,
    # then the withdrawal is successful and remaining amount stays
    endpoint = base_url + "/api/v1/wallet/withdrawals"
    form_data = {"amount": 2000000, "reference_id": str(uuid.uuid4())}
    response = requests.post(
        endpoint,
        data=form_data,
        headers={"Authorization": "Token {token}".format(token=actual_token)},
    )
    assert response.status_code == 201
    content = response.json()
    assert content["status"] == "success"
    assert content["data"]["wallet"]["status"] == "success"
    assert "id" in content["data"]["wallet"]

    # # Given some money in the wallet,
    # # when withdrawing an amount bigger than the balance amount,
    # # then the withdrawal fails and the balance stays
    # endpoint = base_url + "/api/v1/wallet/withdrawals"
    # form_data = {
    #     "amount": 4000000,
    #     "reference_id": str(uuid.uuid4())
    # }
    # response = requests.post(
    #     endpoint,
    #     data=form_data,
    #     headers={"Authorization": "Token {token}".format(token=actual_token)}
    # )
    # assert response.status_code == 404
    # content = response.json()
    # assert content["status"] == "fail"
    # assert content["data"]["error"] == "Insufficient fund"

    # Given some funds are in the wallet,
    # when withdrawing an amount within the balance amount,
    # then the withdrawal is successful and remaining amount stays
    endpoint = base_url + "/api/v1/wallet"
    form_data = {"is_disabled": True}
    response = requests.patch(
        endpoint,
        data=form_data,
        headers={"Authorization": "Token {token}".format(token=actual_token)},
    )
    assert response.status_code == 201
    content = response.json()
    assert content["status"] == "success"
    assert content["data"]["wallet"]["status"] == "disabled"
