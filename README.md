# tcp-chat

A little experiment with python's `socket` module expanded with `sqlite3`, `threading`,
and `pyqt5` to create a simple server & client chat mimicking IRC.

## Installation

Create and activate a environment if needed, then install the project requirements:

```bash
pipenv install
```

## Usage

```bash
python launch.py [c | s | server | client]
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
