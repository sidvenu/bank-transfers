from datetime import datetime
import time
import uuid

from flask import Flask, g, request
import sqlite3

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

DATABASE = "main.db"


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.route("/init-db", methods=["POST"])
def init_db():
    conn = get_db()
    cur = conn.cursor()
    with open("init_data.sql") as f:
        cur.executescript(f.read())
    cur.close()
    conn.commit()
    return {"message": "Database initialized successfully"}


txn_initiate_ts = {}
last_remove_old_initiates_ts = 0


def remove_old_initiates():
    cur_ts = int(time.time())
    # dont run this function more than once per 60 seconds
    if cur_ts < last_remove_old_initiates_ts + 60:
        return
    for k, v in txn_initiate_ts.items():
        # remove items older than 60 seconds
        if cur_ts > v + 60:
            txn_initiate_ts.pop(k, None)


def get_balances(cur, accounts):
    if len(accounts) == 0:
        return {}, 0

    bal_res = cur.execute(
        f"select * from balances where account_no in ({','.join(['?']*len(accounts))})",
        accounts,
    ).fetchall()

    bal = {}
    for r in bal_res:
        r = dict(r)
        bal[r["account_no"]] = r["balance"]

    return bal, len(bal_res)


@app.route("/transfer", methods=["POST"])
def transfer():
    initiate_ts = int(time.time())
    post_data = request.get_json()

    if post_data is None:
        return {"message": "Required parameters not passed"}, 400

    acc_from = post_data.get("from", "")
    acc_to = post_data.get("to", "")
    amount = post_data.get("amount", 0)

    txn_temp_id = f"{acc_from}#{amount}"
    # if a similar transaction has been initiated less than 5 seconds ago, prevent this initiate from happening
    if (
        txn_temp_id in txn_initiate_ts
        and txn_initiate_ts[txn_temp_id] >= initiate_ts - 5
    ):
        return {
            "message": "Too many transactions with same amount at a short time"
        }, 429

    txn_initiate_ts[txn_temp_id] = initiate_ts
    remove_old_initiates()

    if (
        (type(acc_from) != str or acc_from == "")
        or (type(acc_to) != str or acc_to == "")
        or (type(amount) != int or amount <= 0)
    ):
        return {"message": "Required parameters not passed/invalid"}, 400

    conn = get_db()
    cur = conn.cursor()

    # get balances for from and to accounts
    bal, len_bal = get_balances(cur, [acc_from, acc_to])

    # check validity of both the accounts
    if len_bal < 2:
        return {"message": "Account(s) not found"}, 400

    if bal[acc_from] < amount:
        return {"message": "Balance is not enough to cover this transaction"}, 400

    # we transfer money from the account even if the balance has changed due to another concurrent API call,
    # PROVIDED the account still has balance left
    cur.execute(
        """
    update balances
    set balance=balance-?
    where account_no=? and balance>=?
    """,
        [amount, acc_from, amount],
    )

    if cur.rowcount <= 0:
        return {"message": "Balance is not enough to cover this transaction"}, 400

    # we don't care if the account where money is being sent to has the same balance as initially
    # or not, since all accounts regardless of their current balance can receive money.
    # This enables an account to concurrently receive money from multiple people
    cur.execute(
        """
    update balances
    set balance=balance+?
    where account_no=?
    """,
        [amount, acc_to],
    )

    # get the new balances of both the accounts
    bal, len_bal = get_balances(cur, [acc_from, acc_to])

    txn_id = str(uuid.uuid4())
    complete_ts = int(time.time())

    cur.execute(
        """
    insert into transactions
    (id, amount, account_no, initiate_ts, complete_ts)
    values (?,?,?,?,?)
    """,
        [txn_id, amount, acc_from, initiate_ts, complete_ts],
    )
    cur.close()
    conn.commit()

    return {
        "id": txn_id,
        "from": {"id": acc_from, "balance": bal[acc_from]},
        "to": {"id": acc_to},
        "amount": amount,
        "initiate_datetime": datetime.utcfromtimestamp(initiate_ts).isoformat() + "Z",
        "complete_datetime": datetime.utcfromtimestamp(complete_ts).isoformat() + "Z",
    }


@app.teardown_appcontext
def close_connection(_):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


if __name__ == "__main__":
    app.run()
