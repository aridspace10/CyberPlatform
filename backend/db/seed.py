import json
import os
import secrets

from db.authentication import hash_password, verify_password
from db.modals import Scenario, User
from sqlalchemy.orm import Session

CONFIG_FOLDER = "./game/configs"


def seed_db(db: Session, *, local_dev_login: bool = False):
    # Only the localhost development runner enables the old quick-login account.
    legacy_user = db.query(User).filter_by(username="jack").first()
    try:
        has_default_password = bool(
            legacy_user
            and legacy_user.password
            and verify_password("1234", legacy_user.password)
        )
    except ValueError:
        has_default_password = False
    if local_dev_login and legacy_user is None:
        db.add(
            User(username="jack", email="jackovand27", password=hash_password("1234"))
        )
    elif local_dev_login and not has_default_password:
        legacy_user.password = hash_password("1234")
    elif not local_dev_login and has_default_password:
        legacy_user.password = hash_password(secrets.token_urlsafe(48))

    ## ADD CONFIGS ##
    for filename in os.listdir(CONFIG_FOLDER):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(CONFIG_FOLDER, filename)

        with open(path) as f:
            config_data = json.load(f)

        # Check if scenario already exists (by name or filename)
        exists = db.query(Scenario).filter_by(name=config_data["name"]).first()

        if not exists:
            scenario = Scenario(
                name=config_data["name"], config=json.dumps(config_data)
            )
            db.add(scenario)

    db.commit()
