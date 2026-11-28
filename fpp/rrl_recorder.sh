#!/bin/bash
# Starts the Rocky Ridge Lights request recorder in the background (run from the FPP schedule).
# Only one copy runs at a time. Log: /home/fpp/media/logs/rrl_recorder.log
# Pass "test" as the script argument to check the token and Remote Falcon without recording.
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG=/home/fpp/media/logs/rrl_recorder.log
if [ "$1" = "test" ]; then
  python3 "$DIR/rrl_recorder.py" --test >> "$LOG" 2>&1
  exit
fi
nohup flock -n /tmp/rrl_recorder.lock python3 "$DIR/rrl_recorder.py" >> "$LOG" 2>&1 < /dev/null &
