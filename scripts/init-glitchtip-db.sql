-- Creates the glitchtip database on first postgres init (docker-entrypoint-initdb.d/).
-- For existing volumes: docker compose exec postgres createdb -U atlas glitchtip
SELECT 'CREATE DATABASE glitchtip'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'glitchtip')\gexec
