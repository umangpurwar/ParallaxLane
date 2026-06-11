"""
Professional Excel assessment report generator for ParallaxLane.
"""
from collections import Counter
from io import BytesIO

from django.db.models import Prefetch
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from exams.models import Exam, ExamAttempt
from monitoring.models import Violation

PASS_PERCENTAGE = 50.0

VIOLATION_LABELS = {
    "tab_switch": "Tab Switch",
    "multiple_faces": "Multiple Faces",
    "no_face": "Camera Off",
    "phone_detected": "Phone Detected",
    "window_blur": "Window Focus Lost",
    "copy_paste": "Copy / Paste",
    "suspicious_movement": "Suspicious Movement",
    "fullscreen_exit": "Fullscreen Exit",
}

HEADER_FONT = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True)
CELL_ALIGNMENT = Alignment(vertical="top", wrap_text=True)
WRAP_ALIGNMENT = Alignment(vertical="top", wrap_text=True)
THIN_BORDER = Border(
    left=Side(style="thin", color="D9D9D9"),
    right=Side(style="thin", color="D9D9D9"),
    top=Side(style="thin", color="D9D9D9"),
    bottom=Side(style="thin", color="D9D9D9"),
)
TITLE_FONT = Font(name="Calibri", bold=True, size=14, color="1F3864")
SUBTITLE_FONT = Font(name="Calibri", bold=True, size=11, color="1F3864")
METRIC_FONT = Font(name="Calibri", bold=True, size=11)


def _candidate_name(user):
    full = f"{user.first_name} {user.last_name}".strip()
    return full or user.name or user.email or user.username


def _format_score(value):
    if value is None:
        return 0
    if float(value).is_integer():
        return int(value)
    return round(float(value), 1)


def _format_percentage(scored, total):
    if not total:
        return "0%"
    pct = round((float(scored) / float(total)) * 100, 1)
    if pct == int(pct):
        return f"{int(pct)}%"
    return f"{pct}%"


def _percentage_value(scored, total):
    if not total:
        return 0.0
    return round((float(scored) / float(total)) * 100, 1)


def _format_datetime(dt):
    if not dt:
        return "—"
    local_dt = timezone.localtime(dt)
    return local_dt.strftime("%d %b %Y, %I:%M %p")


def _format_duration(start, end):
    if not start or not end:
        return "—"
    total_secs = max(0, int((end - start).total_seconds()))
    hours, rem = divmod(total_secs, 3600)
    mins, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {mins}m {secs}s"
    return f"{mins}m {secs}s"


def _result_status(attempt, percentage):
    if attempt.status == "active" and not attempt.end_time:
        return "Incomplete"
    if attempt.status == "terminated":
        return "Fail"
    if percentage >= PASS_PERCENTAGE:
        return "Pass"
    return "Fail"


def _violation_label(violation_type):
    return VIOLATION_LABELS.get(violation_type, violation_type.replace("_", " ").title())


def _violation_summary(violations):
    if not violations:
        return "None"
    counts = Counter(v.violation_type for v in violations)
    parts = [f"{_violation_label(vtype)} ({count})" for vtype, count in counts.most_common()]
    return ", ".join(parts)


