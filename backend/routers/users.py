from datetime import datetime, timedelta, timezone

from db.authentication import (
    LoginRequest,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from db.modals import (
    Friendship,
    GameSession,
    SessionShell,
    User,
    UserBlock,
    UserRateLimit,
)
from db.session import SessionLocal
from fastapi import APIRouter, Depends, HTTPException, Request
from network.SessionManger import session_manager
from pydantic import BaseModel
from services.auth_rate_limit import enforce_auth_rate_limit
from services.user_service import friendship_between
from sqlalchemy import or_, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class AccountProfile(BaseModel):
    id: int
    username: str
    email: str


class FriendRequestCreate(BaseModel):
    user_id: int


router = APIRouter(prefix="/users", tags=["users"])

SEARCH_LIMIT = 30
REQUEST_LIMIT = 10
REQUEST_COOLDOWN = timedelta(hours=24)
MAX_OUTGOING_PENDING = 10


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def enforce_limit(db: Session, user_id: int, action: str, window: int, limit: int):
    now = int(datetime.now(timezone.utc).timestamp())
    bucket = now // window
    statement = (
        sqlite_insert(UserRateLimit)
        .values(user_id=user_id, action=action, bucket=bucket, count=1)
        .on_conflict_do_update(
            index_elements=["user_id", "action", "bucket"],
            set_={"count": UserRateLimit.count + 1},
        )
        .returning(UserRateLimit.count)
    )
    count = db.execute(statement).scalar_one()
    db.query(UserRateLimit).filter(
        UserRateLimit.user_id == user_id,
        UserRateLimit.action == action,
        UserRateLimit.bucket < bucket - 2,
    ).delete(synchronize_session=False)
    db.commit()
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(window - now % window)},
        )


def blocked_between(db: Session, user_id: int, other_id: int) -> bool:
    return (
        db.query(UserBlock.id)
        .filter(
            or_(
                (UserBlock.blocker_id == user_id) & (UserBlock.blocked_id == other_id),
                (UserBlock.blocker_id == other_id) & (UserBlock.blocked_id == user_id),
            )
        )
        .first()
        is not None
    )


def unavailable_request():
    raise HTTPException(status_code=409, detail="Friend request unavailable")


