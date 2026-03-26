-- Esquema para o novo app (multiusuário + Google OAuth)
CREATE TABLE IF NOT EXISTS app_usuarios (
    id INT PRIMARY KEY AUTO_INCREMENT,
    google_sub VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    nome VARCHAR(255),
    timezone VARCHAR(64) DEFAULT 'America/Sao_Paulo',
    resumo_diario_ativo BOOLEAN DEFAULT TRUE,
    resumo_diario_hora TIME DEFAULT '18:00:00',
    ultimo_resumo_enviado_em DATETIME NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_tokens_google (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expiry DATETIME NULL,
    scope TEXT,
    token_type VARCHAR(20),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_usuario_token (usuario_id),
    FOREIGN KEY (usuario_id) REFERENCES app_usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS app_compromissos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    descricao VARCHAR(1000),
    data DATE NOT NULL,
    hora TIME NOT NULL,
    local VARCHAR(255),
    google_event_id VARCHAR(200),
    texto_original TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_usuario_data (usuario_id, data),
    FOREIGN KEY (usuario_id) REFERENCES app_usuarios(id) ON DELETE CASCADE
);
