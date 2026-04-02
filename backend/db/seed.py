import os
import json
from sqlalchemy.orm import Session
from db.modals import Scenario

CONFIG_FOLDER = "./game/configs"

def seed_db(db: Session):
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
                name=config_data["name"],
                config=json.dumps(config_data)
            )
            db.add(scenario)

    db.commit()
