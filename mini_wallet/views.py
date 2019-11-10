import datetime
import jsend
import logging
import os

from flask import Flask
from flask import request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func


logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


app = Flask(__name__)
app.logger.info("Just started {}".format(app.name))

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "mini_wallet.db"))
app.config['SQLALCHEMY_DATABASE_URI'] = database_file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
for key, value in app.config.items():
    app.logger.info("{key}: {value}".format(key=key, value=value))

db = SQLAlchemy(app)


# https://stackoverflow.com/questions/31584974/sqlalchemy-model-django-like-save-method
class Customer(db.Model):
    __tablename__ = 'customer'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=func.now())

    xid = db.Column(db.Text, unique=True, nullable=False)  # 93de1727-943d-443e-b311-0da531a267a7
    token = db.Column(db.Text, unique=True, nullable=False)

    wallet = db.relationship("Wallet", uselist=False, back_populates="customer")


class Wallet(db.Model):
    __tablename__ = 'wallet'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    xid = db.Column(db.Text, nullable=False)  # 93de1727-943d-443e-b311-0da531a267a7
    balance = db.Column(db.Numeric, default=0, nullable=False)
    status = db.Column(db.Text, default="enabled", nullable=False)

    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    customer = db.relationship("Customer", back_populates="wallet")

    balance_change = db.relationship("BalanceChange", back_populates="wallet")
    status_change = db.relationship("StatusChange", back_populates="wallet")


class BalanceChange(db.Model):
    __tablename__ = 'balance_change'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=func.now())

    xid = db.Column(db.Text, nullable=False)  # 93de1727-943d-443e-b311-0da531a267a7
    amount = db.Column(db.Numeric, nullable=False)
    reference_id = db.Column(db.Text, unique=True, nullable=False)

    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'))
    wallet = db.relationship("Wallet", back_populates="balance_change")


class StatusChange(db.Model):
    __tablename__ = 'status_change'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=func.now())

    status = db.Column(db.Text, nullable=False)

    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'))
    wallet = db.relationship("Wallet", back_populates="status_change")

app.logger.info("-" * 80)

import uuid
import secrets

db.create_all()


from contextlib import contextmanager


@contextmanager
def enter_session():
    """Provide a transactional scope around a series of operations."""
    session = db.session()
    try:
        yield session
        session.commit()
        app.logger.info("committed")
    except Exception as e:
        session.rollback()
        app.logger.info(e)
        raise e
    finally:
        session.close()


token = secrets.token_hex(21)
wallet_xid = str(uuid.uuid4())
with enter_session() as session:
    customer = Customer(xid=str(uuid.uuid4()), token=token)
    # wallet = Wallet(xid=wallet_xid, customer=customer)
    # app.logger.info(wallet.customer.token)
    # app.logger.info(wallet.xid)

    session.add(customer)
    # session.add(wallet)

with enter_session() as session:
    wallet = session.query(Wallet).join(Customer).filter(Customer.token==token).one_or_none()
    # app.logger.info(wallet.xid)
    # app.logger.info(wallet.balance)
    # app.logger.info(wallet.status)

# with enter_session() as session:
#     for customer in Customer.query.all():
#         app.logger.info(customer.wallet)

app.logger.info("-" * 80)
################################################################################


@app.route("/api/v1/init", methods=["POST"])
def initialize_customer():
    customer_xid = request.json["customer_xid"]
    with enter_session() as session:
        token = secrets.token_hex(21)
        customer = Customer(xid=customer_xid, token=token)
        session.add(customer)
    return jsend.success({"token": token})


@app.route("/api/v1/wallet", methods=["POST"])
def enable():
    authorization = request.headers.get("Authorization")
    if not authorization.startswith("Token "):
        return jsend.fail({"error": "Incorrect Authorization signature: 'Token <my token>'"}), 401
    _, token = authorization.split(" ")

    customer = db.session.query(Customer).filter(Customer.token==token).one_or_none()
    if not customer:
        return jsend.fail({"error": "Incorrect token"}), 401

    data = dict()

    wallet = customer.wallet
    if not wallet:
        wallet_xid = str(uuid.uuid4())
        wallet = Wallet(xid=wallet_xid, customer=customer, status="enabled")
        db.session.add(wallet)
        status_change = StatusChange(wallet=wallet, status="enabled")
        db.session.add(status_change)
        wallet = Wallet.query.filter(Wallet.xid==wallet_xid).one_or_none()
        status_change = StatusChange.query.filter(StatusChange.wallet==wallet).order_by(StatusChange.id.desc()).first()
    else:
        if wallet.status == "enabled":
            return jsend.fail({"error": "Already enabled"}), 400

        wallet.status = "enabled"
        db.session.merge(wallet)
        status_change = StatusChange(wallet=wallet, status="enabled")
        db.session.add(status_change)

    data["wallet"] = {
        "id": wallet.xid,
        "owned_by": customer.xid,
        "status": wallet.status,
        "enabled_at": status_change.created_at,
        "balance": wallet.balance
    }
    db.session.commit()
    logging.info(data)
    return jsend.success(data), 201


@app.route("/api/v1/wallet", methods=["PATCH"])
def disable():
    authorization = request.headers.get("Authorization")
    if not authorization.startswith("Token "):
        return jsend.fail({"error": "Incorrect Authorization signature: 'Token <my token>'"}), 401
    _, token = authorization.split(" ")

    customer = db.session.query(Customer).filter(Customer.token==token).one_or_none()
    if not customer:
        return jsend.fail({"error": "Incorrect token"}), 401

    is_disabled = request.form.get("is_disabled")
    assert False


@app.route("/api/v1/wallet", methods=["GET"])
def view():
    authorization = request.headers.get("Authorization")
    if not authorization.startswith("Token "):
        return jsend.fail({"error": "Incorrect Authorization signature: 'Token <my token>'"}), 401
    _, token = authorization.split(" ")

    customer = db.session.query(Customer).filter(Customer.token==token).one_or_none()
    if not customer:
        return jsend.fail({"error": "Incorrect token"}), 401

    assert False


@app.route("/api/v1/wallet/deposits", methods=["POST"])
def deposit():
    authorization = request.headers.get("Authorization")
    if not authorization.startswith("Token "):
        return jsend.fail({"error": "Incorrect Authorization signature: 'Token <my token>'"}), 401
    _, token = authorization.split(" ")

    customer = db.session.query(Customer).filter(Customer.token==token).one_or_none()
    if not customer:
        return jsend.fail({"error": "Incorrect token"}), 401

    amount = request.fdb.get("amount")
    reference_id = request.fdb.get("reference_id")
    assert False


@app.route("/api/v1/wallet/withdrawals", methods=["POST"])
def withdraw():
    authorization = request.headers.get("Authorization")
    if not authorization.startswith("Token "):
        return jsend.fail({"error": "Incorrect Authorization signature: 'Token <my token>'"}), 401
    _, token = authorization.split(" ")

    customer = db.session.query(Customer).filter(Customer.token==token).one_or_none()
    if not customer:
        return jsend.fail({"error": "Incorrect token"}), 401

    amount = request.fdb.get("amount")
    reference_id = request.fdb.get("reference_id")
    assert False


################################################################################


class MiniWalletException(Exception):
    pass


def enable_or_create(customer_token):

    raise MiniWalletException("todo")


def disable(customer_token):
    raise MiniWalletException("todo")


def get_balance(customer_token):

    raise MiniWalletException("todo")


def deposit(customer_token, amount, reference_id):
    raise MiniWalletException("todo")


def withdraw(customer_token, amount, reference_id):
    raise MiniWalletException("todo")
