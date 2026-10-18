# Background jobs

Append `&` to a shell job to schedule it in the background. For example,
`echo before & sleep 2 & echo after` returns the foreground output and a
`[job PID] started COMMAND` line without waiting for either background job.
The session scheduler starts each job on its next tick. Background output and
the exit status are reported to the owning WebSocket when the job finishes;
the interactive prompt remains available while it runs.

Background `sleep` is supported. Commands that ask for interactive input, such
as `rm -i` and heredocs, exit with status 1 and report that background jobs
cannot wait for input. A failed command or execution error ends its job with a
nonzero status and includes its diagnostic in the completion event.

Clients can cancel an active job by sending
`{"type":"cancel_background_job","job_id":PID}`. Cancellation ends the job
with status 130, stops its child processes, and reports completion through the
same event. Removing a session stops its scheduler and cleans up its background
jobs.

Completion messages use this shape:

```json
{
  "type": "background_job_complete",
  "job_id": 104,
  "command": "sleep 2",
  "stdout": [],
  "stderr": [],
  "status": 0
}
```
