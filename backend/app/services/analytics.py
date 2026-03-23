from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

from app.models.complaint import Complaint

OPEN = "Open"
IN_PROGRESS = "In Progress"
ESCALATED = "Escalated"
RESOLVED = "Resolved"


def build_analytics(complaints: list[Complaint]) -> dict:
    if not complaints:
        return {
            "status_breakdown": [
                {"name": OPEN, "value": 0},
                {"name": IN_PROGRESS, "value": 0},
                {"name": ESCALATED, "value": 0},
                {"name": RESOLVED, "value": 0},
            ],
            "department_volume": [],
            "ward_unresolved": [],
            "department_performance": [],
            "satisfaction_score": 85,
            "anomalies": [],
            "live_feed": []
        }

    now = datetime.now(timezone.utc)
    
    status_counter = Counter()
    dept_counter = Counter()
    
    # 1. Ward Unresolved (Heatmap logic)
    ward_stats = defaultdict(lambda: {"ward": "", "open": 0, "escalated": 0, "total_unresolved": 0})
    
    # 2. Dept Performance (Avg time vs SLA)
    dept_resolution_times = defaultdict(list)
    
    # 3. Anomalies
    one_hour_ago = now - timedelta(hours=1)
    recent_dept_counts = Counter()
    
    # 4. Satisfaction Score
    total_resolved = 0
    resolved_in_sla = 0

    # 5. Live Feed
    live_feed = []

    for c in complaints:
        status_counter[c.status] += 1
        dept_counter[c.department] += 1
        
        # Ward Heatmap
        if c.status in [OPEN, IN_PROGRESS, ESCALATED]:
            ward_stats[c.ward]["ward"] = c.ward
            if c.status == ESCALATED:
                ward_stats[c.ward]["escalated"] += 1
            else:
                ward_stats[c.ward]["open"] += 1
            ward_stats[c.ward]["total_unresolved"] += 1
            
        # Department Performance
        if c.status == RESOLVED and c.resolved_at:
            resolve_time_hrs = (c.resolved_at - c.created_at).total_seconds() / 3600.0
            dept_resolution_times[c.department].append(resolve_time_hrs)
            total_resolved += 1
            
            # SLA logic
            sla = (c.sla_deadline - c.created_at).total_seconds() / 3600.0 if c.sla_deadline else 48.0
            if resolve_time_hrs <= sla:
                resolved_in_sla += 1
                
        # Anomaly Detection (recent spike logic)
        if c.created_at >= one_hour_ago:
            recent_dept_counts[(c.ward, c.department)] += 1
            
        # Live Feed
        if c.status == RESOLVED and c.resolved_at:
            live_feed.append(c)

    # Compile structures
    status_breakdown = [
        {"name": OPEN, "value": status_counter.get(OPEN, 0)},
        {"name": IN_PROGRESS, "value": status_counter.get(IN_PROGRESS, 0)},
        {"name": ESCALATED, "value": status_counter.get(ESCALATED, 0)},
        {"name": RESOLVED, "value": status_counter.get(RESOLVED, 0)},
    ]

    department_volume = [
        {"name": department, "complaints": count}
        for department, count in sorted(dept_counter.items(), key=lambda item: item[1], reverse=True)
    ]

    ward_unresolved = sorted(ward_stats.values(), key=lambda x: x["total_unresolved"], reverse=True)
    
    # Ensure all departments appear in performance index even if 0 resolved
    department_performance = []
    for dept, count in dept_counter.items():
        times = dept_resolution_times.get(dept, [])
        avg_time = sum(times) / max(len(times), 1)
        department_performance.append({
            "name": dept,
            "avg_time_hours": round(avg_time, 1) if times else 0,
            "sla_hours": 48.0 # Standard threshold representation
        })
        
    # Minimum baseline CSAT calculation
    satisfaction_score = int((resolved_in_sla / total_resolved * 100) if total_resolved > 0 else 85)
    
    anomalies = []
    for (ward, dept), count in recent_dept_counts.items():
        if count >= 3: # Demonstrable threshold for anomaly flag
            anomalies.append({
                "ward": ward,
                "department": dept,
                "message": f"Critical Anomaly: {count} {dept} complaints in {ward} within the last hour. Potential localized failure."
            })

    live_feed.sort(key=lambda x: x.resolved_at, reverse=True)
    live_feed_data = [
        {
            "ticket_id": c.ticket_id,
            "department": c.department,
            "ward": c.ward,
            "resolved_at": c.resolved_at.isoformat()
        }
        for c in live_feed[:10]
    ]

    return {
        "status_breakdown": status_breakdown,
        "department_volume": department_volume,
        "ward_unresolved": ward_unresolved,
        "department_performance": department_performance,
        "satisfaction_score": satisfaction_score,
        "anomalies": anomalies,
        "live_feed": live_feed_data
    }


def get_mayor_metrics(city_code: str) -> dict:
    from app.repositories.global_index import global_index
    
    raw_data = global_index.aggregate_by_tier(city_code)
    
    status_counts = {}
    category_counts = {}
    
    for row in raw_data:
        st = row.get("status", "")
        cat = row.get("category", "")
        c = row.get("count", 0)
        
        if st:
            status_counts[st] = status_counts.get(st, 0) + c
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + c
            
    # Format for PieChart and BarChart
    # Sorting to ensure consistent layout
    status_breakdown = [
        {"name": st, "value": count}
        for st, count in sorted(status_counts.items(), key=lambda x: x[0])
    ]
    
    category_breakdown = [
        {"name": cat, "value": count}
        for cat, count in sorted(category_counts.items(), key=lambda x: x[0])
    ]
    
    return {
        "status_breakdown": status_breakdown,
        "category_breakdown": category_breakdown
    }
