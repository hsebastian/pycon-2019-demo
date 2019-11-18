import logging
import random
import socket
import uuid

import pytest
from waiting import wait

# from unittest import mock
from mini_wallet import views
from mini_wallet.views import db

# from sqlalchemy_utils.functions import create_database
# from sqlalchemy_utils.functions import drop_database
from sqlalchemy.exc import OperationalError


pytest_plugins = ["docker_compose"]


@pytest.fixture(scope="session")
def api_client():
    with views.app.test_client() as client:
        # views.app.config["TESTING"] = True
        yield client


@pytest.fixture(scope="session")
def wait_for_db_up(session_scoped_container_getter):

    service = session_scoped_container_getter.get("db").network_info[0]

    def is_db_up(host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            up = s.connect_ex((host, port)) == 0
            if not up:
                logging.warning(
                    "db at {host}:{port} not up yet".format(host=host, port=port)
                )
            return up

    wait(lambda: is_db_up(service.hostname, int(service.host_port)), timeout_seconds=5)

    def can_connect_db():
        can_connect = False
        try:
            connection = db.engine.connect()
            connection.close()
            can_connect = True
        except OperationalError:
            logging.warning("cannot connect yet")
        return can_connect

    wait(lambda: can_connect_db(), timeout_seconds=5)

    db.create_all()

    # create_database('postgres://mydbuser:mydbpassword@localhost/mydb1')
    # http://www.axelcdv.com/python/flask/postgresql/2018/03/30/flask-postgres-tests.html

    yield session_scoped_container_getter

    # drop_database('postgres://mydbuser:mydbpassword@localhost/mydb1')


def test_initialize_customer(wait_for_db_up):

    token = "invalid"
    customer_dict = views.get_customer_info_by_token(token)
    assert customer_dict is None

    customer_xid = str(uuid.uuid4())
    data = views.initialize_customer(customer_xid)
    token = data["token"]
    assert len(token) == 42

    customer_dict = views.get_customer_info_by_token(token)
    assert customer_dict["xid"] == customer_xid

    with pytest.raises(views.MiniWalletException, match="already initialized"):
        views.initialize_customer(customer_xid)


def test_enable_or_create_wallet(wait_for_db_up):

    customer_xid = str(uuid.uuid4())
    data = views.initialize_customer(customer_xid)
    token = data["token"]
    customer_dict = views.get_customer_info_by_token(token)

    with pytest.raises(views.MiniWalletException, match="not found"):
        views.disable_wallet(customer_dict)

    data = views.enable_or_create(customer_dict)
    wallet_data = data["wallet"]
    assert wallet_data["customer"] == customer_xid
    assert wallet_data["status"] == "enabled"

    with pytest.raises(views.MiniWalletException, match="already enabled"):
        views.enable_or_create(customer_dict)

    data = views.disable_wallet(customer_dict)
    wallet_data = data["wallet"]
    assert wallet_data["status"] == "disabled"

    with pytest.raises(views.MiniWalletException, match="already disabled"):
        views.disable_wallet(customer_dict)

    data = views.enable_or_create(customer_dict)
    wallet_data = data["wallet"]
    assert wallet_data["customer"] == customer_xid
    assert wallet_data["status"] == "enabled"


def test_get_balance(wait_for_db_up):

    customer_xid = str(uuid.uuid4())
    data = views.initialize_customer(customer_xid)
    token = data["token"]
    customer_dict = views.get_customer_info_by_token(token)

    with pytest.raises(views.MiniWalletException, match="not found"):
        data = views.get_balance(customer_dict)

    views.enable_or_create(customer_dict)
    views.disable_wallet(customer_dict)

    with pytest.raises(views.MiniWalletException, match="not enabled"):
        data = views.get_balance(customer_dict)


def test_deposit_money(wait_for_db_up):

    customer_xid = str(uuid.uuid4())
    data = views.initialize_customer(customer_xid)
    token = data["token"]
    customer_dict = views.get_customer_info_by_token(token)

    with pytest.raises(views.MiniWalletException, match="not found"):
        data = views.deposit_money(customer_dict, 2000000, str(uuid.uuid4()))

    views.enable_or_create(customer_dict)

    expected_total_deposit = 0
    for i in range(10):
        amount = random.randint(1, 9) * 1000 * 1000 * 1000 * 1000
        expected_total_deposit += amount
        reference_id = str(uuid.uuid4())
        data = views.deposit_money(customer_dict, amount, reference_id)
        deposit_data = data["deposit"]
        assert deposit_data["status"] == "completed"

    data = views.get_balance(customer_dict)
    wallet_data = data["wallet"]
    assert wallet_data["balance"] == expected_total_deposit

    amount = 3 * 1000 * 1000
    reference_id = str(uuid.uuid4())
    data = views.deposit_money(customer_dict, amount, reference_id)
    deposit_data = data["deposit"]
    assert deposit_data["status"] == "completed"
    with pytest.raises(views.MiniWalletException, match="duplicate reference_id"):
        amount = 2 * 1000 * 1000
        data = views.deposit_money(customer_dict, amount, reference_id)

    for amount in [-1, 0]:
        with pytest.raises(views.MiniWalletException, match="must be positive"):
            reference_id = str(uuid.uuid4())
            data = views.deposit_money(customer_dict, amount, reference_id)


def test_withdraw_money(wait_for_db_up):

    customer_xid = str(uuid.uuid4())
    data = views.initialize_customer(customer_xid)
    token = data["token"]
    customer_dict = views.get_customer_info_by_token(token)

    with pytest.raises(views.MiniWalletException, match="not found"):
        data = views.withdraw_money(customer_dict, 2000000, str(uuid.uuid4()))

    views.enable_or_create(customer_dict)

    deposit_amount = 3 * 1000
    reference_id = str(uuid.uuid4())
    data = views.deposit_money(customer_dict, deposit_amount, reference_id)
    deposit_data = data["deposit"]
    assert deposit_data["status"] == "completed"

    withdrawal_amount = 2 * 1000
    reference_id = str(uuid.uuid4())
    data = views.withdraw_money(customer_dict, withdrawal_amount, reference_id)
    deposit_data = data["withdrawal"]
    assert deposit_data["status"] == "completed"

    remaining_balance = deposit_amount - withdrawal_amount
    data = views.get_balance(customer_dict)
    wallet_data = data["wallet"]
    assert wallet_data["balance"] == remaining_balance

    withdrawal_amount = remaining_balance + 1
    reference_id = str(uuid.uuid4())
    with pytest.raises(views.MiniWalletException, match="insufficient fund"):
        data = views.withdraw_money(customer_dict, withdrawal_amount, reference_id)

    reference_id = str(uuid.uuid4())
    data = views.withdraw_money(customer_dict, remaining_balance, reference_id)
    deposit_data = data["withdrawal"]
    assert deposit_data["status"] == "completed"

    data = views.get_balance(customer_dict)
    wallet_data = data["wallet"]
    assert wallet_data["balance"] == 0

    for amount in [-1, 0]:
        reference_id = str(uuid.uuid4())
        with pytest.raises(views.MiniWalletException, match="must be positive"):
            data = views.withdraw_money(customer_dict, amount, reference_id)

    deposit_amount = 3 * 1000
    reference_id = str(uuid.uuid4())
    data = views.deposit_money(customer_dict, deposit_amount, reference_id)
    deposit_data = data["deposit"]
    assert deposit_data["status"] == "completed"

    withdrawal_amount = 1 * 1000
    with pytest.raises(views.MiniWalletException, match="duplicate reference_id"):
        data = views.withdraw_money(customer_dict, withdrawal_amount, reference_id)

    views.disable_wallet(customer_dict)
    withdrawal_amount = 2 * 1000 * 1000
    reference_id = str(uuid.uuid4())
    with pytest.raises(views.MiniWalletException, match="not enabled"):
        data = views.withdraw_money(customer_dict, withdrawal_amount, reference_id)


def test_api(api_client, wait_for_db_up):
    customer_xid = str(uuid.uuid4())
    response = api_client.post("/api/v1/init", json={"customer_xid": customer_xid})
    assert response.status_code == 201
    data = response.get_json()
    assert data["status"] == "success"
    token = data["data"]["token"]

    response = api_client.post(
        "/api/v1/wallet", headers={"Authorization": "{}".format(token)}
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "fail"

    response = api_client.post("/api/v1/wallet")
    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "fail"

    response = api_client.post(
        "/api/v1/wallet", headers={"Authorization": "Token {}".format("invalid_token")}
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "fail"

    response = api_client.post(
        "/api/v1/wallet", headers={"Authorization": "Token {}".format(token)}
    )
    data = response.get_json()
    assert response.status_code == 201
    assert data["status"] == "success"
    assert data["data"]["wallet"]["customer"] == customer_xid

    response = api_client.post(
        "/api/v1/wallet/deposits",
        headers={"Authorization": "Token {}".format(token)},
        data={"amount": 2000000, "reference_id": str(uuid.uuid4())},
    )
    data = response.get_json()
    assert response.status_code == 201
    assert data["status"] == "success"
    assert data["data"]["deposit"]["status"] == "completed"

    response = api_client.post(
        "/api/v1/wallet/withdrawals",
        headers={"Authorization": "Token {}".format(token)},
        data={"amount": 2000000, "reference_id": str(uuid.uuid4())},
    )
    data = response.get_json()
    assert response.status_code == 201
    assert data["status"] == "success"
    assert data["data"]["withdrawal"]["status"] == "completed"

    response = api_client.get(
        "/api/v1/wallet", headers={"Authorization": "Token {}".format(token)}
    )
    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "success"
    assert data["data"]["wallet"]["balance"] == 0

    response = api_client.post(
        "/api/v1/wallet/withdrawals",
        headers={"Authorization": "Token {}".format(token)},
        data={"amount": 2000000, "reference_id": str(uuid.uuid4())},
    )
    data = response.get_json()
    assert response.status_code == 400
    assert data["status"] == "fail"
    assert "insufficient" in data["data"]["error"]

    response = api_client.patch(
        "/api/v1/wallet",
        headers={"Authorization": "Token {}".format(token)},
        data={"is_disabled": True},
    )
    data = response.get_json()
    assert response.status_code == 201
    assert data["status"] == "success"
    assert data["data"]["wallet"]["customer"] == customer_xid
