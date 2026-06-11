import os
import json
from sqlalchemy.orm import Session
from db.modals import Scenario, User
from db.authentication import hash_password

CONFIG_FOLDER = "./game/configs"


def seed_db(db: Session):
    ## ADD BASE USER ##
    exists = db.query(User).filter_by(username="jack").first()

    if not exists:
        user = User(
            username="jack", email="jackovand27", password=hash_password("1234")
        )
        db.add(user)
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
