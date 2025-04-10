.PHONY: build test test-network clean run

build:
	docker-compose build

run: build
	RUN_TESTS=false docker-compose up -d

test: build
	@export RUN_TESTS=true && docker-compose up --exit-code-from mcp-browser --abort-on-container-exit

test-network: build
	@export RUN_TESTS=true && docker-compose up -d
	docker-compose exec mcp-browser pytest /app/tests/test_network_isolation.py -v

clean:
	docker-compose down
	docker-compose rm -f

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