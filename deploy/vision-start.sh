#!/bin/sh
set -eu
ollama serve &
server_pid=$!
trap 'kill "$server_pid"' INT TERM EXIT
until ollama list >/dev/null 2>&1; do sleep 1; done
ollama pull qwen2.5vl:3b
wait "$server_pid"
