#!/usr/bin/env bash
set -eu

function help() {
  less -RX << EOF

USAGE: $0 [major|minor|patch]

The [major|minor|patch] argument specifies which portion of the version
number will be incremented for the next development version. Defaults to minor.

EXAMPLE:
  # If the current version in abm/VERSION is 2.10.9 then
  $0 major # > 3.0.0-dev.1
  $0 minor # > 2.11.0-dev.1
  $0 patch # > 2.10.10-dev.1

EOF
}

# Get the type of release to perform. Default to minor.
type=minor
if [[ $# = 1 ]] ; then
  case $1 in
    major|minor|patch)
      type=$1
      ;;
    help)
      help
      exit 0
      ;;
    *)
      echo "Invalid option $1"
      help
      exit 1
      ;;
  esac
fi

# Ensure we have the latest updates from both dev and master before merging.
git checkout dev
git pull origin dev
git checkout master
git pull origin master
git merge dev

# Bump to a release version and push to GitHub
bin/bump.sh release
release=$(cat abm/VERSION)
tag="v$release"
git add abm/VERSION
git commit -m "Release $release"
git push origin master

# Build and deploy the release to PyPI
make clean build deploy

# Create a release on GitHub
git tag -a -m "Release $tag" $tag
git push origin $tag_name
gh release create $tag --generate-notes

# Set up the next dev version
git checkout dev
bin/bump.sh $type
git add abm/VERSION
git commit -m "Bump to next dev version $(cat abm/VERSION)"
git push origin dev

# Move any remaining open issues to a new milestone
milestone=$(awk -F- '{print $1}' abm/VERSION)
bin/move_issues.sh --from $release --to $milestone


