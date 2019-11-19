import jsend
import logging
import uuid
import secrets
from contextlib import contextmanager
from functools import wraps

from flask import Flask
from flask import request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from sqlalchemy import exc

from webargs import fields
from webargs.flaskparser import use_args


logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

app = Flask(__name__)
app.logger.info("Just started {}".format(app.name))

# project_dir = os.path.dirname(os.path.abspath(__file__))
# database_uri = "sqlite:///{}".format(os.path.join(project_dir, "mini_wallet.db"))

database_uri = "postgresql+psycopg2://mydbuser:mydbpassword@localhost/mydb"
app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
db = SQLAlchemy(app)


@app.before_first_request
def initialize_db():
    for key, value in app.config.items():
        app.logger.info("{key}: {value}".format(key=key, value=value))

    # app.logger.info("dropping DB")
    # app.logger.info("-" * 80)
    # db.drop_all()
    # app.logger.info("DB droppped")
    # app.logger.info("-" * 80)

    app.logger.info("creating DB")
    app.logger.info("-" * 80)
    db.create_all()
    app.logger.info("DB created")
    app.logger.info("-" * 80)


# https://stackoverflow.com/questions/31584974/sqlalchemy-model-django-like-save-method
class Customer(db.Model):
    __tablename__ = "customer"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=func.now())

    xid = db.Column(
        db.Text, unique=True, nullable=False
    )  # 93de1727-943d-443e-b311-0da531a267a7
    token = db.Column(db.Text, unique=True, nullable=False)

    wallet = db.relationship("Wallet", uselist=False, back_populates="customer")


class Wallet(db.Model):
    __tablename__ = "wallet"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now())

    xid = db.Column(db.Text, nullable=False)  # 93de1727-943d-443e-b311-0da531a267a7
    balance = db.Column(db.Numeric, default=0, nullable=False)
    status = db.Column(db.Text, default="enabled", nullable=False)

    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    customer = db.relationship("Customer", back_populates="wallet")

    balance_change = db.relationship("BalanceChange", back_populates="wallet")
    status_change = db.relationship("StatusChange", back_populates="wallet")


class BalanceChange(db.Model):
    __tablename__ = "balance_change"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=func.now())

    xid = db.Column(db.Text, nullable=False)  # 93de1727-943d-443e-b311-0da531a267a7
    amount = db.Column(db.Numeric, nullable=False)
    reference_id = db.Column(db.Text, unique=True, nullable=False)
    type = db.Column(db.Text, nullable=False)

    wallet_id = db.Column(db.Integer, db.ForeignKey("wallet.id"))
    wallet = db.relationship("Wallet", back_populates="balance_change")


class StatusChange(db.Model):
    __tablename__ = "status_change"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=func.now())

    status = db.Column(db.Text, nullable=False)

    wallet_id = db.Column(db.Integer, db.ForeignKey("wallet.id"))
    wallet = db.relationship("Wallet", back_populates="status_change")


################################################################################


# service layer logger
logger = logging.getLogger(__name__)


@contextmanager
def enter_session():
    """Provide a transactional scope around a series of operations."""
    session = db.session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.exception("commit to DB fails")
        raise e
    finally:
        session.close()


class MiniWalletException(Exception):
    def __init__(self, *args):
        super().__init__(*args)
        logger.error({"class": self.__class__.__name__, "args": args})


def get_customer_info_by_token(token):
    customer = db.session.query(Customer).filter(Customer.token == token).one_or_none()
    return customer.__dict__ if customer else None


def initialize_customer(customer_xid):
    token = secrets.token_hex(21)
    try:
        with enter_session() as session:
            customer = Customer(xid=customer_xid, token=token)
            session.add(customer)
    except exc.IntegrityError:
        raise MiniWalletException(
            "customer with customer_id={} already initialized".format(customer_xid)
        )
    return {"token": token}