def _style_header_row(ws, row_num, col_count):
    for col in range(1, col_count + 1):
        cell = ws.cell(row=row_num, column=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER


def _apply_table_borders(ws, start_row, end_row, col_count):
    for row in range(start_row, end_row + 1):
        for col in range(1, col_count + 1):
            ws.cell(row=row, column=col).border = THIN_BORDER


def _auto_column_widths(ws, min_width=12, max_width=45):
    for col_cells in ws.columns:
        letter = get_column_letter(col_cells[0].column)
        lengths = []
        for cell in col_cells:
            if cell.value is not None:
                lengths.append(len(str(cell.value)))
        width = min(max(lengths + [min_width]), max_width)
        ws.column_dimensions[letter].width = width


def _build_candidate_rows(attempts):
    rows = []
    for attempt in attempts:
        user = attempt.user
        scored = attempt.points_scored or 0
        total = attempt.total_points or 0
        pct = _percentage_value(scored, total)
        violations = list(attempt.violations.all())

        rows.append({
            "name": _candidate_name(user),
            "email": user.email or user.username,
            "score": scored,
            "total": total,
            "percentage": pct,
            "percentage_display": _format_percentage(scored, total),
            "status": _result_status(attempt, pct),
            "duration": _format_duration(attempt.start_time, attempt.end_time),
            "attempt_date": _format_datetime(attempt.start_time),
            "submission_time": _format_datetime(attempt.end_time),
            "risk_score": attempt.risk_score or 0,
            "total_violations": attempt.total_violations or 0,
            "violation_summary": _violation_summary(violations),
        })
    return rows


def _compute_statistics(exam, attempts, candidate_rows):
    completed = [a for a in attempts if a.end_time is not None]
    percentages = [r["percentage"] for r in candidate_rows if r["status"] != "Incomplete"]
    pass_count = sum(1 for r in candidate_rows if r["status"] == "Pass")
    fail_count = sum(1 for r in candidate_rows if r["status"] == "Fail")
    decided = pass_count + fail_count

    all_violations = []
    for attempt in attempts:
        all_violations.extend(attempt.violations.all())

    violation_counter = Counter(v.violation_type for v in all_violations)

    best_per_user = {}
    for row in candidate_rows:
        if row["status"] == "Incomplete":
            continue
        email = row["email"]
        if email not in best_per_user or row["percentage"] > best_per_user[email]["percentage"]:
            best_per_user[email] = row

    top_scores = sorted(best_per_user.values(), key=lambda r: (-r["percentage"], -r["score"]))[:10]
    highest_risk = sorted(candidate_rows, key=lambda r: (-r["risk_score"], -r["total_violations"]))[:10]
    common_violations = violation_counter.most_common(10)

    scores = [r["score"] for r in candidate_rows if r["status"] != "Incomplete"]
    risk_scores = [r["risk_score"] for r in candidate_rows]

    return {
        "total_candidates": len({a.user_id for a in attempts}),
        "total_attempts": len(attempts),
        "completed_attempts": len(completed),
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "highest_score": max(scores) if scores else 0,
        "lowest_score": min(scores) if scores else 0,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": f"{round((pass_count / decided) * 100, 1)}%" if decided else "0%",
        "fail_rate": f"{round((fail_count / decided) * 100, 1)}%" if decided else "0%",
        "average_risk": round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else 0,
        "total_violations": sum(r["total_violations"] for r in candidate_rows),
        "top_scores": top_scores,
        "highest_risk": highest_risk,
        "common_violations": common_violations,
        "average_percentage": round(sum(percentages) / len(percentages), 1) if percentages else 0,
    }


def _write_candidate_sheet(ws, exam, org_name, rows):
    ws.title = "Candidate Assessment Report"

    ws.merge_cells("A1:N1")
    title_cell = ws["A1"]
    title_cell.value = "ParallaxLane — Candidate Assessment Report"
    title_cell.font = TITLE_FONT
    title_cell.alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("A2:N2")
    meta_cell = ws["A2"]
    meta_cell.value = (
        f"Exam: {exam.title}  |  Organisation: {org_name}  |  "
        f"Generated: {_format_datetime(timezone.now())}"
    )
    meta_cell.font = Font(name="Calibri", size=10, color="666666")
    meta_cell.alignment = Alignment(horizontal="left", vertical="center")

    headers = [
        "Candidate Name",
        "Email",
        "Organisation",
        "Exam Name",
        "Attempt Date",
        "Score Obtained",
        "Maximum Score",
        "Percentage",
        "Result Status",
        "Duration Taken",
        "Submission Time",
        "Risk Score",
        "Total Violations",
        "Violation Summary",
    ]

    header_row = 4
    for col, header in enumerate(headers, start=1):
        ws.cell(row=header_row, column=col, value=header)

    _style_header_row(ws, header_row, len(headers))

    data_start = header_row + 1
    for idx, row in enumerate(rows, start=data_start):
        values = [
            row["name"],
            row["email"],
            org_name,
            exam.title,
            row["attempt_date"],
            _format_score(row["score"]),
            _format_score(row["total"]),
            row["percentage_display"],
            row["status"],
            row["duration"],
            row["submission_time"],
            row["risk_score"],
            row["total_violations"],
            row["violation_summary"],
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=idx, column=col, value=value)
            cell.alignment = WRAP_ALIGNMENT if col == 14 else CELL_ALIGNMENT
            if col == 9 and value == "Pass":
                cell.font = Font(color="006100", bold=True)
            elif col == 9 and value == "Fail":
                cell.font = Font(color="9C0006", bold=True)

    if rows:
        _apply_table_borders(ws, data_start, data_start + len(rows) - 1, len(headers))
        ws.auto_filter.ref = f"A{header_row}:N{data_start + len(rows) - 1}"
    else:
        ws.cell(row=data_start, column=1, value="No attempts recorded for this exam.")
        ws.merge_cells(f"A{data_start}:N{data_start}")

    ws.freeze_panes = f"A{data_start}"
    _auto_column_widths(ws)
    ws.column_dimensions["N"].width = 45


def _write_statistics_sheet(ws, exam, org_name, stats):
    ws.title = "Exam Statistics"

    ws.merge_cells("A1:D1")
    ws["A1"].value = "ParallaxLane — Exam Statistics"
    ws["A1"].font = TITLE_FONT

    ws.merge_cells("A2:D2")
    ws["A2"].value = f"Exam: {exam.title}  |  Organisation: {org_name}"
    ws["A2"].font = Font(name="Calibri", size=10, color="666666")

    metrics = [
        ("Total Candidates", stats["total_candidates"]),
        ("Total Attempts", stats["total_attempts"]),
        ("Completed Attempts", stats["completed_attempts"]),
        ("Average Score", stats["average_score"]),
        ("Average Percentage", f"{stats['average_percentage']}%"),
        ("Highest Score", stats["highest_score"]),
        ("Lowest Score", stats["lowest_score"]),
        ("Pass Count", stats["pass_count"]),
        ("Fail Count", stats["fail_count"]),
        ("Pass Rate", stats["pass_rate"]),
        ("Fail Rate", stats["fail_rate"]),
        ("Average Risk Score", stats["average_risk"]),
        ("Total Violations Logged", stats["total_violations"]),
    ]

    row = 4
    ws.cell(row=row, column=1, value="Metric").font = SUBTITLE_FONT
    ws.cell(row=row, column=2, value="Value").font = SUBTITLE_FONT
    row += 1

    for label, value in metrics:
        ws.cell(row=row, column=1, value=label).font = METRIC_FONT
        ws.cell(row=row, column=2, value=value)
        row += 1

    row += 2

    def write_table(title, headers, data_rows, start_row):
        ws.cell(row=start_row, column=1, value=title).font = SUBTITLE_FONT
        header_row = start_row + 1
        for col, header in enumerate(headers, start=1):
            ws.cell(row=header_row, column=col, value=header)
        _style_header_row(ws, header_row, len(headers))

        data_row = header_row + 1
        for entry in data_rows:
            for col, value in enumerate(entry, start=1):
                ws.cell(row=data_row, column=col, value=value)
            data_row += 1

        if data_rows:
            _apply_table_borders(ws, header_row, data_row - 1, len(headers))
        return data_row + 1

    top_score_rows = [
        (
            entry["name"],
            entry["email"],
            f"{_format_score(entry['score'])}/{_format_score(entry['total'])}",
            entry["percentage_display"],
            entry["status"],
        )
        for entry in stats["top_scores"]
    ]
    row = write_table(
        "Top 10 Scores",
        ["Candidate Name", "Email", "Score", "Percentage", "Status"],
        top_score_rows,
        row,
    )

    risk_rows = [
        (
            entry["name"],
            entry["email"],
            entry["risk_score"],
            entry["total_violations"],
            entry["violation_summary"],
        )
        for entry in stats["highest_risk"]
        if entry["risk_score"] > 0 or entry["total_violations"] > 0
    ]
    row = write_table(
        "Highest Risk Candidates",
        ["Candidate Name", "Email", "Risk Score", "Total Violations", "Violation Summary"],
        risk_rows[:10],
        row,
    )

    violation_rows = [
        (_violation_label(vtype), count) for vtype, count in stats["common_violations"]
    ]
    write_table(
        "Most Common Violations",
        ["Violation Type", "Occurrences"],
        violation_rows,
        row,
    )

    _auto_column_widths(ws, min_width=14, max_width=50)
    ws.column_dimensions["E"].width = 45


def generate_assessment_report(exam):
    org_name = exam.organisation.name

    attempts = list(
        ExamAttempt.objects.filter(exam=exam)
        .select_related("user", "exam", "exam__organisation")
        .prefetch_related(
            Prefetch("violations", queryset=Violation.objects.order_by("timestamp"))
        )
        .order_by("user__name", "user__email", "-start_time")
    )

    candidate_rows = _build_candidate_rows(attempts)
    stats = _compute_statistics(exam, attempts, candidate_rows)

    wb = Workbook()
    candidate_ws = wb.active
    stats_ws = wb.create_sheet()

    _write_candidate_sheet(candidate_ws, exam, org_name, candidate_rows)
    _write_statistics_sheet(stats_ws, exam, org_name, stats)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
