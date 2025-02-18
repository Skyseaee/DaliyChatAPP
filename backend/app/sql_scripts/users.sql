INSERT INTO users (user_id, username, password_hash)
VALUES 
    ('550e8400-e29b-41d4-a716-446655440000', 'user1', 'pbkdf2:sha256:260000$abcdefgh$1234567890abcdef1234567890abcdef1234567890abcdef'),
    ('550e8400-e29b-41d4-a716-446655440001', 'user2', 'pbkdf2:sha256:260000$hijklmno$1234567890abcdef1234567890abcdef1234567890abcdef');