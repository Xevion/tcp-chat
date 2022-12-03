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

```bash
python launch.py [c | s | server | client]
```

## Commands

Sent as ordinary messages, parsed by the server:

- `/help <command>` — info about a command
- `/reroll` — pick a new random colour
- `/join <room>` — move to another room (created on demand)
- `/rooms` — list active rooms and their member counts

## TLS

Off by default. Set `USE_TLS = True` in `shared/constants.py` and point `TLS_CERT` /
`TLS_KEY` at a certificate and key. A self-signed cert works with `TLS_VERIFY = False`:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -keyout shared/key.pem -out shared/cert.pem -days 365 -subj /CN=localhost
```

## Testing

```bash
pipenv run pytest
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
