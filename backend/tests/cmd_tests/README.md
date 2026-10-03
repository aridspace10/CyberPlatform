# Command path regressions

Every registered command has a dedicated `test_<command>.py`. The `dot_paths`
tests exercise the public shell entry point from root and a nested directory.
Run them from `backend` with:

```sh
python -m pytest tests -k dot_paths -o addopts= -p no:cacheprovider
```

The cases cover `.` and `..` as complete operands and path components,
traversal above root, parent-directory files, hidden names, and missing or
regular-file components before `.`/`..`. Shared assertions check node identity,
parent links, unique child names, working-directory state, and serialization.
Read-only commands must also preserve file data and the existing tree. Creation,
copying, moving, links, metadata changes, and removal have command-specific
expected effects. `ls -a`/`-A` must render virtual entries without creating nodes.

Shell redirection and listing followed by recursive operations stay in
`tests/test_cmd.py`. Commands without filesystem operands (`echo`, `ps`, `ping`,
`sleep`, and `pwd`) have relevant literal-argument or directory-state checks;
the tests do not introduce path operands for those commands.

These are regression contracts, including currently broken behavior. Failures
remain ordinary pytest failures, not skips or expected failures. Fix the command
or shared filesystem implementation before changing an expected result. The
baseline can be checked separately with `-k 'not dot_paths'`.
