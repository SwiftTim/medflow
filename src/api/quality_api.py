"""
Quality Management API
Johns Hopkins Quality and Safety Standards
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from src.config.database import get_db
from src.services.quality_metrics import QualityMetrics
from src.services.clinical_decision_support import ClinicalDecisionSupport
from src.auth.security import get_current_user, require_permission

router = APIRouter(prefix="/api/quality", tags=["quality"])
logger = logging.getLogger(__name__)

@router.get("/dashboard")
@require_permission("quality:read")
async def get_quality_dashboard(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Comprehensive quality metrics dashboard"""
    if not date_from:
        date_from = datetime.now() - timedelta(days=30)
    if not date_to:
        date_to = datetime.now()
    
    quality_service = QualityMetrics()
    
    dashboard_data = {
        "overview": {
            "reporting_period": {
                "start": date_from.isoformat(),
                "end": date_to.isoformat()
            },
            "department": department or "All Departments"
        },
        "patient_safety": await quality_service.get_safety_metrics(date_from, date_to, db, department),
        "clinical_outcomes": await quality_service.get_outcome_metrics(date_from, date_to, db, department),
        "efficiency": await quality_service.get_efficiency_metrics(date_from, date_to, db, department),
        "satisfaction": await quality_service.get_satisfaction_metrics(date_from, date_to, db, department),
        "compliance": await quality_service.get_compliance_metrics(date_from, date_to, db, department),
        "benchmarks": await quality_service.get_benchmark_comparisons(date_from, date_to, db)
    }
    
    return dashboard_data

@router.get("/safety-events")
@require_permission("quality:read")
async def get_safety_events(
    severity: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get patient safety events and incidents"""
    from src.models.quality import SafetyEvent
    
    query = db.query(SafetyEvent)
    
    if severity:
        query = query.filter(SafetyEvent.severity == severity)
    if event_type:
        query = query.filter(SafetyEvent.event_type == event_type)
    if date_from:
        query = query.filter(SafetyEvent.occurred_at >= date_from)
    if date_to:
        query = query.filter(SafetyEvent.occurred_at <= date_to)
    
    events = query.order_by(SafetyEvent.occurred_at.desc()).all()
    
    return {
        "events": events,
        "summary": {
            "total_events": len(events),
            "by_severity": await _group_by_severity(events),
            "by_type": await _group_by_type(events)
        }
    }

@router.post("/safety-events")
@require_permission("quality:write")
async def report_safety_event(
    event_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Report patient safety event"""
    from src.models.quality import SafetyEvent
    
    safety_event = SafetyEvent(
        reporter_id=current_user.id,
        **event_data
    )
    
    db.add(safety_event)
    db.commit()
    db.refresh(safety_event)
    
    # Trigger immediate response for high-severity events
    if safety_event.severity in ["critical", "major"]:
        await _trigger_safety_response(safety_event, db)
    
    logger.info(f"Safety event reported: {safety_event.id} by user {current_user.id}")
    
    return {"status": "success", "event_id": safety_event.id}

@router.get("/clinical-indicators")
@require_permission("quality:read")
async def get_clinical_indicators(
    indicator_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get clinical quality indicators"""
    quality_service = QualityMetrics()
    
    indicators = {
        "core_measures": await quality_service.get_core_measures(db),
        "patient_safety_indicators": await quality_service.get_psi_metrics(db),
        "healthcare_acquired_conditions": await quality_service.get_hac_metrics(db),
        "readmission_rates": await quality_service.get_readmission_rates(db),
        "mortality_rates": await quality_service.get_mortality_rates(db)
    }
    
    if indicator_type:
        return indicators.get(indicator_type, {})
    
    return indicators

@router.get("/infection-control")
@require_permission("infection_control:read")
async def get_infection_control_metrics(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Infection control and prevention metrics"""
    if not date_from:
        date_from = datetime.now() - timedelta(days=30)
    if not date_to:
        date_to = datetime.now()
    
    quality_service = QualityMetrics()
    
    infection_metrics = {
        "healthcare_acquired_infections": {
            "clabsi_rate": await quality_service.calculate_clabsi_rate(date_from, date_to, db),
            "cauti_rate": await quality_service.calculate_cauti_rate(date_from, date_to, db),
            "ssi_rate": await quality_service.calculate_ssi_rate(date_from, date_to, db),
            "vap_rate": await quality_service.calculate_vap_rate(date_from, date_to, db),
            "cdiff_rate": await quality_service.calculate_cdiff_rate(date_from, date_to, db)
        },
        "antimicrobial_stewardship": {
            "antibiotic_usage": await quality_service.get_antibiotic_usage(date_from, date_to, db),
            "resistance_patterns": await quality_service.get_resistance_patterns(date_from, date_to, db),
            "stewardship_interventions": await quality_service.get_stewardship_metrics(date_from, date_to, db)
        },
        "hand_hygiene": {
            "compliance_rate": await quality_service.get_hand_hygiene_compliance(date_from, date_to, db),
            "observations": await quality_service.get_hand_hygiene_observations(date_from, date_to, db)
        }
    }
    
    return infection_metrics

@router.get("/performance-improvement")
@require_permission("quality:read")
async def get_performance_improvement_data(
    focus_area: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Performance improvement and PDSA cycle data"""
    quality_service = QualityMetrics()
    
    improvement_data = {
        "active_initiatives": await quality_service.get_active_initiatives(db),
        "completed_projects": await quality_service.get_completed_projects(db),
        "outcome_trends": await quality_service.get_outcome_trends(db),
        "benchmark_comparisons": await quality_service.get_external_benchmarks(db)
    }
    
    if focus_area:
        improvement_data = {
            k: v for k, v in improvement_data.items() 
            if focus_area.lower() in str(v).lower()
        }
    
    return improvement_data

@router.post("/quality-improvement/initiative")
@require_permission("quality:write")
async def create_quality_initiative(
    initiative_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create new quality improvement initiative"""
    from src.models.quality import QualityInitiative
    
    initiative = QualityInitiative(
        created_by=current_user.id,
        **initiative_data
    )
    
    db.add(initiative)
    db.commit()
    db.refresh(initiative)
    
    logger.info(f"Quality initiative created: {initiative.id} by user {current_user.id}")
    
    return {"status": "success", "initiative_id": initiative.id}

async def _group_by_severity(events: List) -> Dict[str, int]:
    """Group safety events by severity"""
    severity_counts = {}
    for event in events:
        severity = event.severity
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return severity_counts

async def _group_by_type(events: List) -> Dict[str, int]:
    """Group safety events by type"""
    type_counts = {}
    for event in events:
        event_type = event.event_type
        type_counts[event_type] = type_counts.get(event_type, 0) + 1
    return type_counts

async def _trigger_safety_response(safety_event, db: Session):
    """Trigger immediate response for critical safety events"""
    # Implementation would include:
    # - Immediate notifications to safety team
    # - Automatic escalation procedures
    # - Integration with rapid response systems
    logger.critical(f"CRITICAL SAFETY EVENT: {safety_event.id} - {safety_event.description}")