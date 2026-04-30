.PHONY: dist docker
help:
	@echo
	@echo "GOALS"
	@echo "    clean       - deletes the dist directory and egg-info"
	@echo "    dist        - creates the distribution package (wheel)"
	@echo "    format      - runs Black and isort"
	@echo "    test-deploy - deploys to test.pypi.org"
	@echo "    deploy      - deploys to pypi.org"
	@echo "    docker      - builds the Docker image"
	@echo "    push-docker - push images to docker.io"
	@echo "    push-quay   - push images to quay.io"
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

docker:
	$(eval VERSION := $(shell cat abm/VERSION))
	docker build --platform linux/amd64 -t ksuderman/gxabm:$(VERSION) -t ksuderman/gxabm:latest .
	docker build --platform linux/amd64 -t quay.io/galaxyproject/abm:$(VERSION) -t quay.io/galaxyproject/abm:latest .

push-docker:
	$(eval VERSION := $(shell cat abm/VERSION))
	docker push ksuderman/gxabm:$(VERSION)
	docker push ksuderman/gxabm:latest

push-quay:
	$(eval VERSION := $(shell cat abm/VERSION))
	docker push quay.io/galaxyproject/abm:$(VERSION)
	docker push quay.io/galaxyproject/abm:latest

#tag:
#	bin/tag.sh
