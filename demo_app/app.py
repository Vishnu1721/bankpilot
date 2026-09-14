from decimal import Decimal, InvalidOperation

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

MEMBERS = {
    "10023": {"name": "Alex Morgan", "checking": "1250.40", "savings": "4820.35", "requires_verification": False},
    "10024": {"name": "Jordan Lee", "checking": "845.10", "savings": "2150.75", "requires_verification": False},
    "10025": {"name": "Taylor Smith", "checking": "950.25", "savings": "3675.20", "requires_verification": True},
}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/member-search")
def member_search():
    return render_template("member_search.html")


@app.route("/member", methods=["POST"])
def find_member():
    member_id = request.form.get("member_id", "").strip()
    member = MEMBERS.get(member_id)
    if member is None:
        return render_template("member_search.html", error="Member not found")
    if member.get("requires_verification"):
        return render_template("verification.html", member_id=member_id, member=member)
    return render_template("member.html", member_id=member_id, member=member)


@app.route("/verify/<member_id>", methods=["POST"])
def verify_member(member_id):
    member = MEMBERS.get(member_id)
    if member is None:
        return redirect(url_for("home"))
    return render_template("member.html", member_id=member_id, member=member)


@app.route("/balance-lookup")
def balance_lookup():
    return render_template("balance_form.html")


@app.route("/balance", methods=["POST"])
def show_balance():
    member_id = request.form.get("member_id", "").strip()
    account_type = request.form.get("account_type", "")
    member = MEMBERS.get(member_id)
    key = {"Checking": "checking", "Savings": "savings"}.get(account_type)
    if member is None or key is None:
        return render_template("balance_form.html", error="Member or account type is invalid.")
    return render_template(
        "balance_result.html",
        member_id=member_id,
        member=member,
        account_type=account_type,
        balance=member[key],
    )


@app.route("/sub-account")
def subaccount_start():
    return render_template("subaccount_form.html")


@app.route("/sub-account/<member_id>")
def new_subaccount(member_id):
    member = MEMBERS.get(member_id)
    if member is None:
        return redirect(url_for("home"))
    return render_template("subaccount_form.html", member_id=member_id, member=member)


@app.route("/sub-account/review", methods=["POST"])
def review_subaccount():
    member_id = request.form.get("member_id", "").strip()
    member = MEMBERS.get(member_id)
    account_type = request.form.get("account_type", "")
    nickname = request.form.get("nickname", "").strip()
    if member is None:
        return render_template("subaccount_form.html", error="Member not found.")
    if account_type not in {"Holiday Savings", "Money Market", "Certificate"}:
        return render_template(
            "subaccount_form.html",
            member_id=member_id,
            member=member,
            error="Choose a valid account type.",
        )
    return render_template(
        "subaccount_review.html",
        member_id=member_id,
        member=member,
        account_type=account_type,
        nickname=nickname or "No nickname",
    )


@app.route("/sub-account/commit", methods=["POST"])
def commit_subaccount():
    return "Commit disabled in the safe demo. A human must approve account creation.", 403


@app.route("/deposit")
def deposit_start():
    return render_template("deposit_form.html")


@app.route("/deposit/review", methods=["POST"])
def review_deposit():
    member_id = request.form.get("member_id", "").strip()
    member = MEMBERS.get(member_id)
    account_type = request.form.get("account_type", "")
    amount_text = request.form.get("amount", "").strip()
    memo = request.form.get("memo", "").strip()

    try:
        amount = Decimal(amount_text)
    except InvalidOperation:
        amount = Decimal("0")

    if member is None:
        return render_template("deposit_form.html", error="Member not found.")
    if account_type not in {"Checking", "Savings"}:
        return render_template("deposit_form.html", error="Choose a valid destination account.")
    if not amount.is_finite() or amount <= 0 or amount > Decimal("10000"):
        return render_template("deposit_form.html", error="Deposit must be between $0.01 and $10,000.")

    return render_template(
        "deposit_review.html",
        member_id=member_id,
        member=member,
        account_type=account_type,
        amount=f"{amount:.2f}",
        memo=memo or "No memo",
    )


@app.route("/deposit/commit", methods=["POST"])
def commit_deposit():
    return "Posting disabled in the safe demo. A human must approve the deposit.", 403


if __name__ == "__main__":
    app.run(port=5001, debug=True)
