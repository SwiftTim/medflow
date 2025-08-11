"""
Clinical API Endpoints - Johns Hopkins Standards
Advanced clinical workflows and decision support
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from src.config.database import get_db
from src.models.clinical import Patient, Encounter, Diagnosis, Order, Provider
from src.schemas.clinical import (
    PatientCreate, PatientResponse, EncounterCreate, EncounterResponse,
    DiagnosisCreate, OrderCreate, VitalSigns, ClinicalAlert
)
from src.services.clinical_decision_support import ClinicalDecisionSupport
from src.services.quality_metrics import QualityMetrics
from src.auth.security import get_current_user

router = APIRouter(prefix="/api/clinical", tags=["clinical"])
logger = logging.getLogger(__name__)

@router.post("/patients", response_model=PatientResponse)
async def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create new patient with comprehensive validation"""
    try:
        # Generate MRN
        mrn = await generate_mrn(db)
        
        patient = Patient(
            mrn=mrn,
            **patient_data.dict()
        )
        
        db.add(patient)
        db.commit()
        db.refresh(patient)
        
        # Log patient creation for audit
        logger.info(f"Patient created: MRN {mrn} by user {current_user.id}")
        
        return patient
        
    except Exception as e:
        logger.error(f"Error creating patient: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create patient")

@router.get("/patients/{patient_id}/clinical-summary")
async def get_clinical_summary(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get comprehensive clinical summary for patient"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get recent encounters
    recent_encounters = db.query(Encounter).filter(
        Encounter.patient_id == patient_id
    ).order_by(Encounter.start_time.desc()).limit(10).all()
    
    # Get active diagnoses
    active_diagnoses = db.query(Diagnosis).join(Encounter).filter(
        Encounter.patient_id == patient_id,
        Diagnosis.status == "active"
    ).all()
    
    # Get recent orders
    recent_orders = db.query(Order).filter(
        Order.patient_id == patient_id
    ).order_by(Order.ordered_at.desc()).limit(20).all()
    
    # Clinical decision support alerts
    cds = ClinicalDecisionSupport()
    alerts = await cds.get_patient_alerts(patient_id, db)
    
    return {
        "patient": patient,
        "recent_encounters": recent_encounters,
        "active_diagnoses": active_diagnoses,
        "recent_orders": recent_orders,
        "clinical_alerts": alerts,
        "risk_scores": await cds.calculate_risk_scores(patient_id, db)
    }

@router.post("/encounters", response_model=EncounterResponse)
async def create_encounter(
    encounter_data: EncounterCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create new clinical encounter"""
    encounter = Encounter(
        provider_id=current_user.id,
        **encounter_data.dict()
    )
    
    db.add(encounter)
    db.commit()
    db.refresh(encounter)
    
    # Trigger clinical decision support
    cds = ClinicalDecisionSupport()
    await cds.evaluate_encounter(encounter.id, db)
    
    return encounter

@router.post("/encounters/{encounter_id}/vital-signs")
async def record_vital_signs(
    encounter_id: str,
    vitals: VitalSigns,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Record vital signs with automated alerts"""
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Update encounter with vital signs
    for field, value in vitals.dict(exclude_unset=True).items():
        setattr(encounter, field, value)
    
    # Calculate BMI if height and weight provided
    if encounter.height and encounter.weight:
        height_m = float(encounter.height) / 100  # Convert cm to meters
        encounter.bmi = float(encounter.weight) / (height_m ** 2)
    
    db.commit()
    
    # Check for critical values
    alerts = await check_vital_signs_alerts(vitals, encounter.patient_id, db)
    
    return {
        "status": "success",
        "alerts": alerts,
        "bmi": encounter.bmi
    }

@router.get("/quality-metrics/dashboard")
async def get_quality_dashboard(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Quality metrics dashboard - Johns Hopkins standards"""
    if not date_from:
        date_from = datetime.now() - timedelta(days=30)
    if not date_to:
        date_to = datetime.now()
    
    quality_service = QualityMetrics()
    
    metrics = {
        "patient_safety": await quality_service.get_safety_metrics(date_from, date_to, db),
        "clinical_outcomes": await quality_service.get_outcome_metrics(date_from, date_to, db),
        "efficiency": await quality_service.get_efficiency_metrics(date_from, date_to, db),
        "satisfaction": await quality_service.get_satisfaction_metrics(date_from, date_to, db),
        "compliance": await quality_service.get_compliance_metrics(date_from, date_to, db)
    }
    
    return metrics

async def generate_mrn(db: Session) -> str:
    """Generate unique Medical Record Number"""
    import random
    while True:
        mrn = f"MRN{random.randint(100000, 999999)}"
        existing = db.query(Patient).filter(Patient.mrn == mrn).first()
        if not existing:
            return mrn

async def check_vital_signs_alerts(vitals: VitalSigns, patient_id: str, db: Session) -> List[dict]:
    """Check vital signs for critical values"""
    alerts = []
    
    # Critical value thresholds (Johns Hopkins protocols)
    if vitals.blood_pressure_systolic and vitals.blood_pressure_systolic > 180:
        alerts.append({
            "type": "critical",
            "message": "Hypertensive crisis - Systolic BP > 180",
            "action_required": "Immediate physician notification"
        })
    
    if vitals.heart_rate and vitals.heart_rate > 120:
        alerts.append({
            "type": "warning",
            "message": "Tachycardia - HR > 120",
            "action_required": "Monitor closely"
        })
    
    if vitals.oxygen_saturation and vitals.oxygen_saturation < 90:
        alerts.append({
            "type": "critical",
            "message": "Hypoxemia - O2 Sat < 90%",
            "action_required": "Immediate intervention required"
        })
    
    if vitals.temperature and vitals.temperature > 38.5:
        alerts.append({
            "type": "warning",
            "message": "Fever - Temperature > 38.5°C",
            "action_required": "Fever protocol"
        })
    
    return alerts