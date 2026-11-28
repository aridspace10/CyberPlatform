"""Persist a validated runtime state transition before notifying players."""

from copy import deepcopy


async def transition_and_persist(db, saved_session, runtime, new_state: str) -> None:
    old_state = runtime.state
    old_saved_state = saved_session.state
    old_finished = runtime.game_manager.finished
    old_manager = deepcopy(runtime.game_manager) if new_state == "running" else None
    old_shells = (
        {name: deepcopy(player.shell) for name, player in runtime.players.items()}
        if new_state == "running"
        else {}
    )
    try:
        await runtime.set_state(new_state, broadcast=False)
        saved_session.state = runtime.state
        db.commit()
    except Exception:
        db.rollback()
        saved_session.state = old_saved_state
        runtime.state = old_state
        runtime.game_manager.finished = old_finished
        if old_manager is not None:
            runtime.game_manager = old_manager
            runtime.game_manger = old_manager
            for name, shell in old_shells.items():
                runtime.players[name].shell = shell
        raise
    await runtime.broadcast_game_state()
