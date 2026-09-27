# Repository conventions

## Command tests

- Keep each command's tests in one dedicated file: `backend/tests/cmd_tests/test_<command>.py`.
- Add new command tests and ticket regressions to that command's existing file. Do not create combined command test files or separate per-ticket test files.
- When working on a command, consolidate its legacy command-specific tests from `test_cmd.py` or other files into its dedicated file.
- Put shared fixtures in `conftest.py` and reusable assertions in helper modules. Cross-command shell and WebSocket integration tests can remain in their relevant integration suites.
