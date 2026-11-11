from db.authentication import (
    LoginRequest,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from db.modals import Friendship, GameSession, SessionShell, User
from db.session import SessionLocal
from fastapi import APIRouter, Depends, HTTPException
from network.SessionManger import session_manager
from pydantic import BaseModel
from services.user_service import friendship_between
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class FriendRequestCreate(BaseModel):
    user_id: int


router = APIRouter(prefix="/users", tags=["users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/me")
def get_me(user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return

    return {"id": user.id, "username": user.username}


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
    users = (
        db.query(User)
        .filter(User.id != user_id, User.username.ilike(f"%{query}%"))
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
        friendship.recipient_id
        if friendship.requester_id == user_id
        else friendship.requester_id
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
    if data.user_id == user_id:
        raise HTTPException(status_code=400, detail="You cannot add yourself")
    other = db.get(User, data.user_id)
    if other is None:
        raise HTTPException(status_code=404, detail="User not found")
    existing = friendship_between(db, user_id, data.user_id)
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="Friend relationship already exists"
        )
    request = Friendship(requester_id=user_id, recipient_id=data.user_id)
    db.add(request)
    db.commit()
    db.refresh(request)
    return {"id": request.id, "user": public_user(other), "status": request.status}


@router.post("/me/friend-requests/{request_id}/accept")
def accept_friend_request(
    request_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    request = db.get(Friendship, request_id)
    if request is None or request.status != "pending":
        raise HTTPException(status_code=404, detail="Friend request not found")
    if request.recipient_id != user_id:
        raise HTTPException(status_code=403, detail="Only the recipient can accept")
    request.status = "accepted"
    db.commit()
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
    request = db.get(Friendship, request_id)
    if request is None or request.status != "pending":
        raise HTTPException(status_code=404, detail="Friend request not found")
    if user_id not in (request.requester_id, request.recipient_id):
        raise HTTPException(status_code=403, detail="Not your friend request")
    db.delete(request)
    db.commit()
    return {"message": "Friend request removed"}


@router.delete("/me/friends/{friend_id}")
async def remove_friend(
    friend_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendship = friendship_between(db, user_id, friend_id)
    if friendship is None or friendship.status != "accepted":
        raise HTTPException(status_code=404, detail="Friend not found")
    affected_sessions = (
        db.query(GameSession)
        .filter(
            GameSession.visibility == "friends_only",
            GameSession.creatorID.in_((user_id, friend_id)),
        )
        .all()
    )
    db.delete(friendship)
    for session in affected_sessions:
        removed_id = friend_id if session.creatorID == user_id else user_id
        shell = db.get(SessionShell, (session.id, removed_id))
        if shell is not None:
            db.delete(shell)
    db.commit()
    for session in affected_sessions:
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
    return {"message": "Friend removed"}


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id, "username": user.username})

    return {"access_token": token}


# CREATE USER
@router.post("/", status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=409, detail="Username is already taken")

    hpassword = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, password=hpassword)

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username is already taken") from exc
    db.refresh(new_user)

    return {"id": new_user.id, "username": new_user.username, "email": new_user.email}


# GET USERS
@router.get("/")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    return db.query(User).filter(User.id == user_id).first()


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

    return user


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
