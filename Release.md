# GXABM Release Process

The `master` branch is used for releases and points to the latest tagged commit. The current version number is maintained in `abm/VERSION`. The `dev` branch is used for development.

You can use the `bin/bump.sh` script to update the version number as needed. Run `bin/bump.sh --help` for more information.

## To perform a release

To perform a release, follow these steps
1. Merge the `dev` branch into `master`.<br/>`git checkout master`<br/>`git merge dev`
2. Update the version number in `abm/VERSION`.<br/>`bin/bump.sh release`
3. Commit and push the changes to `origin master`.<br/>`git add abm/VERSION`<br/>`git commit -m "Release $(cat abm/VERSION)"`<br/>`git push origin master`
4. Use the `make` command to build and deploy the release.<br/>`make clean build deploy release`<br/>The `deploy` goal deploys `gxabm` to PyPi. The `release` goal tags the current commit using the version defined in `abm/VERSION` and creates a release on GitHub using the `bin/release.sh` script.
5. Switch back to the `dev` branch and merge the `master` branch into `dev`.<br/>`git checkout dev`<br/>`git merge master`
6. Update the version number in `abm/VERSION` to the next dev version and push to `origin dev`.<br/>`bin/bump.sh next`<br/>`git add abm/VERSION`<br/>`git commit -m "Bump version to $(cat abm/VERSION)"`<br/>`git push origin dev`
7. [Optional] use the `bin/move_issues.sh` script to move all open issues from the current  milestone to the next milestone.  For example, to move all issues from the 2.10 milestone to the 2.11 milestone use:<br/>`bin/move_issues.sh --from 2.10 --to 2.11`<br/>If the `--to` milestone does not exist it will be created.