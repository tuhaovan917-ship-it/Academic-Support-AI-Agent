# Stage 24 - Expanded Retrieval Audit Summary

## Goal

Mo rong bo kiem thu truy xuat len 100 cau hoi de bao phu nhieu chu de cua Task 1.2 truoc khi cleanup cac artifact du.

## Input

- `data/review/audit_cases.jsonl`
- `huit_db/` collection `huit_academic_chunks`
- `scripts/audit_retrieval.py`
- `src/retriever.py`

## Process

1. Mo rong bo audit tu 50 len 100 cau hoi, giu `case_id` duy nhat.
2. Bao phu cac nhom:
   - Quy dinh hien hanh tu QD-3344.
   - Huong dan hoc vu 2026.
   - Bieu mau BM02, BM03, BM04, BM08, BM10, BM11, BM12.
   - Nguon pending: BM09, QD-3297, QD-2658.
   - Nguon discarded: QD-3230.
3. Chay audit lan dau voi 100 cau hoi, ket qua 91/100.
4. Phan tich 9 case fail va dieu chinh rerank/hint:
   - Chi ap dung article hint manh cho `current_policy`, khong de no lan at form/guidance trong cau hoi thu tuc.
   - Tang uu tien guidance khi cau hoi hoi ve quy trinh/thu tuc.
   - Tang uu tien form khi cau hoi hoi "dung mau/phieu/bieu mau".
   - Tinh chinh mot so hint dieu khoan de tranh nham lan giua Dieu 15/17, Dieu 21/32, Dieu 34/42, Dieu 41/18.
5. Dong bo logic giua `scripts/audit_retrieval.py` va `src/retriever.py`.
6. Chay `compileall` va audit lai 100 cau hoi.

## Output

- `data/review/audit_cases.jsonl`: 100 audit cases, 100 unique case IDs.
- `data/review/stage24_expanded_audit_plan.md`: ke hoach mo rong audit.
- `data/review/retrieval_audit_report.json`: ket qua audit chi tiet moi nhat.
- `data/review/retrieval_audit_report.md`: bao cao audit dang Markdown.
- `data/review/stage24_expanded_audit_summary.md`: tong ket Stage 24.
- Updated `scripts/audit_retrieval.py`.
- Updated `src/retriever.py`.

## Result

- Total cases: 100
- Passed cases: 100
- Failed cases: 0
- Active cases: 96
- Pending-source cases: 3
- Discarded-source cases: 1
- Collection count: 141

## Verification

```powershell
$env:PYTHONIOENCODING="utf-8"
.\venv\Scripts\python.exe -m compileall scripts src tests
.\venv\Scripts\python.exe scripts\audit_retrieval.py
```

Both checks passed.

## Notes

- QD-3230 van duoc giu la `discarded_source` trong audit theo quyet dinh cua user, khong dung cho cau tra loi quy dinh hien hanh.
- BM09, QD-3297, QD-2658 van la pending-source, khong dua vao cau tra loi hien hanh neu chua duoc duyet.
- Chua thuc hien cleanup file/thu muc du trong Stage 24.

## Recommended Next Stage

Stage 25 nen la cleanup co kiem soat:

1. Lap danh sach file/thu muc du kien don dep, dac biet cac artifact cua QD-3230.
2. Xac nhan voi user truoc khi xoa/di chuyen.
3. Sau cleanup, chay lai `compileall`, final audit 100 cases va final readiness report.
