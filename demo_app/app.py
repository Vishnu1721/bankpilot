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

@app.route("/member", methods=["POST"])
def find_member():
    member_id = request.form.get("member_id", "").strip()
    member = MEMBERS.get(member_id)
    if member is None:
        return render_template("index.html", error="Member not found")
    if member.get("requires_verification"):
        return render_template("verification.html", member_id=member_id, member=member)
    return render_template("member.html", member_id=member_id, member=member)

@app.route("/verify/<member_id>", methods=["POST"])
def verify_member(member_id):
    member = MEMBERS.get(member_id)
    if member is None:
        return redirect(url_for("home"))
    return render_template("member.html", member_id=member_id, member=member)

@app.route("/sub-account/<member_id>")
def new_subaccount(member_id):
    member = MEMBERS.get(member_id)
    if member is None:
        return redirect(url_for("home"))
    return render_template("subaccount_form.html", member_id=member_id, member=member)

@app.route("/sub-account/review", methods=["POST"])
def review_subaccount():
    member_id = request.form.get("member_id", "")
    member = MEMBERS.get(member_id)
    if member is None:
        return redirect(url_for("home"))
    account_type = request.form.get("account_type", "")
    nickname = request.form.get("nickname", "").strip()
    if account_type not in {"Holiday Savings", "Money Market", "Certificate"}:
        return render_template("subaccount_form.html", member_id=member_id, member=member, error="Choose a valid account type.")
    return render_template("subaccount_review.html", member_id=member_id, member=member, account_type=account_type, nickname=nickname or "No nickname")

@app.route("/sub-account/commit", methods=["POST"])
def commit_subaccount():
    return "Commit disabled in the safe demo. A human must approve consequential actions.", 403

if __name__ == "__main__":
    app.run(port=5001, debug=True)
