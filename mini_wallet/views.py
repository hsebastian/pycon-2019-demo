import jsend
import logging

from flask import Flask
from flask import request

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username


@app.route("/")
def hello_world():
    return jsend.success({"message": "Hello, World!"})


@app.route("/api/v1/wallet", methods=["POST"])
def enable():
    authorization = request.headers.get("Authorization")
    if "Token" in authorization:
        return jsend.fail({"error": "Already enabled"}), 400

    data = {"wallet": {
      "id": "6ef31ed3-f396-4b6c-8049-674ddede1b16",
      "owned_by": "c4d7d61f-b702-44a8-af97-5dbdafa96551",
      "status": "enabled",
      "enabled_at": "1994-11-05T08:15:30-05:00",
      "balance": 0
    }}
    logging.info(data)
    return jsend.success(data), 201


@app.route("/api/v1/wallet", methods=["PATCH"])
def disable():
    authorization = request.headers.get("Authorization")
    is_disabled = request.form.get("is_disabled")
    assert False


@app.route("/api/v1/wallet", methods=["GET"])
def view():
    authorization = request.headers.get("Authorization")
    assert False


@app.route("/api/v1/wallet/deposits", methods=["POST"])
def deposit():
    authorization = request.headers.get("Authorization")
    amount = request.form.get("amount")
    reference_id = request.form.get("reference_id")
    assert False


@app.route("/api/v1/wallet/withdrawals", methods=["POST"])
def withdraw():
    authorization = request.headers.get("Authorization")
    amount = request.form.get("amount")
    reference_id = request.form.get("reference_id")
    assert False


################################################################################


def enable_or_create(customer_id):
    pass


def disable():
    pass