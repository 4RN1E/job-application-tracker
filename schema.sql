-- =====================================================================
-- Job Application Tracker - database schema
--
-- Run with:  mysql -u root -p < schema.sql
--
-- WARNING: this script DROPS and recreates the four tables, so running it
-- again resets the database to empty. Use seed.sql afterwards for demo data.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS job_tracker
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE job_tracker;

-- Drop in reverse dependency order (children before parents)
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS companies;

-- ---------------------------------------------------------------------
-- companies: one row per employer
-- ---------------------------------------------------------------------
CREATE TABLE companies (
    company_id    INT          PRIMARY KEY AUTO_INCREMENT,
    company_name  VARCHAR(100) NOT NULL,
    industry      VARCHAR(50),
    website       VARCHAR(200),
    city          VARCHAR(50),
    state         VARCHAR(50),
    notes         TEXT
);

-- ---------------------------------------------------------------------
-- jobs: a posting at a company
--   requirements is a JSON array of skill names, e.g. ["Python","SQL"]
--   (the Job Match feature compares your skills against this array)
-- ---------------------------------------------------------------------
CREATE TABLE jobs (
    job_id        INT          PRIMARY KEY AUTO_INCREMENT,
    company_id    INT          NOT NULL,
    job_title     VARCHAR(100) NOT NULL,
    job_type      ENUM('Full-time','Part-time','Contract','Internship') NOT NULL DEFAULT 'Full-time',
    salary_min    INT,
    salary_max    INT,
    job_url       VARCHAR(300),
    date_posted   DATE,
    requirements  JSON,
    CONSTRAINT fk_jobs_company
        FOREIGN KEY (company_id) REFERENCES companies (company_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_jobs_salary
        CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max)
);

-- ---------------------------------------------------------------------
-- applications: your application to a job
--   interview_data is a JSON object, e.g.
--   {"date":"2026-11-20","type":"Video call","interviewer":"Dana Lee","notes":"..."}
-- ---------------------------------------------------------------------
CREATE TABLE applications (
    application_id    INT         PRIMARY KEY AUTO_INCREMENT,
    job_id            INT         NOT NULL,
    application_date  DATE        NOT NULL,
    status            ENUM('Applied','Screening','Interview','Offer','Accepted','Rejected','Withdrawn')
                                  NOT NULL DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN     NOT NULL DEFAULT FALSE,
    interview_data    JSON,
    CONSTRAINT fk_applications_job
        FOREIGN KEY (job_id) REFERENCES jobs (job_id)
        ON DELETE CASCADE,
    INDEX idx_applications_status (status)
);

-- ---------------------------------------------------------------------
-- contacts: people you know at a company (recruiters, referrals, ...)
-- ---------------------------------------------------------------------
CREATE TABLE contacts (
    contact_id    INT          PRIMARY KEY AUTO_INCREMENT,
    company_id    INT          NOT NULL,
    contact_name  VARCHAR(100) NOT NULL,
    title         VARCHAR(100),
    email         VARCHAR(100),
    phone         VARCHAR(20),
    linkedin_url  VARCHAR(200),
    notes         TEXT,
    CONSTRAINT fk_contacts_company
        FOREIGN KEY (company_id) REFERENCES companies (company_id)
        ON DELETE CASCADE
);
