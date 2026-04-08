#!/usr/bin/env bash
daphne -b 0.0.0.0 -p $PORT hotserve.asgi:application