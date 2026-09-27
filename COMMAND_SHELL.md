# Try command fixes in VS Code

Open the repository folder in VS Code. In **Terminal > New Terminal**, run:

```powershell
python run_shell.py
```

You now have a CyberPlatform prompt inside the IDE. Type commands normally:

```text
cyber:/root$ mkdir -p work/demo
cyber:/root$ cd work/demo
cyber:/root/work/demo$ echo hello > example.txt
cyber:/root/work/demo$ cat example.txt
hello
cyber:/root/work/demo$ cat example.txt | grep hello
hello
cyber:/root/work/demo$ rm -i example.txt
rm: remove regular file 'example.txt'? y
cyber:/root/work/demo$ :reset
Fresh filesystem ready. Restart the launcher to load code edits.
cyber:/root$ :exit
```

The launcher uses the actual `CommandLine`, `ShellState`, process programs, and
scheduler. Files and directories persist between inputs in this console and are
discarded on exit or reset. They live in the simulated filesystem in memory.
No backend server, database, browser, login, or frontend is needed.

## Run and debug from VS Code

1. Have Microsoft's **Python** and **Python Debugger** extensions installed.
2. Press **Ctrl+Shift+P**, choose **Python: Select Interpreter**, and select your
   working backend Python environment (Python 3.12+; CI uses 3.13).
3. For normal use: **Ctrl+Shift+P > Tasks: Run Task > CyberPlatform: Command shell**.
4. To debug: select **CyberPlatform: Debug command shell** under **Run and Debug**,
   put a breakpoint in the command handler in `backend/game/commandline.py`, and
   press **F5**. Enter your command in the **Terminal** panel to hit the breakpoint.
5. Edit a handler, save, and restart debugging with **Ctrl+Shift+F5**. For a normal
   terminal session, use `:exit` and rerun `python run_shell.py` to load the edits.

The task and debugger use your selected Python interpreter. A manually opened
terminal uses its own activated environment; `python -c "import sys; print(sys.executable)"`
shows which interpreter that terminal uses.

If imports fail, install the backend dependencies into that environment from the
repository root:

```powershell
python -m pip install -r backend/requirements.txt
```

If the old `venv` reports **No Python at ...**, select a working interpreter instead.
Do not select the broken environment. A fresh optional environment can be created
with `python -m venv .venv`, then select `.venv` and install the requirements there
(keep that local environment out of Git).

## Useful controls

- `:help`: show available engine commands and console controls.
- `:status`: show the last returned status. Launch with `--status` to print it after
  every input. These are the engine's current statuses, including existing bugs;
  prompt-based programs currently expose only stdout/stderr, so the adapter reports
  1 when those inputs return errors and 0 otherwise.
- `:reset`: reset to the starting sample files; this **does not reload Python code**.
- `:exit`, `exit`, or `quit`: leave the console at the normal shell prompt.
- **Ctrl+C**: cancel a foreground program (including `sleep` or heredoc input).
- **Ctrl+Z**, then **Enter** on Windows, or **Ctrl+D** on Linux/macOS: send EOF and exit.

Start with `python run_shell.py --empty` for a blank filesystem. The default samples
are `notes.txt` and `logs/app.log`; try `grep ERROR logs/app.log`. Normal command help
works, for example `mkdir --help`. Heredocs work too: enter `cat << EOF`, some lines,
and then `EOF` on its own line. While a program is asking for input, console control
words are passed to that program as literal input; use Ctrl+C to cancel it.

This is a local shell adapter: it exercises engine behavior, not WebSocket transport,
frontend rendering, login, or multiplayer behavior. Existing parser, command, and
foreground-composition limitations remain visible. Scheduler waits use one-second
ticks, and background jobs are not supported by the current engine.

### Commands that wait, such as sleep

Enter `sleep 2` at the CyberPlatform prompt. The console runs the real `SleepProgram`
through the existing scheduler and returns to the prompt after two one-second ticks.
You can then type `echo awake`. Press Ctrl+C during a longer sleep to cancel it.
This runs locally and does not require a WebSocket or backend server.

For a repeatable version from your VS Code terminal:

```powershell
python run_shell.py -c "sleep 2" -c "echo awake"
```

## Repeat a reproduction and run regression tests

Each `-c` is a separate input to the same shell. Quote the entire input so PowerShell
does not consume `>`, `|`, or `&&` itself:

```powershell
python run_shell.py --empty --status -c "mkdir -p work/demo" -c "cd work/demo" -c "echo hello > example.txt" -c "cat example.txt"
```

The process exits with the last returned status. A remaining interactive prompt exits
with status 2 rather than hanging; supply another `-c` for each response or use the
interactive console. Each new invocation loads your saved code with fresh state.

After trying a fix, run **Tasks: Run Task > CyberPlatform: Test one command** and
enter the command name, such as `mkdir`. Its dedicated test file must already exist.
The terminal equivalent is:

```powershell
Set-Location backend
python -m pytest tests/cmd_tests/test_mkdir.py -q --no-cov
```

Keep command regressions in `backend/tests/cmd_tests/test_<command>.py`, following
`AGENTS.md`. The console's cross-command integration checks live in
`backend/tests/test_dev_shell.py`. `--no-cov` is for quick focused runs; use
`python -m pytest` from `backend` for the full suite with the configured coverage gate.

VS Code references: [Python debugging](https://code.visualstudio.com/docs/python/debugging)
and [running tasks](https://code.visualstudio.com/docs/debugtest/tasks).
