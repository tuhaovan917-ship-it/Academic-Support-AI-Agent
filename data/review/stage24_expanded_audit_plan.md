# Stage 24 - Expanded Retrieval Audit Plan

## Input

- Existing audit cases: `data/review/audit_cases.jsonl`
- Current vector DB: `huit_db`
- Primary current regulation: `huit_qd_3344_2025`

## Output

- Added cases: `0`
- Total cases: `100`

## Coverage

- By status: `{'active': 96, 'pending_source': 3, 'discarded_source': 1}`
- By expected document: `{'huit_qd_3344_2025': 80, 'huit_guidance_course_registration_2026': 3, 'huit_guidance_academic_status_2026': 4, 'huit_guidance_academic_results_2026': 2, 'huit_form_bm02_return_to_study': 1, 'huit_form_bm03_change_major': 1, 'huit_form_bm04_dual_program': 1, 'huit_form_bm08_change_training_system': 1, 'huit_form_bm10_cancel_course': 1, 'huit_form_bm11_exemption_credit_recognition': 1, 'huit_form_bm12_graduation_application': 1, 'huit_form_bm09_exam_postponement': 1, 'huit_qd_3230_foreign_language_outcomes_2023': 1, 'huit_qd_3297_it_outcomes_2023': 1, 'huit_qd_2658_student_affairs_2023': 1}`

## Process

1. Added 50 new cases covering definitions, program structure, registration limits, leave, transfer, assessment tables, GPA, thesis, graduation, storage, inspection, and reward rules.
2. Kept pending/discarded cases in the suite to ensure blocked sources stay out of current-policy answers.
3. Next command should run `scripts/audit_retrieval.py` and inspect any failures.
