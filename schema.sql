-- Video Portal schema (MariaDB / MySQL)
CREATE DATABASE IF NOT EXISTS videoportal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE videoportal;

CREATE TABLE IF NOT EXISTS users (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role ENUM('admin', 'manager', 'farmer') NOT NULL,
    mobile_no VARCHAR(64) NULL,
    id_card_no VARCHAR(128) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_by INT UNSIGNED NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS manager_farmers (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    manager_id INT UNSIGNED NOT NULL,
    farmer_id INT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_manager_farmer (manager_id, farmer_id),
    CONSTRAINT fk_mf_manager FOREIGN KEY (manager_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_mf_farmer FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS videos (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    original_filename VARCHAR(512) NOT NULL,
    stored_path VARCHAR(1024) NOT NULL,
    farmer_id INT UNSIGNED NOT NULL,
    uploader_id INT UNSIGNED NOT NULL,
    status ENUM('uploaded', 'ready') NOT NULL DEFAULT 'uploaded',
    recorded_at DATETIME NOT NULL,
    uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ready_at DATETIME NULL,
    CONSTRAINT fk_videos_farmer FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_videos_uploader FOREIGN KEY (uploader_id) REFERENCES users(id) ON DELETE RESTRICT,
    INDEX idx_videos_status (status),
    INDEX idx_videos_recorded (recorded_at),
    INDEX idx_videos_farmer (farmer_id),
    INDEX idx_videos_uploader (uploader_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS upload_consents (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    video_id INT UNSIGNED NOT NULL,
    uploader_id INT UNSIGNED NOT NULL,
    accepted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    terms_version VARCHAR(64) NOT NULL,
    CONSTRAINT fk_consent_video FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    CONSTRAINT fk_consent_uploader FOREIGN KEY (uploader_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS manager_agreements (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    manager_id INT UNSIGNED NOT NULL,
    docusign_envelope_id VARCHAR(128) NULL,
    status ENUM('pending', 'completed', 'declined') NOT NULL DEFAULT 'pending',
    signed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_agreement_manager FOREIGN KEY (manager_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_agreement_manager (manager_id),
    INDEX idx_agreement_status (status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS settings (
    `key` VARCHAR(128) NOT NULL PRIMARY KEY,
    `value` TEXT NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by INT UNSIGNED NULL,
    CONSTRAINT fk_settings_user FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

INSERT INTO settings (`key`, `value`) VALUES
    ('site_name', 'Video Portal'),
    ('support_contact', ''),
    ('consent_terms', 'I confirm that I have collected this video from the named farmer, that the farmer consented to recording farm work, and that I am authorized to upload this video to the Video Portal for operational use.'),
    ('terms_version', '1'),
    ('max_upload_mb', '500'),
    ('allowed_extensions', 'mp4,mov,avi,mkv,webm'),
    ('timezone_display', 'UTC'),
    ('docusign_template_id', ''),
    ('docusign_return_path', '/agreements/callback'),
    ('enable_farmer_download', '1')
ON DUPLICATE KEY UPDATE `key` = `key`;
