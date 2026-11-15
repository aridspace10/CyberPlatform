# MiniGames challenge packs

Each playable command has a module in this directory. Its pack declares the
selectable `modes`, scenario `variants`, fixture root, and `build` method. Add the
pack once to `PACK_TYPES` in `registry.py`; the API's option map is derived from
the registered packs. `GameManager` handles rounds and scores, while
`ChallengeEngine` creates challenges and evaluates their private goals.
The frontend command picker still needs an entry for a newly playable command.

A builder receives the round's seeded random generator through `BasePack`. Use
`self.token_hex()` and `self.rng` for scenario content so the session seed
can reproduce prompts and fixtures. Give variants different file layouts or
contents and player-facing context; changing only a filename is not enough to
make another scenario. The planner rotates commands across rounds and spreads
modes and variants before repeating them.

Return a `Challenge` with a public prompt and generic syntax example. Keep the
working solution and expected outcome in its private goal. `OutputGoal` checks
terminal output and source inode IDs. `FileContentGoal` checks final file
contents and can be combined with command evidence for mutation tasks. New
goal types should implement `accepts(Observation)` so WebSocket scoring stays
command agnostic.

Put each command's gameplay tests in its existing
`backend/tests/cmd_tests/test_<command>.py`. Cross-command session and WebSocket
checks belong in their existing integration suites.
