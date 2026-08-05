#!/bin/sh
set -eu
curl --fail --silent --show-error http://127.0.0.1/api/health >/dev/null
