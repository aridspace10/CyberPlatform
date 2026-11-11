from db.modals import Friendship, User
from sqlalchemy import or_
from sqlalchemy.orm import Session


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def friendship_between(db: Session, user_id: int, other_id: int) -> Friendship | None:
    return (
        db.query(Friendship)
        .filter(
            or_(
                (Friendship.requester_id == user_id)
                & (Friendship.recipient_id == other_id),
                (Friendship.requester_id == other_id)
                & (Friendship.recipient_id == user_id),
            )
        )
        .first()
    )


def is_friend(db: Session, user_id: int, other_id: int) -> bool:
    relationship = friendship_between(db, user_id, other_id)
    return relationship is not None and relationship.status == "accepted"
