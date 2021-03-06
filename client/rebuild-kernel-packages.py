#!/usr/bin/python

from __future__ import print_function

import argparse
import collections
import os
import rpm
import shlex
import subprocess
import sys

supported_kernels = ['head', '5.4', '4.19', '4.14', '4.9']

packages = collections.OrderedDict([
    ('dahdi-linux',                           ['head', '5.4', '4.19', '4.14', '4.9']),
    ('ipset',                                 ['head', '5.4', '4.19', '4.14', '4.9']),
    ('lin_tape',                              ['head', '5.4', '4.19', '4.14', '4.9']),
    ('linux-gpib',                            ['head', '5.4', '4.19', '4.14', '4.9']),
    ('lttng-modules',                         ['head', '5.4', '4.19', '4.14', '4.9']),
    ('r8168',                                 ['head', '5.4', '4.19', '4.14', '4.9']),
    ('rtl8812au',                             ['head', '5.4', '4.19', '4.14', '4.9']),
    ('VirtualBox',                            ['head', '5.4', '4.19', '4.14', '4.9']),
    ('vpb-driver',                            ['head', '5.4', '4.19', '4.14', '4.9']),
    ('wl',                                    ['head', '5.4', '4.19', '4.14', '4.9']),
    ('xorg-driver-video-nvidia',              ['head', '5.4', '4.19', '4.14', '4.9']),
    ('xorg-driver-video-nvidia-legacy-390xx', ['head', '5.4', '4.19', '4.14', '4.9']),
    ('zfs',                                   ['head', '5.4', '4.19', '4.14', '4.9']),
    ('xtables-addons',                        ['head', '5.4', '4.19']),
    ('xtables-addons:XTADDONS_2',             ['4.14', '4.9']),
    ('crash',                                 ['5.4', '4.19', '4.14', '4.9']),
    ('WireGuard',                             ['5.4', '4.19', '4.14', '4.9']),
])

def get_rpmdir():
    return rpm.expandMacro("%_topdir")

def clean_pkgname(package):
    pkg = package.split(":")
    if not pkg:
        raise NameError
    spec = pkg[0]
    # ensure package ends with .spec
    if not spec.endswith(".spec"):
        spec += ".spec"
    name = spec[:-5]
    # and pkg without subdir
    name = name[name.rfind("/")+1:]
    try:
        branch = pkg[1]
    except IndexError:
        branch = "master"
    return [name, spec, branch]

def run_command(command, verbose=False, quiet=True):
    gitproc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=-1)
    gitproc.wait()
    out = gitproc.stdout.read().strip("\n'")
    if verbose:
        print(' '.join(command))
    if not quiet:
        print(out)
    if gitproc.returncode != 0:
        if quiet:
            print(out)
        print('\nError running command: \n')
        print(' '.join(command))
        return (False, None)
    return (True, out)

def get_last_tag(name, spec, branch, dist="th", kernel=None, verbose=False):
    fetch_package(name, spec, branch, verbose=verbose)
    if os.path.exists("%s/%s/%s" % (get_rpmdir(), name, spec)):
        tag = get_autotag(name, spec, branch, dist=dist, kernel=kernel, verbose=verbose)
    return tag

def get_autotag(name, spec, branch, dist="th", kernel=None, verbose=False):
    if not kernel or kernel == "head" or kernel == "master":
        ref = "auto/%s/%s-[0-9]*" % (dist, name)
    else:
        ref = "auto/%s/%s-%s-[0-9]*" % (dist, name, kernel)
    gitdir = "%s/%s" % (get_rpmdir(), name)
    tag = run_command(["/usr/bin/git", "-C", gitdir, "describe", "--tags", "--match", ref, "--abbrev=0", branch], verbose=verbose)
    return tag[1]

def fetch_package(name, spec, branch, verbose=False):
    gitdir = "%s/%s" % (get_rpmdir(), name)
    if os.path.exists("%s/.git" % gitdir):
        run_command(["/usr/bin/git", "-C", gitdir, "fetch", "origin"], verbose=verbose)
    else:
        run_command(["/usr/bin/git", "clone", "-o", "origin", "git://git.pld-linux.org/packages/" + name + ".git", gitdir], verbose=verbose)
        if not os.path.exists("%s/%s" % (gitdir, spec)):
            return None
        run_command(["/usr/bin/git", "-C", gitdir, "config", "--local", "--add", "remote.origin.fetch", "refs/notes/*:refs/notes/*"], verbose=verbose)
        run_command(["/usr/bin/git", "-C", gitdir, "remote", "set-url", "--push", "origin", "ssh://git@git.pld-linux.org/packages/" + name], verbose=verbose)
    run_command(["/usr/bin/git", "-C", gitdir, "fetch", "origin", "refs/notes/*:refs/notes/*"], verbose=verbose)
    if branch:
        if run_command(["/usr/bin/git", "-C", gitdir, "rev-parse", "--verify", "-q", branch], verbose=verbose):
            run_command(["/usr/bin/git", "-C", gitdir, "checkout", branch, "--"], verbose=verbose)
        elif run_command(["/usr/bin/git", "-C", gitdir, "rev-parse", "--verify", "-q", "refs/remotes/origin/" + branch], verbose=verbose):
            run_command(["/usr/bin/git", "-C", gitdir, "checkout", "-t", "refs/remotes/origin/" + branch], verbose=verbose)
        rev_branch = run_command(["/usr/bin/git", "-C", gitdir, "rev-parse", branch], verbose=verbose)
        rev_head = run_command(["/usr/bin/git", "-C", gitdir, "rev-parse", "HEAD"], verbose=verbose)
        if rev_branch[1] != rev_head[1]:
            print("Error: cannot checkout " + name)
            return None
        run_command(["/usr/bin/git", "-C", gitdir, "merge", "--ff-only", "@{upstream}"], verbose=verbose)

