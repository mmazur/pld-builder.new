#!/bin/sh
set -e

dir=$(cd "$(dirname "$0")"; pwd)
rpmdir=$(rpm -E %_topdir)
dist=th

pkgs_head="
	dahdi-linux
	e1000e
	igb
	ipset
	ixgbe
	lin_tape
	linux-fusion
	linuxrdac
	lirc
	madwifi-ng
	nvidiabl
	open-vm-tools
	r8168
	VirtualBox
	vpb-driver
	xorg-driver-video-fglrx
	xorg-driver-video-fglrx-legacy
	xorg-driver-video-nvidia
	xtables-addons
"

pkgs_longterm=

# autotag from rpm-build-macros
# displays latest used tag for a specfile
autotag() {
	local out spec pkg ref
	for spec in "$@"; do
		# strip branches
		pkg=${spec%:*}
		# ensure package ends with .spec
		spec=${pkg%.spec}.spec
		# and pkg without subdir
		pkg=${pkg#*/}
		# or .ext
		pkg=${pkg%%.spec}
		cd $pkg
		git fetch --tags
		if [ -n "$alt_kernel" ]; then
			ref="refs/tags/auto/${dist}/${pkg}-${alt_kernel}-[0-9]*"
		else
			ref="refs/tags/auto/${dist}/${pkg}-[0-9]*"
		fi
		out=$(git for-each-ref $ref --sort=-authordate --format='%(refname:short)' --count=1)
		echo "$spec:$out"
		cd -
	done
}

get_last_tags() {
	local pkg spec

	echo >&2 "Fetching package tags: $*..."
	for pkg in "$@"; do
		echo >&2 "$pkg... "
		if [ ! -e $pkg/$pkg.spec ]; then
			$rpmdir/builder -g $pkg -ns -r HEAD 1>&2
		fi
		if [ ! -e $pkg/$pkg.spec ]; then
			# just print it out, to fallback to base pkg name
			echo "$pkg"
		else
			spec=$(autotag $pkg/$pkg.spec)
			spec=${spec#*/}
			echo >&2 "... $spec"
			echo $spec
		fi
	done
}

# The HP-UX ksh and POSIX shell print the target directory to stdout
# if CDPATH is set.
(unset CDPATH) >/dev/null 2>&1 && unset CDPATH

cd $rpmdir
case "$1" in
	head)
		kernel=$(get_last_tags kernel)
		kernel=$(echo ${kernel#*auto/??/} | tr _ .)
		specs=""
		for pkg in $pkgs_head; do
			echo >&2 "Rebuilding $pkg..."
			$rpmdir/builder -g $pkg -ns
			$rpmdir/relup.sh -m "rebuild for $kernel" -ui $pkg/$pkg.spec
			specs="$specs $pkg.spec"
		done
		$dir/make-request.sh -nd -r -d $dist $specs
		;;
	longterm)
		kernel=$(alt_kernel=longterm get_last_tags kernel)
		kernel=$(echo ${kernel#*auto/??/} | tr _ .)
		specs=""
		if [ -n "$pkgs_longterm" ]; then
			for pkg in $pkgs_longterm; do
				echo >&2 "Rebuilding $pkg..."
				$rpmdir/builder -g $pkg -ns
				$rpmdir/relup.sh -m "rebuild for $kernel" -ui $pkg/$pkg.spec
				specs="$specs $pkg.spec"
			done
			# first build with main pkg (userspace), later build from tag
			$dir/make-request.sh -nd -r -d $dist --without kernel $specs
		fi
		specs=$(get_last_tags $pkgs_head $pkgs_longterm)
		$dir/make-request.sh -nd -r -d $dist --kernel longterm --without userspace $specs
		;;
	*)
		# try to parse all args, filling them with last autotag
		while [ $# -gt 0 ]; do
			case "$1" in
			--kernel|--with|--without)
				args="$1 $2"
				shift
				;;
			-*)
				args="$args $1"
				;;
			*)
				specs="$specs $1"
				;;
			esac
			shift
		done
		specs=$(get_last_tags $specs)
		$dir/make-request.sh -nd -r -d $dist $args $specs
		;;
esac
