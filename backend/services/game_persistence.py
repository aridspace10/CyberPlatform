"""Atomic checkpoints for live game progress and player shell snapshots."""

from db.modals import GameSession as SavedSession
from db.modals import RoundState, SessionShell
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified


def persist_checkpoint(db: Session, runtime, *, commit=True) -> None:
    session_id = int(runtime.session_id)
    saved = db.get(SavedSession, session_id)
    if saved is None:
        raise ValueError("Cannot checkpoint a missing session")
    saved.state = runtime.state
    if runtime.game_manager.game_type == "MiniGames":
        round_state = db.get(RoundState, session_id)
        if round_state is None:
            db.add(
                RoundState(
                    session_id=session_id, state=runtime.game_manager.export_state()
                )
            )
        else:
            round_state.state = runtime.game_manager.export_state()
            flag_modified(round_state, "state")
    for player in runtime.players.values():
        shell = db.get(SessionShell, (session_id, int(player.user_id)))
        if shell is not None:
            shell.shell = player.serialize()
            flag_modified(shell, "shell")
    if commit:
        db.commit()


def attach_checkpoint(runtime, db: Session) -> None:
    """Allow timer transitions to checkpoint after the WebSocket request ends."""
    session_factory = sessionmaker(bind=db.get_bind())

    def checkpoint():
        with session_factory() as independent_db:
            persist_checkpoint(independent_db, runtime)

    runtime.checkpoint = checkpoint
