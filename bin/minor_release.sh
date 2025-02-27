#!/usr/bin/env bash

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
bin/bump.sh next
git add abm/VERSION
git commit -m "Bump to next dev version $(cat abm/VERSION)"
git push origin dev

# Move any remaining open issues to a new milestone
milestone=$(awk -F- '{print $1}' abm/VERSION)
bin/move_issues.sh --from $release --to $milestone


