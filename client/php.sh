#!/bin/sh
set -eu
program=${0##*/}
program=${program%.sh}
dir=$(dirname "$0")
suffix=${program#php}
pre_command='for a in php4-common php52-common php53-common php54-common php55-common php56-common php70-common php71-common php72-common php73-common php74-common hhvm; do poldek -e $a --noask; done; :'

request() {
	"$dir/make-request.sh" -D "php_suffix $suffix" ${pre_command:+-c "$pre_command"} ${post_command:+-C "$post_command"} "$@"
}

# if called as php.sh, invoke all php versions
# for php7.sh, invoke only php 7.x
case "$suffix" in
'')
	for php in $dir/php??.sh; do
		suffix=${php#$dir/php}
		suffix=${suffix%.sh}
		request "$@"
	done
	;;
7)
	for php in $dir/php7?.sh; do
		suffix=${php#$dir/php}
		suffix=${suffix%.sh}
		request "$@"
	done
	;;
*)
	request "$@"
	;;
esac
