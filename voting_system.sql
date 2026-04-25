-- Create database and schema (idempotent)
CREATE DATABASE IF NOT EXISTS `voting_system` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `voting_system`;

-- Drop existing objects (safe for fresh start)
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS election_voters;
DROP TABLE IF EXISTS votes;
DROP TABLE IF EXISTS archive_voters;
DROP TABLE IF EXISTS candidates;
DROP TABLE IF EXISTS voters;
DROP TABLE IF EXISTS elections;
DROP TABLE IF EXISTS admin_settings;
DROP TABLE IF EXISTS admins;
SET FOREIGN_KEY_CHECKS = 1;

-- Admins table
CREATE TABLE IF NOT EXISTS admins (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Admin settings
CREATE TABLE IF NOT EXISTS admin_settings (
  id INT PRIMARY KEY,
  results_published TINYINT(1) DEFAULT 0
) ENGINE=InnoDB;

-- Elections table
CREATE TABLE IF NOT EXISTS elections (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  area VARCHAR(255),
  start_time DATETIME,
  end_time DATETIME,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Voters table (active voters)
CREATE TABLE IF NOT EXISTS voters (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(255) NOT NULL,
  voter_id VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  has_voted BOOLEAN DEFAULT FALSE,
  registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  election_id INT NULL,
  INDEX idx_voters_election (election_id)
) ENGINE=InnoDB;

-- Candidates table
CREATE TABLE IF NOT EXISTS candidates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  candidate_name VARCHAR(255) NOT NULL,
  party_name VARCHAR(255),
  election_id INT,
  FOREIGN KEY (election_id) REFERENCES elections(id)
) ENGINE=InnoDB;

-- Votes table
CREATE TABLE IF NOT EXISTS votes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  voter_id INT,
  candidate_id INT,
  election_id INT,
  FOREIGN KEY (voter_id) REFERENCES voters(id),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id),
  FOREIGN KEY (election_id) REFERENCES elections(id)
) ENGINE=InnoDB;

-- Link table (optional) election_voters
CREATE TABLE IF NOT EXISTS election_voters (
  election_id INT NOT NULL,
  voter_id INT NOT NULL,
  PRIMARY KEY (election_id, voter_id),
  INDEX idx_ev_voter (voter_id)
) ENGINE=InnoDB;

-- Archive voters table (for completed elections)
CREATE TABLE IF NOT EXISTS archive_voters (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  voter_id VARCHAR(50) NOT NULL,
  email VARCHAR(100) NOT NULL,
  password VARCHAR(255) NOT NULL,
  has_voted TINYINT(1) DEFAULT 0,
  registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  election_id INT NULL,
  INDEX idx_archive_election (election_id)
) ENGINE=InnoDB;

-- Add foreign keys (after tables exist)
ALTER TABLE voters
  ADD CONSTRAINT fk_voters_election FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE SET NULL;

ALTER TABLE candidates
  ADD CONSTRAINT fk_candidates_election FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE;

ALTER TABLE votes
  ADD CONSTRAINT fk_votes_voter FOREIGN KEY (voter_id) REFERENCES voters(id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_votes_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_votes_election FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE;

ALTER TABLE election_voters
  ADD CONSTRAINT fk_ev_election FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_ev_voter FOREIGN KEY (voter_id) REFERENCES voters(id) ON DELETE CASCADE;

ALTER TABLE archive_voters
  ADD CONSTRAINT fk_archive_election FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE SET NULL;

-- Seed default admin and settings (only if not exists)
INSERT INTO admins (username, password)
SELECT 'admin', 'admin@123' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM admins WHERE username = 'admin');

INSERT INTO admin_settings (id, results_published)
SELECT 1, 0 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM admin_settings WHERE id = 1);

-- Quick verification output (optional, remove if you paste into Workbench)
SELECT 'Schema ready' AS note;