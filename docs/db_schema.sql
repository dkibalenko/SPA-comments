-- SPA Comments — Database Schema
-- Compatible with MySQL Workbench "Reverse Engineer from SQL Script"
-- (Database → Reverse Engineer → "Import SQL Script")
--
-- Original DB: PostgreSQL 16
-- Type mapping: UUID→CHAR(36), INET→VARCHAR(45), TIMESTAMPTZ→DATETIME
-- CAPTCHA tokens are NOT stored in the database; they live in Redis (TTL 300s).

CREATE DATABASE IF NOT EXISTS comments_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE comments_db;

-- ─── users_user ──────────────────────────────────────────────────────────────
CREATE TABLE users_user (
    id           CHAR(36)     NOT NULL,
    username     VARCHAR(50)  NOT NULL,
    email        VARCHAR(254) NOT NULL,
    home_page    VARCHAR(200)     NULL,
    ip_address   VARCHAR(45)  NOT NULL,
    user_agent   TEXT         NOT NULL,
    created_at   DATETIME     NOT NULL,

    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username_email (username, email),
    INDEX idx_users_username (username),
    INDEX idx_users_email    (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ─── comments_comment ────────────────────────────────────────────────────────
CREATE TABLE comments_comment (
    id         CHAR(36) NOT NULL,
    user_id    CHAR(36) NOT NULL,
    parent_id  CHAR(36)     NULL,
    text       TEXT     NOT NULL,
    created_at DATETIME NOT NULL,

    PRIMARY KEY (id),
    INDEX idx_comments_parent       (parent_id),
    INDEX idx_comments_created_desc (created_at DESC),
    CONSTRAINT fk_comment_user   FOREIGN KEY (user_id)   REFERENCES users_user     (id),
    CONSTRAINT fk_comment_parent FOREIGN KEY (parent_id) REFERENCES comments_comment (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ─── attachments_attachment ──────────────────────────────────────────────────
CREATE TABLE attachments_attachment (
    id                CHAR(36)     NOT NULL,
    comment_id        CHAR(36)     NOT NULL,
    file_type         VARCHAR(10)  NOT NULL,
    storage_path      VARCHAR(100) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    created_at        DATETIME     NOT NULL,

    PRIMARY KEY (id),
    UNIQUE KEY uq_attachment_comment (comment_id),
    CONSTRAINT fk_attachment_comment FOREIGN KEY (comment_id) REFERENCES comments_comment (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
