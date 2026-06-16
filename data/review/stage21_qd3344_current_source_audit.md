# Stage 21 - QĐ-3344 Current Source Audit

## Decision

- Status: `pass`
- QĐ-3344 remains the primary current legal source for HUIT academic-policy answers.
- The supplied PDF contains Articles 1-44 and the attached-form index; Articles 45-46 were not found in this file.
- QĐ-3230 was marked as discarded/do-not-process per user instruction.

## Input

- Chunk source: `data\processed_chunks_enriched.jsonl`
- Review decision file: `data\review\source_review_decisions.yaml`

## Output

- JSON audit: `data\review\stage21_qd3344_current_source_audit.json`
- Markdown audit: `data\review\stage21_qd3344_current_source_audit.md`

## Coverage

- QĐ-3344 chunk count: 70
- Article count detected: 44/46
- Unit types: {'legal_article': 37, 'legal_clause': 33}
- Missing articles: none

## Metadata And Citation

- Metadata issues: 0
- Citation format issues: 0
- Expected citation date format: `ngày dd/mm/yyyy`.

## Critical Checks

- article_18_training_time_table_present: pass
- article_30_academic_warning_present: pass
- article_34_exam_absence_or_postponement_present: pass
- article_39_graduation_conditions_present: pass
- article_40_five_percent_rule_present: pass
- article_44_final_article_present: pass

## Table Review

- Table-bearing chunks detected: 5
- Chunks with flattened symbols/math likely needing cleanup: 0
- Article 18, `huit_qd_3344_2025:legal_article:article_18:fdaecb0cbcdc3ecd`: ok/acceptable
- Article 21, `huit_qd_3344_2025:legal_clause:article_21_clause_2:b2b2e00542665387`: ok/acceptable
- Article 30, `huit_qd_3344_2025:legal_clause:article_30_clause_4:060beb13d7769fda`: ok/acceptable
- Article 30, `huit_qd_3344_2025:legal_clause:article_30_clause_5:0534610bcdb9261e`: ok/acceptable
- Article 32, `huit_qd_3344_2025:legal_article:article_32:62c51a457fd580a5`: ok/acceptable

## Recommended Next Stage

Stage 22 should perform targeted cleanup for QĐ-3344 table-heavy chunks only, especially formulas and converted tables, then rerun retrieval audit.
