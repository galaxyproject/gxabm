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
	python3 -m build
    
clean:
	@rm -rf dist/ build/ gxabm.egg-info/

format:
	black -S abm/
	isort abm/
	
test-deploy:
	twine upload -r pypitest dist/*
    
deploy:
	twine upload -r pypi dist/*

tag:
	bin/tag.sh