def enable_or_create(customer_dict):
    customer_id = customer_dict["id"]
    wallet = (
        Wallet.query.options(joinedload(Wallet.customer))
        .filter_by(customer_id=customer_id)
        .one_or_none()
    )
    data = dict()
    if not wallet:
        with enter_session() as session:
            wallet_xid = str(uuid.uuid4())
            wallet = Wallet(xid=wallet_xid, customer_id=customer_id)
            session.add(wallet)

            status_change = StatusChange(wallet=wallet, status="enabled")
            session.add(status_change)
            session.flush()
            data["wallet"] = {
                "xid": wallet.xid,
                "customer": customer_dict["xid"],
                "status": wallet.status,
                "enabled_at": status_change.created_at,
                "balance": int(wallet.balance),
            }
    else:
        new_status = "enabled"
        if wallet.status == new_status:
            raise MiniWalletException(
                "wallet with wallet_id={} already enabled".format(wallet.id)
            )

        with enter_session() as session:
            wallet.status = new_status
            session.merge(wallet)
            status_change = StatusChange(wallet=wallet, status=new_status)
            session.add(status_change)
            session.flush()
            data["wallet"] = {
                "xid": wallet.xid,
                "customer": customer_dict["xid"],
                "status": wallet.status,
                "enabled_at": status_change.created_at,
                "balance": int(wallet.balance),
            }
    logger.debug(data)
    return data


def get_balance(customer_dict):
    customer_id = customer_dict["id"]
    wallet = (
        Wallet.query.options(joinedload(Wallet.customer))
        .filter_by(customer_id=customer_id)
        .one_or_none()
    )
    if not wallet:
        raise MiniWalletException(
            "wallet with customer_id={} not found".format(customer_id)
        )
    if wallet.status != "enabled":
        raise MiniWalletException(
            "wallet with wallet_id={} not enabled".format(wallet.id)
        )
    data = {
        "wallet": {
            "xid": wallet.xid,
            "customer": wallet.customer.xid,
            "status": wallet.status,
            "balance": int(wallet.balance),
        }
    }
    logger.debug(data)
    return data


def deposit_money(customer_dict, amount, reference_id):
    customer_id = customer_dict["id"]
    data = dict()

    if amount <= 0:
        raise MiniWalletException("amount={} must be positive".format(amount))
    wallet = (
        Wallet.query.filter_by(customer_id=customer_id)
        .with_for_update(of=Wallet)
        .options(joinedload(Wallet.customer))
        .one_or_none()
    )
    if not wallet:
        raise MiniWalletException(
            "wallet with customer_id={} not found".format(customer_id)
        )
    if wallet.status != "enabled":
        raise MiniWalletException(
            "wallet with wallet_id={} not enabled".format(wallet.id)
        )
    try:
        with enter_session() as session:
            wallet.balance = wallet.balance + amount
            session.merge(wallet)
            balance_change_xid = str(uuid.uuid4())
            balance_change = BalanceChange(
                xid=balance_change_xid,
                amount=amount,
                reference_id=reference_id,
                wallet=wallet,
                type="deposit",
            )
            session.add(balance_change)
            data["deposit"] = {
                "xid": balance_change.xid,
                "wallet": wallet.xid,
                "status": "completed",
                "deposited_at": balance_change.created_at,
                "amount": amount,
                "reference_id": reference_id,
            }
    except exc.IntegrityError:
        raise MiniWalletException(
            "deposit fails duplicate reference_id={}".format(reference_id)
        )
    logger.debug(data)
    return data


def withdraw_money(customer_dict, amount, reference_id):
    customer_id = customer_dict["id"]
    data = dict()

    if amount <= 0:
        raise MiniWalletException("amount={} must be positive".format(amount))
    wallet = (
        Wallet.query.filter_by(customer_id=customer_id)
        .with_for_update(of=Wallet)
        .options(joinedload(Wallet.customer))
        .one_or_none()
    )
    if not wallet:
        raise MiniWalletException(
            "wallet with customer_id={} not found".format(customer_id)
        )
    if wallet.status != "enabled":
        raise MiniWalletException(
            "wallet with wallet_id={} not enabled".format(wallet.id)
        )
    if amount > wallet.balance:
        raise MiniWalletException(
            "insufficient fund to withdraw amount={} for wallet_id={}".format(
                amount, wallet.id
            )
        )
    try:
        with enter_session() as session:
            wallet.balance = wallet.balance - amount
            session.merge(wallet)
            balance_change_xid = str(uuid.uuid4())
            balance_change = BalanceChange(
                xid=balance_change_xid,
                amount=amount,
                reference_id=reference_id,
                wallet=wallet,
                type="withdrawal",
            )
            session.add(balance_change)
            data["withdrawal"] = {
                "xid": balance_change.xid,
                "wallet": wallet.xid,
                "status": "completed",
                "deposited_at": balance_change.created_at,
                "amount": amount,
                "reference_id": reference_id,
            }
    except exc.IntegrityError:
        raise MiniWalletException(
            "withdrawal fails duplicate reference_id={}".format(reference_id)
        )
    return data


