import logging
import socket
import time
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


def test_initialize_customer1(wait_for_db_up):
    time.sleep(10)


def test_initialize_customer2(wait_for_db_up):
    pass


def test_initialize_customer3(wait_for_db_up):
    pass


def test_initialize_customer4(wait_for_db_up):
    pass


def test_deposit_money(wait_for_db_up):

    customer_xid = str(uuid.uuid4())
    data = views.initialize_customer(customer_xid)
    token = data["token"]
    customer_dict = views.get_customer_info_by_token(token)

    with pytest.raises(views.MiniWalletException, match="not found"):
        data = views.deposit_money(customer_dict, 2000000, str(uuid.uuid4()))

    views.enable_or_create(customer_dict)

    amount = 1000 * 1000
    reference_id = str(uuid.uuid4())
    data = views.deposit_money(customer_dict, amount, reference_id)
    deposit_data = data["deposit"]
    assert deposit_data["status"] == "completed"

    data = views.get_balance(customer_dict)
    wallet_data = data["wallet"]
    assert wallet_data["balance"] == amount


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


# def not_test_get_customer_info_by_token():
#     token = "not_exist"
#     from alchemy_mock.mocking import UnifiedAlchemyMagicMock
#     # from alchemy_mock.mocking import AlchemyMagicMock
#     session = UnifiedAlchemyMagicMock(data=[(
#         [
#             mock.call.query(Customer),
#             mock.call.filter(Customer.token == token)
#         ],
#         [None]
#     )])
#     # session = AlchemyMagicMock()
#     # session.add(Customer(token="exist1"))
#     # session.add(Customer(token="exist2"))
#     with mock.patch.object(views.db, 'session', new=session) as mock_session:
#         # c = db.session.query(Customer).filter(Customer.token == token).one_or_none()
#         customer_dict = views.get_customer_info_by_token(token)
#         assert customer_dict is None
#         assert mock_session.query.assert_called()

#     # token = "not_exist"
#     # with mock.patch('sqlalchemy.orm.query.Query.one_or_none', return_value=None):
#     #     customer_dict = views.get_customer_info_by_token(token)
#     #     assert customer_dict is None

#     # # mock a customer on DB
#     # assert views.get_customer_info_by_token(token) is not None
