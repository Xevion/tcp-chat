# tcp-chat

A little experiment with python's `socket` module expanded with `sqlite3`, `threading`,
and `pyqt5` to create a simple server & client chat mimicking IRC.

## Installation

Create and activate a environment if needed, then install the project requirements:

```bash
pipenv install
```

## Usage

I like to use Windows Terminal to run both a server and client simultaneously inside one window.

```bash
wt -d . -p "Command Prompt" ; sp -d . -p "Command Prompt"
```

Then in each pane, run the client:
```bash
python launch.py c
```
and the server:
```bash
python launch.py s
```

## To-do List

Expand to-do list
