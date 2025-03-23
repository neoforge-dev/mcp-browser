build:
	docker-compose build

run:
	docker-compose up -d

test:
	docker-compose exec mcp-browser pytest tests/ -v

publish:
	docker login -u ${DOCKER_USER} -p ${DOCKER_PASS}
	docker tag mcp-browser neoforge-dev/mcp-browser:$(shell git rev-parse --short HEAD)
	docker push neoforge-dev/mcp-browser

generate-secret:
	@echo "MCP_SECRET=$(shell openssl rand -hex 32)" > .env

security-check:
	docker run --rm -it \
	  --security-opt apparmor=mcp-browser \
	  --entrypoint=lynis \
	  neoforge-dev/mcp-browser:latest audit system