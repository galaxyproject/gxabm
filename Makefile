.PHONY: dist
dist:
	python3 setup.py sdist bdist_wheel
    
clean:
	@if [ -e dist/ ] ; then rm -rf dist/ ; fi
	@if [ -e gxabm.egg-info ] ; then rm -rf gxabm.egg-info ; fi

test-deploy:
	twine upload -r pypitest dist/*
    
deploy:
	twine upload -r pypi dist/*

version:
	@./release.sh

release:
	tag_name="v$(cat abm/VERSION)"
	git tag -a -m "Automatic release of $tag_name" $tag_name
	git push origin $tag_name
	gh release create $tag_name --generate-notes
