# Domain checklist — CLI tool

Load this checklist when the diff touches:
- executable entry points: `bin/`, `cmd/`, `#!/usr/bin/env …` shebangs, `main()` functions in a project whose `package.json` / `Cargo.toml` / `pyproject.toml` declares a binary/script target
- argument parsing: `commander`, `yargs`, `clap`, `argparse`, `cobra`, `click`, `docopt`, `oclif`
- process wiring: `process.argv`, `os.Args`, `sys.argv`, `ProcessInfo.arguments`
- shell interop: `child_process`, `subprocess`, `Command`, spawn/run APIs, backtick-escaping
- signal handling: `SIGINT`, `SIGTERM`, `SIGHUP`, `Ctrl+C` handlers
- terminal I/O: `readline`, `prompt`, `inquirer`, `dialoguer`, TTY detection, ANSI color codes

CLI tools are **unix citizens**: they compose into pipelines, run inside scripts, get piped into `less`, get killed mid-run, and are expected to follow conventions that predate most of their authors. A CLI that breaks pipeline composition, ignores signals, or corrupts output when piped is broken even if it "works" interactively.

---

## Argument parsing

- **Unknown flags**: does the parser reject unknown flags, or silently ignore them? Silent ignore is a footgun — a typo `--foce` becomes a no-op and the user doesn't notice.
- **Positional vs flag**: does the parser handle `--` (end of flags marker) correctly? A file named `-rf` should be passable as `-- -rf`.
- **Flag / value separation**: are both `--flag value` and `--flag=value` supported? Is the short form `-f value` supported?
- **Flag conflicts**: does the parser detect mutually exclusive flags and error out, or does one silently override the other?
- **Required arguments**: if a required flag is missing, is the error message actionable (tells the user WHICH flag and WHERE to supply it)?
- **Type coercion**: `--count 10abc` — does the parser reject it or silently parse as 10? Rejection is correct; silent truncation is a classic bug.
- **Array flags**: `--tag a --tag b --tag c` vs `--tag a,b,c` — which does the parser support? Inconsistency across flags is confusing.
- **Subcommand dispatch**: does `cli foo bar` correctly route to the `foo bar` subcommand, or does it fall through to a default?

---

## Exit codes

- **`0` means success, non-zero means failure**. This is a contract. Any CLI that returns `0` on failure breaks shell scripts that check `$?` or use `&&` / `||`.
- **Distinct exit codes for distinct failures**: `1` = general error, `2` = misuse (parse error, invalid argument), specific codes for domain errors (`64-78` reserved by `sysexits.h`, but conventions vary).
- **Does the change return the right exit code on panic / uncaught exception?** A Node CLI that throws unhandled becomes exit 1 — but the error may not be visible if stderr is redirected.
- **Early return on `--help` / `--version`**: exit 0, write to stdout (not stderr), and do nothing else.
- **Signal death**: when killed by a signal, the exit code is `128 + signal_number` by convention. Does the change preserve this?

---

## Stdin / stdout / stderr discipline

- **stdout is for results, stderr is for diagnostics**. A CLI that prints progress bars to stdout breaks `cli | grep something`. A CLI that prints errors to stdout breaks `result=$(cli)`.
- **Does the change put progress / log output on stderr?** Check every `console.log`, `print`, `println!`, `fmt.Println` added in the diff — is it result data, or diagnostic?
- **Is stdout line-buffered or unbuffered?** A CLI whose output is buffered when piped (common with C stdio) looks hung in `cli | tee` until it flushes. Flush explicitly or set unbuffered mode.
- **Binary output**: if the CLI emits binary (e.g., `cli --png`), does it correctly write bytes without text encoding? On Windows, stdout may translate `\n` to `\r\n` in text mode.
- **Does the CLI read from stdin** when no file argument is given? This is the "unix pipe" idiom: `cat file | cli` should work the same as `cli file`.
- **EOF handling on stdin**: does the reader handle partial lines at EOF, empty input, and broken pipes?
- **Broken pipe**: `cli | head -1` closes the pipe after 1 line. Subsequent writes raise EPIPE / SIGPIPE. Does the CLI handle this gracefully, or crash with a stack trace?

---

## TTY detection

- **Is stdout a terminal?** `isatty(stdout)` tells you. The CLI should adapt:
  - **TTY**: colors, progress bars, interactive prompts, column widths
  - **Pipe / file**: no colors, no progress, plain output, stable format
- **A CLI that emits ANSI color codes when piped pollutes downstream tools** (`grep`, `less`, file writes). Default `--color=auto` with manual `--color=always` / `--color=never` override.
- **Is stdin a terminal?** Determines whether to prompt for input or read from pipe. Prompting when stdin is piped blocks forever.
- **NO_COLOR** environment variable: if set, disable color regardless. This is a de facto standard.
- **Width detection**: `process.stdout.columns` may be 0 or undefined when piped. Does the change assume a width?

---

## Signal handling

