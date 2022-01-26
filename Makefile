.PHONY: dist
dist:
	python3 setup.py sdist bdist_wheel
    
clean:
	@if [ -e dist/ ] ; then rm -rf dist/ ; fi
	@if [ -e gxabm.egg-info ] ; then rm -rf gxabm.egg-info ; fi

test-deploy:
	twine upload -r pypitest dist/*
    
deploy:
	twine -r pypi upload dist/*
