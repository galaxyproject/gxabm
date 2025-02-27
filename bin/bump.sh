#!/usr/bin/env bash
set -eu

# ANSI color codes for the console.
reset="\033[0m"
bold="\033[1m"

# Function used to highlight text.
function hi() {
    echo -e "$bold$@$reset"
}

function help() {
	less -RX << EOF

$(hi NAME)
    $0

$(hi DESCRIPTION)
    Bump the version in abm/VERSION

$(hi SYNOPSIS)
    $0 [major|minor|patch|dev|help]

$(hi OPTIONS)
    $(hi major)    Bump to the major dev version.
    $(hi minor)    Bump to the minor dev version.
    $(hi patch)    Bump to the patch dev version.
    $(hi dev)      Bump the development version.
    $(hi release)  Bump to the next release version by stipping the dev portion.
    $(hi help)     Show this help message.

EOF
}

if [[ $# = 0 ]] ; then
  help
  exit 1
fi

case $1 in
  major)
    version=$(awk -F. '{print $1+1 ".0.0"}-dev.1' abm/VERSION)
    ;;
  minor)
    version=$(awk -F. '{print $1 "." $2+1 ".0"}-dev.1' abm/VERSION)
    ;;
  patch)
    version=$(awk -F. '{print $1 "." $2 "." $3+1}-dev.1' abm/VERSION)
    ;;
  dev)
    version=$(awk -F. '{print $1 "." $2 "." $3 "." $4+1}' abm/VERSION)
    ;;
  release)
    version=$(awk -F- '{print $1}' abm/VERSION)
    ;;
  help)
    help
    exit
    ;;
  *)
    echo "Invalid option $1"
    exit 1
    ;;
esac
echo $version | tee abm/VERSION
