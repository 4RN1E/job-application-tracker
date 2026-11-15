-- =====================================================================
-- Optional demo data. Run AFTER schema.sql:
--     mysql -u root -p job_tracker < seed.sql
-- All companies, people and URLs below are fictional.
-- =====================================================================

USE job_tracker;

INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('TechCorp',      'Software',   'https://www.techcorp.example',   'Miami',   'Florida',  'Referred by a CodePath mentor.'),
('DataCo',        'Analytics',  'https://www.dataco.example',     'Orlando', 'Florida',  'Remote-friendly data team.'),
('Harbor Cloud',  'Cloud',      'https://www.harborcloud.example','Tampa',   'Florida',  NULL),
('Bayou Systems', 'Consulting', 'https://www.bayousys.example',   'New Orleans', 'Louisiana', 'Met at a career fair.');

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Software Developer',     'Full-time',  75000, 95000, 'https://www.techcorp.example/jobs/101',   CURDATE() - INTERVAL 12 DAY, JSON_ARRAY('Python','SQL','Flask')),
(2, 'Data Analyst',           'Full-time',  65000, 80000, 'https://www.dataco.example/careers/7',    CURDATE() - INTERVAL 9 DAY,  JSON_ARRAY('Python','SQL','Tableau')),
(3, 'Backend Engineer Intern','Internship', 25,    30,    'https://www.harborcloud.example/intern', CURDATE() - INTERVAL 20 DAY, JSON_ARRAY('Python','Docker','AWS','Git')),
(3, 'Cloud Support Engineer', 'Full-time',  70000, 90000, NULL,                                      CURDATE() - INTERVAL 3 DAY,  JSON_ARRAY('Linux','AWS','Bash')),
(4, 'Integration Developer',  'Contract',   90000, 120000,'https://www.bayousys.example/jobs/42',    CURDATE() - INTERVAL 5 DAY,  JSON_ARRAY('Java','SQL','REST','Git'));

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
(1, CURDATE() - INTERVAL 10 DAY, 'Interview',  'v3-software', TRUE,
    JSON_OBJECT('date', DATE_FORMAT(CURDATE() + INTERVAL 4 DAY, '%Y-%m-%d'),
                'type', 'Video call', 'interviewer', 'Dana Lee',
                'notes', 'Expect Flask and SQL questions.')),
(2, CURDATE() - INTERVAL 8 DAY,  'Screening',  'v2-data',     FALSE, NULL),
(3, CURDATE() - INTERVAL 18 DAY, 'Rejected',   'v3-software', TRUE,  NULL),
(4, CURDATE() - INTERVAL 2 DAY,  'Applied',    'v3-software', FALSE, NULL),
(5, CURDATE() - INTERVAL 4 DAY,  'Offer',      'v3-software', TRUE,
    JSON_OBJECT('date', DATE_FORMAT(CURDATE() - INTERVAL 1 DAY, '%Y-%m-%d'),
                'type', 'On-site', 'interviewer', 'Marcus Boudreaux',
                'notes', 'Went well; offer expected this week.'));

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) VALUES
(1, 'Dana Lee',         'Engineering Manager', 'dana.lee@techcorp.example',        '305-555-0142', 'https://www.linkedin.com/in/dana-lee-example',  'Hiring manager for the developer role.'),
(2, 'Priya Raman',      'Technical Recruiter', 'priya.raman@dataco.example',       NULL,           NULL,                                            NULL),
(3, 'Tom Alvarez',      'University Recruiter','tom.alvarez@harborcloud.example',  '813-555-0199', NULL,                                            'Sent a polite rejection; keep in touch for next cycle.'),
(4, 'Marcus Boudreaux', 'Senior Consultant',   'marcus.b@bayousys.example',        '504-555-0123', NULL,                                            'Met at the career fair.');