def csv_list(string):
    return string.split(',')

def kernel_cmp(x, y):
    x = x.split('.')
    y = y.split('.')
    try:
        int(x[0])
    except ValueError:
        return 1
    try:
        int(y[0])
    except ValueError:
        return -1
    majdiff = int(x[0]) - int(y[0])
    if majdiff:
        return majdiff
    mindiff = int(x[1]) - int(y[1])
    return mindiff

def main():
    parser = argparse.ArgumentParser(description='Rebuild kernel modules.')
    parser.add_argument('-d', '--dist',
            default='th',
            help='Dist name for getting auto-tags (default: %(default)s)')
    parser.add_argument('-m', '--make-request',
            default="make-request",
            metavar='SCRIPT',
            help='Name / path of the make-request script (default: %(default)s)')
    parser.add_argument('-ni', '--noinstall',
            action='store_true',
            help='skip installing new kernel packages on src builder (default: %(default)s)')
    parser.add_argument('-p', '--packages',
            type=csv_list,
            default=packages.keys(),
            metavar='PKG1[,PKG2...]',
            help='Package names to build (default: all)')
    parser.add_argument('-s', '--skip',
            type=csv_list,
            metavar='VER1[,VER2...]',
            help='Don\'t build modules specific to these kernels (default: %(default)s)')
    parser.add_argument('-t', '--test-build',
            action='store_true',
            help='Perform a test-builds')
    parser.add_argument('-bh', '--head',
            action='store_true',
            help='Perform build from head instead of last auto-tag')
    parser.add_argument('-v', '--verbose',
            action='store_true',
            help='Be verbose when running commands (default: %(default)s)')
    args = parser.parse_args()

    build_mode = '-r'
    if args.test_build:
        build_mode = '-t'

    if not args.skip:
        args.skip = []

    if not args.make_request.startswith('/'):
        for path in os.defpath.split(os.pathsep):
            if os.path.isfile('/'.join([path, args.make_request])):
                args.make_request = '/'.join([path, args.make_request])
                break

    if not args.noinstall:
        source_packages = []
        for kernel in supported_kernels:
            if kernel == 'head':
                ver = '-'
            else:
                ver = '-%s-' % kernel
            source_packages.extend(['kernel%sheaders' % ver, 'kernel%smodule-build' % ver])
        command = (('%(make_request)s -b %(dist)s-src -t -c '
                '"poldek -n %(dist)s -n %(dist)s-ready -n %(dist)s-test --up ; '
                'poldek -uvg %(source_packages)s"') %
                {'make_request': args.make_request,
                    'dist': args.dist,
                    'source_packages': ' '.join(source_packages)})
        run_command(shlex.split(command), verbose=args.verbose, quiet=False)
        raw_input('\nPress Enter after src builder updates kernel packages...')

    print('\nCurrent kernels versions:')
    all_kernels = set()
    for kernel_list in packages.values():
        all_kernels.update(kernel_list)
    all_kernels = list(all_kernels)
    all_kernels.sort(cmp=kernel_cmp, reverse=True)
    for kernel in all_kernels:
        branch = 'master'
        if kernel != 'head':
            branch = 'LINUX_%s' % kernel.replace('.','_')
        print('%s: %s' % (kernel, get_last_tag('kernel', 'kernel.spec', branch, dist=args.dist, kernel=kernel, verbose=args.verbose)))

    for pkg, kernels in packages.items():
        try:
            name, spec, branch = clean_pkgname(pkg)
        except NameError:
            continue
        if not pkg in args.packages:
            continue
        if not set(kernels).symmetric_difference(args.skip):
            continue
        if args.test_build:
            if branch:
                spec = '%s:%s' % (spec, branch)
            command = ("%s -nd %s -d %s --define 'build_kernels %s' --without userspace %s" %
                    (args.make_request, build_mode, args.dist, ','.join(kernels), spec))
        else:
            if not args.head:
              tag = get_last_tag(name, spec, branch, dist=args.dist, verbose=args.verbose)
              if not tag:
                  print("Failed getching last autotag for %s!" % pkg)
                  continue
              spec = '%s:%s' % (spec, tag)
            command = ("%s -nd %s -d %s --define 'build_kernels %s' --without userspace %s" %
                    (args.make_request, build_mode, args.dist, ','.join(kernels), spec))
        run_command(shlex.split(command), verbose=args.verbose, quiet=False)

if __name__ == "__main__":
    main()

# vi: encoding=utf-8 ts=8 sts=4 sw=4 et
