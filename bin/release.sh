#!/usr/bin/env bash

tag_name="v$(cat abm/VERSION)"
git tag -a -m "Release $tag_name" $tag_name
git push origin $tag_name
gh release create $tag_name --generate-notes