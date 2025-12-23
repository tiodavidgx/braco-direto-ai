-- Criar tabela de usuários para autenticação
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user', -- 'admin', 'user', 'viewer'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Inserir usuário admin padrão (senha: admin123)
-- A senha será hasheada pelo backend, mas para começar vamos usar um hash bcrypt
-- Hash de 'admin123' com bcrypt
INSERT INTO users (username, email, password_hash, full_name, role)
VALUES (
    'admin',
    'admin@suportedg.site',
    '$2b$12$LQv3c1yqBwwOVFp1z.IYeOiX8Q0KL6C2HzU6LbZJTH8fLXWXO.Sd2',
    'Administrador',
    'admin'
) ON CONFLICT (username) DO NOTHING;

-- Comentário: Para criar novos usuários, use a API ou execute:
-- INSERT INTO users (username, email, password_hash, full_name, role)
-- VALUES ('usuario', 'email@example.com', '<hash_bcrypt>', 'Nome Completo', 'user');
