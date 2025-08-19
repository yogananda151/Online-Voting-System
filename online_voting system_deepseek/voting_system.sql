CREATE DATABASE IF NOT EXISTS voting_system;
USE voting_system;

-- Voters Table
CREATE TABLE voters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    voter_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    has_voted BOOLEAN DEFAULT FALSE,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Admins Table
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);
INSERT INTO admins (username, password) VALUES ('admin', 'admin@123');

-- Elections Table
CREATE TABLE elections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);
ALTER TABLE elections
    ADD COLUMN start_time DATETIME AFTER name,
    ADD COLUMN end_time DATETIME AFTER start_time,
    ADD COLUMN area VARCHAR(100) AFTER end_time;

-- Candidates Table
CREATE TABLE candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_name VARCHAR(100) NOT NULL,
    party_name VARCHAR(100) NOT NULL,
    photo_path VARCHAR(255),
    symbol_path VARCHAR(255),
    election_id INT NOT NULL,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
);

-- Votes Table
CREATE TABLE votes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    voter_id INT NOT NULL,
    candidate_id INT NOT NULL,
    election_id INT NOT NULL,
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (voter_id) REFERENCES voters(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    UNIQUE (voter_id, election_id)
);

-- Admin Settings Table (for result publishing)
CREATE TABLE admin_settings (
    id INT PRIMARY KEY,
    results_published BOOLEAN DEFAULT FALSE
);

INSERT INTO admin_settings (id, results_published) VALUES (1, FALSE)
    ON DUPLICATE KEY UPDATE results_published=results_published;
    
SELECT * FROM elections;

SELECT * FROM admin_settings;
INSERT INTO admin_settings (id, results_published) VALUES (1, FALSE);