- **SIGINT (Ctrl+C)**: the CLI should clean up (close files, flush output, remove temp files) and exit with code 130. A CLI that leaves temp files on Ctrl+C accumulates garbage.
- **SIGTERM**: similar to SIGINT but often from `kill` or systemd. Should shut down cleanly, usually without prompting.
- **SIGHUP**: typically means the controlling terminal closed. A long-running CLI should usually continue (nohup semantics) or exit cleanly.
- **Double-Ctrl+C**: user wants out now. First Ctrl+C starts graceful shutdown; second forces exit.
- **Signal-safe cleanup**: the signal handler runs in a restricted context. Avoid async operations; set a flag and let the main loop check it.
- **Does the change add a long-running operation without a cancellation point?** A `for` loop with no interrupt check blocks Ctrl+C until completion.
- **Subprocess signal propagation**: when the CLI spawns children and receives a signal, does it forward the signal? Orphaned children keep running after the parent exits.

---

## Subprocess management

- **Shell injection**: passing user input to a shell-interpreted string API (`shell: true`, Python `subprocess.run(..., shell=True)`, Ruby backticks, PHP `shell_exec`) is a classic vulnerability. Use argument-array APIs instead: `spawn("git", ["clone", userInput])`, `subprocess.run(["git", "clone", user_input])`.
- **Quoting**: if a shell invocation is unavoidable, use proper quoting (`shell-quote`, `shlex.quote`). Manual string concatenation is a bug magnet.
- **Environment inheritance**: does the child inherit the parent environment, or a cleaned one? Secrets in env may leak to subprocesses unintentionally.
- **Working directory**: does the child run in the expected CWD? Does the change set it explicitly, or rely on implicit inheritance?
- **Stdout/stderr capture**: does the parent wait for the child, capture its output, or stream it? Buffered capture of a large output can OOM; streamed capture can interleave.
- **Zombie processes**: does the parent reap the child with `wait` / `await` / `Wait`? Unreaped children become zombies.
- **Timeout**: is there a timeout on subprocess execution? A hung subprocess can freeze the CLI forever.
- **Kill on parent exit**: if the CLI exits while children are running, are they terminated? Orphaned `grep` or `ffmpeg` processes are a common bug.

---

## File and path handling

- **Path arguments**: does the CLI handle `~`, `.`, `..`, `~user`, absolute vs relative paths correctly?
- **Glob expansion**: on Windows, shell does not expand `*.txt` — the CLI must do it, or require the user to pass full paths. On Unix, shell expands before `argv`, but the CLI should still handle literal `*` if the user quotes.
- **Symlinks**: does the change follow symlinks? Should it? A `rm -r` on a symlinked directory is different from recursing into it.
- **File creation mode**: what permissions does a newly created file get? Default may be 0666, but `umask` affects it. Sensitive files (keys, configs) should be 0600.
- **Atomic file writes**: write-then-rename pattern for config updates. Does the change overwrite the destination in place (risking partial writes on crash)?
- **Temp files**: are they created in a secure temp dir (`os.tmpdir()` / `TMPDIR` / `mkdtemp`)? Are they cleaned up on success AND on failure AND on signal?

---

## Environment variables

- **Sensitive env vars in error messages**: printing env values verbatim can leak secrets. Scrub before logging.
- **Required vs optional**: does the CLI validate required env vars at startup with a clear error, or crash later with an unrelated error?
- **Default values**: are defaults documented? Does `--help` show them?
- **Precedence**: flag > env var > config file > default is the usual order. Does the change respect this?
- **Env var leaking to subprocesses**: does the CLI unset sensitive vars before spawning untrusted children?

---

## Output formatting

- **Human-readable vs machine-readable**: does the CLI have `--json` / `--format=json` for scripting? A CLI that only prints to humans forces downstream tools to parse prose — fragile.
- **Table alignment**: if the CLI prints tables, do they misalign on unicode wide characters or zero-width codepoints?
- **Quoting / escaping**: if output contains filenames with spaces or newlines, can downstream tools parse it? `find` solves this with `-print0`; does the CLI?
- **Progress indicators**: on non-TTY, suppress. On TTY, use carriage return to overwrite, and clear the line on completion.
- **Pagination**: does the CLI auto-page long output into `less` when TTY? Is there a `--no-pager` escape hatch?

---

## Error messages

- **Actionable errors**: "Permission denied: /etc/foo" is better than "Error: operation failed". Include the path, the operation, and the underlying error.
- **Error to stderr, not stdout**.
- **Consistent error prefix**: `cli: error: ...` or `Error: ...` — whatever the convention, use it consistently.
- **Stack traces in production**: does the CLI dump a stack trace on error, or a clean message? Debug mode (`--verbose` / `RUST_BACKTRACE=1`) is the right switch.

---

## Output integration

`scenarios_considered` must include at least one **pipeline composition scenario** and one **interrupt scenario**. Examples:

```
- `cli | head -1` — does the CLI handle SIGPIPE gracefully?
- `cli | grep error` — is diagnostic output on stderr so grep sees only results?
- `cli < /dev/null` — does the CLI handle empty stdin, or block waiting for input?
- user presses Ctrl+C mid-operation — are temp files cleaned up?
- `cli --color=always | less -R` — do colors render, or is there escape code corruption?
- CLI spawns ffmpeg subprocess; user kills CLI with SIGTERM — is ffmpeg also terminated?
- unknown flag `--foce` (typo of `--force`) — does the parser error or silently ignore?
- output redirected to file on Windows — are line endings correct?
```
