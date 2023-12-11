.PHONY: dist
dist:
	python3 setup.py sdist bdist_wheel
    
clean:
	@if [ -e dist/ ] ; then rm -rf dist/ ; fi
	@if [ -e gxabm.egg-info ] ; then rm -rf gxabm.egg-info ; fi

format:
	black -S abm/
	isort abm/
	
test-deploy:
	twine upload -r pypitest dist/*
    
deploy:
	twine upload -r pypi dist/*

release:
	./release.sh
