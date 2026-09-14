from demo_app.app import app


def test_dashboard_exposes_independent_operations():
    client = app.test_client()
    page = client.get("/")
    assert page.status_code == 200
    assert b"Member Lookup" in page.data
    assert b"Balance Lookup" in page.data
    assert b"Create Sub-account" in page.data
    assert b"Deposit" in page.data


def test_subaccount_review_does_not_commit():
    client = app.test_client()
    review = client.post(
        "/sub-account/review",
        data={
            "member_id": "10023",
            "account_type": "Holiday Savings",
            "nickname": "Vacation",
        },
    )
    assert review.status_code == 200
    assert b"Review New Sub-account" in review.data
    assert b"No account has been opened" in review.data
    assert client.post("/sub-account/commit").status_code == 403


def test_deposit_review_does_not_change_balance():
    client = app.test_client()
    review = client.post(
        "/deposit/review",
        data={
            "member_id": "10024",
            "account_type": "Savings",
            "amount": "200.00",
            "memo": "Cash deposit",
        },
    )
    assert review.status_code == 200
    assert b"Deposit Review" in review.data
    assert b"No funds have been posted" in review.data
    assert b"$200.00" in review.data
    assert client.post("/deposit/commit").status_code == 403


def test_invalid_deposit_is_rejected():
    client = app.test_client()
    review = client.post(
        "/deposit/review",
        data={
            "member_id": "10024",
            "account_type": "Savings",
            "amount": "NaN",
        },
    )
    assert b"Deposit must be between" in review.data


if __name__ == "__main__":
    test_dashboard_exposes_independent_operations()
    test_subaccount_review_does_not_commit()
    test_deposit_review_does_not_change_balance()
    test_invalid_deposit_is_rejected()
    print("4/4 multi-operation portal tests passed")
