#!/bin/sh

umask 022
export LC_CTYPE=en_US.iso-8859-1
CONFIG=$HOME/.pldbuilderrc
[ -f "$CONFIG" ] && . $CONFIG
if [ -z "$BUILDERPATH" ]; then
	dir=$(dirname "$0")
	BUILDERPATH="$(cd "$dir"/..; pwd)"
fi
export BUILDERPATH

if lockfile -r3 $HOME/.builder_request_handler.lock 2>/dev/null; then
	trap "rm -f $HOME/.builder_request_handler.lock" 1 2 3 13 15
	cd $BUILDERPATH
	python PLD_Builder/request_handler.py
	rm -f $HOME/.builder_request_handler.lock
else
	return 1
fi
