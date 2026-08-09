#!/usr/bin/env sh
set -eu

curl --fail --silent http://127.0.0.1:8080/health
curl --fail --silent http://127.0.0.1:8080/info
curl --fail --silent http://127.0.0.1:8080/career/settings
curl --fail --silent http://127.0.0.1:8080/jobs
curl --fail --silent http://127.0.0.1:8080/tracking/dashboard
curl --fail --silent http://127.0.0.1:8501/_stcore/health
