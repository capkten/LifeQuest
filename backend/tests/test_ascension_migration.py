from app.models.immortal import AscensionRecord, CrossRealmSettlement, ImmortalProfile


def test_existing_user_keeps_mortal_profile_without_immortal_row(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={"username": "mortal_before_ascension", "email": "mortal-before@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 200

    from app.models.user import User

    user = db_session.query(User).filter_by(username="mortal_before_ascension").one()
    assert db_session.query(ImmortalProfile).filter_by(user_id=user.id).count() == 0
    assert db_session.query(AscensionRecord).filter_by(user_id=user.id).count() == 0
    assert db_session.query(CrossRealmSettlement).filter_by(user_id=user.id).count() == 0


def test_immortal_tables_expose_unique_idempotency_constraints(db_session):
    assert {constraint.name for constraint in AscensionRecord.__table__.constraints if constraint.name} >= {
        "uq_ascension_record_request",
        "uq_ascension_record_user",
    }
    assert {constraint.name for constraint in CrossRealmSettlement.__table__.constraints if constraint.name} >= {
        "uq_cross_realm_request",
        "uq_cross_realm_user_source",
    }