def disable_wallet(customer_dict):
    customer_id = customer_dict["id"]
    data = dict()
    new_status = "disabled"

    wallet = (
        Wallet.query.filter_by(customer_id=customer_id)
        .with_for_update(of=Wallet)
        .options(joinedload(Wallet.customer))
        .one_or_none()
    )
    if not wallet:
        raise MiniWalletException(
            "wallet with customer_id={} not found".format(customer_id)
        )
    if wallet.status == new_status:
        raise MiniWalletException(
            "wallet with wallet_id={} already disabled".format(wallet.id)
        )

    with enter_session() as session:
        wallet.status = new_status
        session.merge(wallet)
        status_change = StatusChange(wallet=wallet, status=new_status)
        session.add(status_change)
        session.flush()
        data["wallet"] = {
            "xid": wallet.xid,
            "customer": wallet.customer.xid,
            "status": wallet.status,
            "disabled_at": status_change.created_at,
        }
    return data


################################################################################


def create_failed_response(error_message, status_code=400, headers=None):
    if headers:
        return jsend.fail({"error": error_message}), status_code, headers
    else:
        return jsend.fail({"error": error_message}), status_code


# https://webargs.readthedocs.io/en/latest/framework_support.html#error-handling
@app.errorhandler(422)
@app.errorhandler(400)
def handle_error_400(err):
    error_code = 400 if err.code == 422 else err.code
    headers = err.data.get("headers", None)
    messages = err.data.get("messages", ["Invalid request."])
    return create_failed_response(messages, error_code, headers=headers)


@app.errorhandler(Exception)
def handle_error_500(exception):
    if isinstance(exception, MiniWalletException):
        return create_failed_response(str(exception), 400)
    return create_failed_response(str(exception), 500)


def validate_token(f):
    @wraps(f)
    def wrap(*args, **kwargs):

        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Token "):
            app.logger.info(authorization)
            return create_failed_response(
                "Incorrect Authorization signature: 'Token <my token>'", 401
            )

        _, token = authorization.split(" ")
        customer_dict = get_customer_info_by_token(token)
        if not customer_dict:
            return create_failed_response(
                "Incorrect Authorization signature: 'Token <my token>'", 401
            )

        kwargs["customer_dict"] = customer_dict
        return f(*args, **kwargs)

    return wrap


################################################################################


@app.route("/api/v1/init", methods=["POST"])
@use_args({"customer_xid": fields.Str(required=True, validate=lambda cx: len(cx) > 0)})
def initialize(args):
    data = initialize_customer(args["customer_xid"])
    return jsend.success(data), 201


@app.route("/api/v1/wallet", methods=["POST"])
@validate_token
def enable(customer_dict):
    data = enable_or_create(customer_dict)
    return jsend.success(data), 201


@app.route("/api/v1/wallet", methods=["GET"])
@validate_token
def view(customer_dict):
    data = get_balance(customer_dict)
    return jsend.success(data), 200


@app.route("/api/v1/wallet/deposits", methods=["POST"])
@use_args(
    {
        "amount": fields.Integer(required=True, validate=lambda amount: amount > 0),
        "reference_id": fields.Str(required=True, validate=lambda ri: len(ri) > 0),
    }
)
@validate_token
def deposit(args, customer_dict):
    data = deposit_money(customer_dict, args["amount"], args["reference_id"])
    return jsend.success(data), 201


@app.route("/api/v1/wallet/withdrawals", methods=["POST"])
@use_args(
    {
        "amount": fields.Integer(required=True, validate=lambda amount: amount > 0),
        "reference_id": fields.Str(required=True, validate=lambda ri: len(ri) > 0),
    }
)
@validate_token
def withdraw(args, customer_dict):
    data = withdraw_money(customer_dict, args["amount"], args["reference_id"])
    return jsend.success(data), 201


@app.route("/api/v1/wallet", methods=["PATCH"])
@use_args({"is_disabled": fields.Bool(required=True, validate=lambda v: v is True)})
@validate_token
def disable(args, customer_dict):
    data = disable_wallet(customer_dict)
    return jsend.success(data), 201
