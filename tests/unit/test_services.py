import pytest
from unittest import mock
from mini_wallet import views
from mini_wallet.views import Customer
from mini_wallet.views import db
import socket, errno
import logging
from waiting import wait


pytest_plugins = ["docker_compose"]


@pytest.fixture(scope="session")
def wait_for_db_up(session_scoped_container_getter):
    def is_db_up(host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            up = s.connect_ex((host, port)) == 0
            if not up:
                logging.warning("db at {host}:{port} not up yet".format(host=host, port=port))
            return up
    service = session_scoped_container_getter.get("db").network_info[0]
    wait(lambda: is_db_up(service.hostname, int(service.host_port)), timeout_seconds=5)


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


def test_initialize_customer1(wait_for_db_up):
    pass


def test_initialize_customer2(wait_for_db_up):
    pass


def test_initialize_customer3(wait_for_db_up):
    pass


def test_initialize_customer4(wait_for_db_up):
    pass


def test_initialize_customer5(wait_for_db_up):
    pass


def test_initialize_customer6(wait_for_db_up):
    pass
