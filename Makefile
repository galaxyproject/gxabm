.PHONY: dist
help:
	@echo
	@echo "GOALS"
	@echo "    clean       - deletes the dist directory and egg-info"
	@echo "    dist        - creates the distribution package (wheel)"
	@echo "    format      - runs Black and isort"
	@echo "    test-deploy - deploys to test.pypi.org"
	@echo "    deploy      - deploys to pypi.org"
	@echo "    tag         - creates a GitHub tag for the current commit"
	@echo
	
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

tag:
	bin/tag.sh
