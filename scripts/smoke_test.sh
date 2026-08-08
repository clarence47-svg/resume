#!/usr/bin/env sh
set -eu

curl --fail --silent http://127.0.0.1:8080/health
curl --fail --silent http://127.0.0.1:8080/info

