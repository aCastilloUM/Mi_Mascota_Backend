.PHONY: bootstrap up down logs test lint migrate

bootstrap:
\tpnpm install

up:
\tdocker compose up -d

down:
\tdocker compose down -v

logs:
\tdocker compose logs -f

lint:
\tpnpm -r lint

test:
\tpnpm -r test

migrate:
\tpnpm --filter auth-svc migrate:run
