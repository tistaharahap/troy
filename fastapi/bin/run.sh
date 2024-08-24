#!/usr/bin/env bash
set -e

export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
echo 'PYTHONPATH is: '${PYTHONPATH}

unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${unameOut}"
esac

if test "x${PORT}" = 'x'; then
  export PORT=8080
fi
if test "x${HOST}" = 'x'; then
  export HOST=0.0.0.0
fi
if test "x${ENV}" = 'x'; then
  export ENV=dev
fi

# Control number of workers for uvicorn
if test "x${WEB_CONCURRENCY}" = 'x'; then
  echo 'WEB_CONCURRENCY is not set, setting it to number of cores'
  if [ "$machine" == "Mac" ]; then
    export WEB_CONCURRENCY=1
  else
    export WEB_CONCURRENCY=`nproc --all`
  fi
fi
echo 'WEB_CONCURRENCY is: '${WEB_CONCURRENCY}

if test "x${ENV}" = 'xdev'; then
  uvicorn python_fastapi.api:app --host $HOST --port $PORT --log-level debug --reload --reload-dir src
else
  uvicorn python_fastapi.api:app --host $HOST --port $PORT --log-level info --workers $WEB_CONCURRENCY
fi
