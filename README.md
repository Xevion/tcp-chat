# tcp-chat

A little experiment with python's `socket` module expanded with `sqlite3`, `threading`,
and `pyqt5` to create a simple server & client chat mimicking IRC. Supports rooms,
a keep-alive heartbeat with client auto-reconnect, and optional TLS.

## Installation

Create and activate a environment if needed, then install the project requirements:

```bash
pipenv install
```

## Usage

Run the server or client through `launch.py` (`server`/`client` also accept `s`/`c`):

```bash
python launch.py server                            # listen on the defaults
python launch.py client --random                   # connect with a random nickname
python launch.py server --host 0.0.0.0 --port 6000 --tls
```

With the environment active the script is executable directly: `./launch.py server`.
See `python launch.py --help` for all options. Add `-v` for debug logging or
`--log-file PATH` to also write logs to a file.

## Configuration

Settings resolve in order: command-line flag, then `tcp-chat.toml`, then the built-in
default. Copy the sample to get started:

```bash
cp tcp-chat.toml.example tcp-chat.toml
```

## Commands

Sent as ordinary messages, parsed by the server:

- `/help <command>` — info about a command
- `/reroll` — pick a new random colour
- `/join <room>` — move to another room (created on demand)
- `/rooms` — list active rooms and their member counts

## TLS

Off by default. Generate a self-signed development certificate:

```bash
make cert
```

Then enable it with `--tls` (or `tls = true` in `tcp-chat.toml`) on both ends. The
GUI client also has a TLS checkbox in the connection dialog. The client accepts
self-signed certificates while `TLS_VERIFY` is false.

Client and server negotiate TLS (and the protocol version) in a short cleartext
handshake before any connection is established, so a mismatch — connecting without
TLS to a TLS-only server, say — is reported plainly ("server requires TLS") instead
of failing with an opaque socket error.

## Connecting

The connection dialog remembers servers you have used. The Recent tab lists them
newest-first; right-click one to star it onto the Favorites tab. Click any entry to
fill the form, and use Test Connection to check a server is reachable before joining.

## Testing

```bash
pipenv run pytest
```

The codebase is type-checked with [mypy](https://mypy-lang.org/) (configured in
`mypy.ini`):

```bash
pipenv run mypy
```

It is formatted with [Black](https://black.readthedocs.io/) (configured in
`pyproject.toml`):

```bash
pipenv run black .
```

## Building

```bash
make build

# optional
make clean
```

## Development Notes

Launching Qt Designer

```bash
pyqt5-tools designer
```

Launching Dual Pane Windows Terminal

```bash
# Command Prompt
wt -d . -p "Command Prompt" ; sp -d . -p "Command Prompt"
# Powershell
start wt -Arg "-d . -p `"Powershell`" ; sp -d . -p `"Powershell`""
```
