-- Script para crear la base de datos PostgreSQL para el Adora
-- Ejecutar como superusuario de PostgreSQL

-- Crear base de datos
DROP DATABASE IF EXISTS Adora_db;
CREATE DATABASE Adora_db;

-- Conectar a la base de datos
\c Adora_db;

-- Crear usuario (opcional, si quieres un usuario específico)
-- DROP USER IF EXISTS Adora_user;
-- CREATE USER Adora_user WITH PASSWORD 'Adora_password';
-- GRANT ALL PRIVILEGES ON DATABASE Adora_db TO Adora_user;

-- Configurar encoding
ALTER DATABASE Adora_db SET client_encoding TO 'utf8';
ALTER DATABASE Adora_db SET default_transaction_isolation TO 'read committed';
ALTER DATABASE Adora_db SET timezone TO 'UTC';