def begin_write(db: Session):
    # SQLite serializes these read/modify/write paths across API workers.
    db.execute(text("BEGIN IMMEDIATE"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/me", response_model=AccountProfile)
def get_me(user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found")

    return user


def public_user(user: User) -> dict:
    return {"id": user.id, "username": user.username}


@router.get("/search")
def search_users(
    query: str = "",
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = query.strip()
    if not query:
        return []
    enforce_limit(db, user_id, "friend_search", 60, SEARCH_LIMIT)
    if len(query) < 2 or len(query) > 32:
        raise HTTPException(status_code=400, detail="Search needs 2 to 32 characters")
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    hidden_ids = [
        item[0]
        for item in db.query(UserBlock.blocked_id).filter(
            UserBlock.blocker_id == user_id
        )
    ]
    hidden_ids += [
        item[0]
        for item in db.query(UserBlock.blocker_id).filter(
            UserBlock.blocked_id == user_id
        )
    ]
    users = (
        db.query(User)
        .filter(
            User.id != user_id,
            User.id.notin_(hidden_ids),
            User.username.ilike(f"%{escaped}%", escape="\\"),
        )
        .order_by(User.username)
        .limit(20)
        .all()
    )
    return [public_user(user) for user in users]


@router.get("/me/friends")
def get_friends(
    user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    friendships = (
        db.query(Friendship)
        .filter(
            Friendship.status == "accepted",
            or_(
                Friendship.requester_id == user_id,
                Friendship.recipient_id == user_id,
            ),
        )
        .all()
    )
    friend_ids = [
        (
            friendship.recipient_id
            if friendship.requester_id == user_id
            else friendship.requester_id
        )
        for friendship in friendships
    ]
    if not friend_ids:
        return []
    users = db.query(User).filter(User.id.in_(friend_ids)).order_by(User.username).all()
    return [public_user(user) for user in users]


@router.get("/me/friend-requests")
def get_friend_requests(
    user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    requests = (
        db.query(Friendship)
        .filter(
            Friendship.status == "pending",
            or_(
                Friendship.requester_id == user_id,
                Friendship.recipient_id == user_id,
            ),
        )
        .order_by(Friendship.id)
        .all()
    )
    incoming, outgoing = [], []
    for request in requests:
        other_id = (
            request.requester_id
            if request.recipient_id == user_id
            else request.recipient_id
        )
        other = db.get(User, other_id)
        if other is None:
            continue
        entry = {"id": request.id, "user": public_user(other)}
        (incoming if request.recipient_id == user_id else outgoing).append(entry)
    return {"incoming": incoming, "outgoing": outgoing}


@router.post("/me/friend-requests", status_code=201)
def send_friend_request(
    data: FriendRequestCreate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_limit(db, user_id, "friend_request", 3600, REQUEST_LIMIT)
    if data.user_id == user_id:
        raise HTTPException(status_code=400, detail="You cannot add yourself")
    begin_write(db)
    other = db.get(User, data.user_id)
    if other is None or blocked_between(db, user_id, data.user_id):
        unavailable_request()
    existing = friendship_between(db, user_id, data.user_id)
    if existing is not None:
        if existing.status not in ("declined", "cancelled") or (
            existing.declined_at is None
            or utc_now() - existing.declined_at < REQUEST_COOLDOWN
        ):
            unavailable_request()
    outgoing = (
        db.query(Friendship)
        .filter(Friendship.requester_id == user_id, Friendship.status == "pending")
        .count()
    )
    if outgoing >= MAX_OUTGOING_PENDING:
        unavailable_request()
    if existing is None:
        request = Friendship(requester_id=user_id, recipient_id=data.user_id)
        db.add(request)
    else:
        request = existing
        request.requester_id = user_id
        request.recipient_id = data.user_id
        request.status = "pending"
        request.declined_at = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        unavailable_request()
    db.refresh(request)
    return {"id": request.id, "user": public_user(other), "status": request.status}


@router.post("/me/friend-requests/{request_id}/accept")
def accept_friend_request(
    request_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    begin_write(db)
    request = db.get(Friendship, request_id)
    if request is None or request.status != "pending":
        raise HTTPException(status_code=404, detail="Friend request not found")
    if request.recipient_id != user_id:
        raise HTTPException(status_code=403, detail="Only the recipient can accept")
    changed = (
        db.query(Friendship)
        .filter(
            Friendship.id == request_id,
            Friendship.recipient_id == user_id,
            Friendship.status == "pending",
        )
        .update({Friendship.status: "accepted"}, synchronize_session=False)
    )
    if not changed:
        db.rollback()
        raise HTTPException(status_code=404, detail="Friend request not found")
    db.commit()
    db.refresh(request)
    requester = db.get(User, request.requester_id)
    return {
        "id": request.id,
        "user": public_user(requester),
        "status": request.status,
    }


@router.delete("/me/friend-requests/{request_id}")
def delete_friend_request(
    request_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    begin_write(db)
    request = db.get(Friendship, request_id)
    if request is None or request.status != "pending":
        raise HTTPException(status_code=404, detail="Friend request not found")
    if user_id not in (request.requester_id, request.recipient_id):
        raise HTTPException(status_code=403, detail="Not your friend request")
    changed = (
        db.query(Friendship)
        .filter(Friendship.id == request_id, Friendship.status == "pending")
        .update(
            {
                Friendship.status: "declined"
                if user_id == request.recipient_id
                else "cancelled",
                Friendship.declined_at: utc_now(),
            },
            synchronize_session=False,
        )
    )
    if not changed:
        db.rollback()
        raise HTTPException(status_code=404, detail="Friend request not found")
    db.commit()
    return {"message": "Friend request removed"}


@router.get("/me/blocks")
def get_blocks(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    blocked_ids = [
        row[0]
        for row in db.query(UserBlock.blocked_id).filter(
            UserBlock.blocker_id == user_id
        )
    ]
    return [
        public_user(user)
        for user in db.query(User)
        .filter(User.id.in_(blocked_ids))
        .order_by(User.username)
    ]


@router.post("/me/blocks")
async def block_user(
    data: FriendRequestCreate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.user_id == user_id:
        raise HTTPException(status_code=400, detail="You cannot block yourself")
    begin_write(db)
    other = db.get(User, data.user_id)
    if other is None:
        raise HTTPException(status_code=404, detail="User not found")
    existing = (
        db.query(UserBlock)
        .filter_by(blocker_id=user_id, blocked_id=data.user_id)
        .first()
    )
    if existing is None:
        db.add(UserBlock(blocker_id=user_id, blocked_id=data.user_id))
    friendship = friendship_between(db, user_id, data.user_id)
    affected_sessions = (
        private_sessions_for_pair(db, user_id, data.user_id)
        if friendship and friendship.status == "accepted"
        else []
    )
    if friendship is not None:
        db.delete(friendship)
    for session in affected_sessions:
        removed_id = data.user_id if session.creatorID == user_id else user_id
        shell = db.get(SessionShell, (session.id, removed_id))
        if shell is not None:
            db.delete(shell)
    db.commit()
    await disconnect_private_sessions(affected_sessions, user_id, data.user_id)
    return {"message": "User blocked"}


@router.delete("/me/blocks/{blocked_id}")
def unblock_user(
    blocked_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(UserBlock).filter_by(blocker_id=user_id, blocked_id=blocked_id).delete()
    db.commit()
    return {"message": "User unblocked"}


def private_sessions_for_pair(db: Session, user_id: int, friend_id: int):
    return (
        db.query(GameSession)
        .filter(
            GameSession.visibility == "friends_only",
            GameSession.creatorID.in_((user_id, friend_id)),
        )
        .all()
    )


async def disconnect_private_sessions(sessions, user_id: int, friend_id: int):
    for session in sessions:
        removed_id = friend_id if session.creatorID == user_id else user_id
        runtime = session_manager.get_session(str(session.id))
        if runtime == "404":
            continue
        for websocket, username in list(runtime.connections.items()):
            player = runtime.players.get(username)
            if player is not None and int(player.user_id) == removed_id:
                try:
                    await websocket.close(code=4403)
                except Exception:
                    pass
                await runtime.disconnect(websocket)
        for username, player in list(runtime.players.items()):
            if int(player.user_id) == removed_id:
                runtime.players.pop(username)
        await runtime.broadcast_game_state()


@router.delete("/me/friends/{friend_id}")
async def remove_friend(
    friend_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    begin_write(db)
    friendship = friendship_between(db, user_id, friend_id)
    if friendship is None or friendship.status != "accepted":
        raise HTTPException(status_code=404, detail="Friend not found")
    affected_sessions = private_sessions_for_pair(db, user_id, friend_id)
    db.delete(friendship)
    for session in affected_sessions:
        removed_id = friend_id if session.creatorID == user_id else user_id
        shell = db.get(SessionShell, (session.id, removed_id))
        if shell is not None:
            db.delete(shell)
    db.commit()
    await disconnect_private_sessions(affected_sessions, user_id, friend_id)
    return {"message": "Friend removed"}


@router.post("/login")
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    enforce_auth_rate_limit(db, request, "login", data.username)
    user = db.query(User).filter(User.username == data.username).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id, "username": user.username})

    return {"access_token": token}


# CREATE USER
@router.post("/", status_code=201)
def create_user(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    enforce_auth_rate_limit(db, request, "signup")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=409, detail="Username is already taken")

    hpassword = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, password=hpassword)

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Username is already taken"
        ) from exc
    db.refresh(new_user)

    return {"id": new_user.id, "username": new_user.username, "email": new_user.email}


# GET USERS
@router.get("/")
def get_users(_user_id: int = Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Use friend search")


@router.get("/{user_id}")
def get_user(
    user_id: int,
    _current_user_id: int = Depends(get_current_user),
):
    raise HTTPException(status_code=410, detail="Use friend search")


# UPDATE USER
@router.put("/{user_id}")
def update_user(
    user_id: int,
    username: str,
    email: str,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=403, detail="You can only update your own account"
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if db.query(User).filter(User.username == username, User.id != user_id).first():
        raise HTTPException(status_code=409, detail="Username already in use")

    user.username = username
    user.email = email

    db.commit()
    db.refresh(user)

    return {"id": user.id, "username": user.username, "email": user.email}


# DELETE USER
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=403, detail="You can only delete your own account"
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"message": "deleted"}
