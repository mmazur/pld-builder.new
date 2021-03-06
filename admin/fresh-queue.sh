#!/bin/sh

umask 077

CONFIG=$HOME/.pldbuilderrc
[ -f "$CONFIG" ] && . $CONFIG
[ -n "$BUILDERPATH" ] || BUILDERPATH="$HOME/pld-builder.new/"
export BUILDERPATH

if [ -d "$BUILDERPATH" ]; then
	cd "$BUILDERPATH"
else
	echo "the $BUILDERPATH directory does not exist"
	exit 1
fi


if [ -f "$BUILDERPATH/config/global" ]; then
	. $BUILDERPATH/config/global
fi

if [ "$1" != "y" ] ; then
  echo "this scripts kills current queue and installs new"
  echo "run '$0 y' to run it"
  exit 1
fi

mkdir -p spool/{builds,buildlogs,notify,ftp} www/srpms lock
echo 0 > www/max_req_no
echo 0 > spool/last_req_no
echo -n > spool/processed_ids
echo -n > spool/got_lock
echo '<queue/>' > spool/queue
echo '<queue/>' > spool/req_queue
test ! -z "$binary_builders" && for bb in $binary_builders; do
	echo '<queue/>' > spool/queue-$bb
done

chmod 755 www www/srpms
chmod 644 www/max_req_no
