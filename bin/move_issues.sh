#!/usr/bin/env bash

GH=/usr/local/bin/gh

if [[ $# = 0 ]] ; then
	echo "USAGE: $(basename $0) --from MILESTONE --to MILESTONE"
	exit
fi

while [[ $# > 0 ]] ; do
	case $1 in
		-t|--to)
			TO_MILESTONE=$2
			;;
		-f|--from)
			FROM_MILESTONE=$2
			;;
		*)
			echo "Invalid option $1"
			exit 1
			;;
	esac
	shift 2
done

if [[ -z "$FROM_MILESTONE" ]] ; then
	echo "FROM milestone not provided"
	exit 1
fi
if [[ -z "$TO_MILESTONE" ]] ; then
	echo "TO milestone not provided"
	exit 1
fi
echo "Reassigning issues from milestone $FROM_MILESTONE to milestone $TO_MILESTONE"
set -eu

CHECK=$($GH milestone list --json title | jq -r '.[] | .title' | grep $TO_MILESTONE)
#echo "Check: $CHECK"
if [[ -z "$CHECK" ]] ; then
	$GH milestone create --title $TO_MILESTONE
	echo "Created the milestone $TO_MILESTONE"
else
	echo "The milestone $TO_MILESTONE already exists"
fi

ISSUES=$($GH issue list --milestone $FROM_MILESTONE --json number | jq -r '.[] | .number')
for issue in $ISSUES ; do
	$GH issue edit $issue --milestone $TO_MILESTONE > /dev/null
	echo "Assigned #$issue to milestone $TO_MILESTONE"
done
echo "Done"