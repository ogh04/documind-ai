from conftest import login_test_user, register_test_user


def test_register_user_returns_created_user(client, registered_user_payload):
    response = register_test_user(
        client=client,
        user_payload=registered_user_payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["full_name"] == registered_user_payload["full_name"]
    assert data["email"] == registered_user_payload["email"]
    assert "created_at" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_login_user_returns_access_token(client, registered_user_payload):
    register_response = register_test_user(
        client=client,
        user_payload=registered_user_payload,
    )

    assert register_response.status_code == 201

    login_response = login_test_user(
        client=client,
        email=registered_user_payload["email"],
        password=registered_user_payload["password"],
    )

    assert login_response.status_code == 200

    data = login_response.json()

    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20


def test_login_user_with_wrong_password_returns_401(
    client,
    registered_user_payload,
):
    register_response = register_test_user(
        client=client,
        user_payload=registered_user_payload,
    )

    assert register_response.status_code == 201

    login_response = login_test_user(
        client=client,
        email=registered_user_payload["email"],
        password="wrong-password",
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Incorrect email or password"