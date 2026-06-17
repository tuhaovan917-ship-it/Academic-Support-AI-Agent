# Student API Contract For Task 3

`STUDENT_API_PROVIDER=http` makes `ToolAgent` call these endpoints through `HttpStudentClient`.

## Config

```env
STUDENT_API_PROVIDER=http
STUDENT_API_BASE_URL=http://localhost:5000
STUDENT_API_TIMEOUT_SECONDS=10
STUDENT_API_TOKEN=
```

## Endpoints

### GET /students/{student_id}/profile

Expected response:

```json
{
  "found": true,
  "student_id": "SV004",
  "full_name": "Pham Dung",
  "major": "Cong nghe thong tin",
  "certificates": {
    "foreign_language": true,
    "gdtc": true,
    "gdqp": true
  },
  "disciplinary_warning": false
}
```

### GET /students/{student_id}/schedule?semester=2025-2026-2

Expected response:

```json
{
  "found": true,
  "student_id": "SV004",
  "schedule": [
    {
      "semester": "2025-2026-2",
      "day": "Friday",
      "time": "13:00-16:30",
      "course_code": "IT401",
      "course_name": "Do an phan mem",
      "room": "Lab 5",
      "lecturer": "ThS. Hoang Van E"
    }
  ]
}
```

### GET /students/{student_id}/grades?semester=2025-2026-2

Expected response:

```json
{
  "found": true,
  "student_id": "SV004",
  "cumulative_gpa": 3.45,
  "total_credits": 126,
  "retaken_credits": 9,
  "retake_ratio": 0.071,
  "courses": [],
  "failed_courses": []
}
```

### GET /students/{student_id}/graduation-snapshot

Expected response:

```json
{
  "found": true,
  "student_id": "SV004",
  "full_name": "Pham Dung",
  "major": "Cong nghe thong tin",
  "cumulative_gpa": 3.45,
  "total_credits": 126,
  "retaken_credits": 9,
  "retake_ratio": 0.071,
  "failed_courses": [],
  "missing_certificates": [],
  "eligible_for_graduation": true,
  "warnings": [
    "retake_ratio_over_5_percent"
  ]
}
```

For missing students, return either HTTP 404 or:

```json
{
  "found": false,
  "student_id": "SV999",
  "error": "student_not_found"
}
```
