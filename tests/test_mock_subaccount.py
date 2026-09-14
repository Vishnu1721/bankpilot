from demo_app.app import app


def test_review_flow_does_not_commit():
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

    commit = client.post("/sub-account/commit")
    assert commit.status_code == 403


if __name__ == "__main__":
    test_review_flow_does_not_commit()
    print("Mock sub-account safety test passed")
