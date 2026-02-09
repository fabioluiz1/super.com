-- Runs once on first container startup (docker-entrypoint-initdb.d).
-- Creates the test database used by pytest.
CREATE DATABASE super_test;
