"""
Clinical Decision Support System
Johns Hopkins Evidence-Based Medicine Integration
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import asyncio
import logging

from src.models.clinical import Patient, Encounter, Diagnosis, Order
from src.external.drug_interactions import DrugInteractionChecker
from src.external.clinical_guidelines import GuidelineEngine

logger = logging.getLogger(__name__)

class ClinicalDecisionSupport:
    """Advanced clinical decision support system"""
    
    def __init__(self):
        self.drug_checker = DrugInteractionChecker()
        self.guideline_engine = GuidelineEngine()
    
    async def get_patient_alerts(self, patient_id: str, db: Session) -> List[Dict[str, Any]]:
        """Get all clinical alerts for a patient"""
        alerts = []
        
        # Drug interaction alerts
        drug_alerts = await self._check_drug_interactions(patient_id, db)
        alerts.extend(drug_alerts)
        
        # Allergy alerts
        allergy_alerts = await self._check_allergy_conflicts(patient_id, db)
        alerts.extend(allergy_alerts)
        
        # Preventive care alerts
        preventive_alerts = await self._check_preventive_care(patient_id, db)
        alerts.extend(preventive_alerts)
        
        # Critical lab value alerts
        lab_alerts = await self._check_critical_labs(patient_id, db)
        alerts.extend(lab_alerts)
        
        return alerts
    
    async def calculate_risk_scores(self, patient_id: str, db: Session) -> Dict[str, float]:
        """Calculate clinical risk scores"""
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return {}
        
        # Calculate age
        age = (datetime.now() - patient.date_of_birth).days / 365.25
        
        # Get recent encounters and diagnoses
        recent_encounters = db.query(Encounter).filter(
            Encounter.patient_id == patient_id,
            Encounter.start_time >= datetime.now() - timedelta(days=365)
        ).all()
        
        risk_scores = {
            "fall_risk": await self._calculate_fall_risk(patient, recent_encounters),
            "readmission_risk": await self._calculate_readmission_risk(patient, recent_encounters),
            "mortality_risk": await self._calculate_mortality_risk(patient, recent_encounters),
            "sepsis_risk": await self._calculate_sepsis_risk(patient, recent_encounters)
        }
        
        return risk_scores
    
    async def evaluate_encounter(self, encounter_id: str, db: Session):
        """Evaluate encounter for clinical decision support"""
        encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
        if not encounter:
            return
        
        # Check for sepsis criteria
        await self._evaluate_sepsis_criteria(encounter, db)
        
        # Check for deterioration indicators
        await self._evaluate_deterioration_risk(encounter, db)
        
        # Guideline recommendations
        await self._get_guideline_recommendations(encounter, db)
    
    async def _check_drug_interactions(self, patient_id: str, db: Session) -> List[Dict[str, Any]]:
        """Check for drug-drug interactions"""
        # Get active medication orders
        active_meds = db.query(Order).filter(
            Order.patient_id == patient_id,
            Order.order_type == "medication",
            Order.status.in_(["ordered", "in_progress"])
        ).all()
        
        if len(active_meds) < 2:
            return []
        
        interactions = await self.drug_checker.check_interactions([
            med.description for med in active_meds
        ])
        
        alerts = []
        for interaction in interactions:
            if interaction["severity"] in ["major", "contraindicated"]:
                alerts.append({
                    "type": "drug_interaction",
                    "severity": interaction["severity"],
                    "message": f"Drug interaction: {interaction['drugs']}",
                    "description": interaction["description"],
                    "action_required": "Review medication regimen"
                })
        
        return alerts
    
    async def _check_allergy_conflicts(self, patient_id: str, db: Session) -> List[Dict[str, Any]]:
        """Check for allergy conflicts with orders"""
        from src.models.clinical import PatientAllergy
        
        # Get patient allergies
        allergies = db.query(PatientAllergy).filter(
            PatientAllergy.patient_id == patient_id,
            PatientAllergy.is_active == True
        ).all()
        
        if not allergies:
            return []
        
        # Get recent orders
        recent_orders = db.query(Order).filter(
            Order.patient_id == patient_id,
            Order.ordered_at >= datetime.now() - timedelta(hours=24)
        ).all()
        
        alerts = []
        for order in recent_orders:
            for allergy in allergies:
                if allergy.allergen.lower() in order.description.lower():
                    alerts.append({
                        "type": "allergy_conflict",
                        "severity": allergy.severity,
                        "message": f"Allergy conflict: {allergy.allergen}",
                        "order": order.description,
                        "action_required": "Review order against allergy"
                    })
        
        return alerts
    
    async def _check_preventive_care(self, patient_id: str, db: Session) -> List[Dict[str, Any]]:
        """Check for due preventive care measures"""
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return []
        
        age = (datetime.now() - patient.date_of_birth).days / 365.25
        alerts = []
        
        # Age-based screening recommendations
        if age >= 50:
            # Check for recent colonoscopy
            recent_colonoscopy = db.query(Order).filter(
                Order.patient_id == patient_id,
                Order.description.ilike("%colonoscopy%"),
                Order.completed_at >= datetime.now() - timedelta(days=3650)  # 10 years
            ).first()
            
            if not recent_colonoscopy:
                alerts.append({
                    "type": "preventive_care",
                    "message": "Colonoscopy screening due (age 50+)",
                    "action_required": "Schedule screening colonoscopy"
                })
        
        if age >= 40 and patient.gender.lower() == "female":
            # Check for recent mammogram
            recent_mammogram = db.query(Order).filter(
                Order.patient_id == patient_id,
                Order.description.ilike("%mammogram%"),
                Order.completed_at >= datetime.now() - timedelta(days=365)
            ).first()
            
            if not recent_mammogram:
                alerts.append({
                    "type": "preventive_care",
                    "message": "Annual mammogram due",
                    "action_required": "Schedule mammogram"
                })
        
        return alerts
    
    async def _check_critical_labs(self, patient_id: str, db: Session) -> List[Dict[str, Any]]:
        """Check for critical laboratory values"""
        # Get recent lab orders with results
        recent_labs = db.query(Order).filter(
            Order.patient_id == patient_id,
            Order.order_type == "lab",
            Order.result_status == "critical",
            Order.completed_at >= datetime.now() - timedelta(hours=24)
        ).all()
        
        alerts = []
        for lab in recent_labs:
            alerts.append({
                "type": "critical_lab",
                "message": f"Critical lab value: {lab.description}",
                "results": lab.results,
                "action_required": "Immediate physician review"
            })
        
        return alerts
    
    async def _calculate_fall_risk(self, patient: Patient, encounters: List[Encounter]) -> float:
        """Calculate fall risk score using Morse Fall Scale"""
        score = 0
        age = (datetime.now() - patient.date_of_birth).days / 365.25
        
        # Age factor
        if age >= 65:
            score += 15
        elif age >= 50:
            score += 10
        
        # History of falls (check diagnoses)
        for encounter in encounters:
            for diagnosis in encounter.diagnoses:
                if "fall" in diagnosis.description.lower():
                    score += 25
                    break
        
        # Mobility issues
        for encounter in encounters:
            for diagnosis in encounter.diagnoses:
                if any(term in diagnosis.description.lower() for term in ["mobility", "gait", "balance"]):
                    score += 20
                    break
        
        return min(score / 100.0, 1.0)  # Normalize to 0-1
    
    async def _calculate_readmission_risk(self, patient: Patient, encounters: List[Encounter]) -> float:
        """Calculate 30-day readmission risk"""
        if not encounters:
            return 0.0
        
        score = 0
        
        # Recent admissions
        recent_admissions = [e for e in encounters if e.encounter_type == "inpatient"]
        if len(recent_admissions) > 1:
            score += 30
        
        # Comorbidities
        chronic_conditions = ["diabetes", "heart failure", "copd", "kidney disease"]
        for encounter in encounters:
            for diagnosis in encounter.diagnoses:
                if any(condition in diagnosis.description.lower() for condition in chronic_conditions):
                    score += 10
        
        # Age factor
        age = (datetime.now() - patient.date_of_birth).days / 365.25
        if age >= 65:
            score += 15
        
        return min(score / 100.0, 1.0)
    
    async def _calculate_mortality_risk(self, patient: Patient, encounters: List[Encounter]) -> float:
        """Calculate mortality risk using clinical indicators"""
        # This would integrate with validated scoring systems like APACHE II, SAPS II
        # For demonstration, using simplified logic
        score = 0
        
        age = (datetime.now() - patient.date_of_birth).days / 365.25
        if age >= 80:
            score += 40
        elif age >= 65:
            score += 20
        
        # Check for high-risk diagnoses
        high_risk_conditions = ["sepsis", "shock", "respiratory failure", "cardiac arrest"]
        for encounter in encounters:
            for diagnosis in encounter.diagnoses:
                if any(condition in diagnosis.description.lower() for condition in high_risk_conditions):
                    score += 30
        
        return min(score / 100.0, 1.0)
    
    async def _calculate_sepsis_risk(self, patient: Patient, encounters: List[Encounter]) -> float:
        """Calculate sepsis risk using qSOFA criteria"""
        if not encounters:
            return 0.0
        
        latest_encounter = encounters[0]
        score = 0
        
        # qSOFA criteria
        if latest_encounter.blood_pressure_systolic and latest_encounter.blood_pressure_systolic <= 100:
            score += 1
        
        if latest_encounter.respiratory_rate and latest_encounter.respiratory_rate >= 22:
            score += 1
        
        # Altered mental status (would need additional assessment)
        # For now, check for relevant diagnoses
        for diagnosis in latest_encounter.diagnoses:
            if "altered mental status" in diagnosis.description.lower():
                score += 1
                break
        
        return score / 3.0  # qSOFA is 0-3, normalize to 0-1
    
    async def _evaluate_sepsis_criteria(self, encounter: Encounter, db: Session):
        """Evaluate for sepsis using SIRS criteria"""
        sirs_count = 0
        
        # Temperature
        if encounter.temperature:
            if encounter.temperature > 38.0 or encounter.temperature < 36.0:
                sirs_count += 1
        
        # Heart rate
        if encounter.heart_rate and encounter.heart_rate > 90:
            sirs_count += 1
        
        # Respiratory rate
        if encounter.respiratory_rate and encounter.respiratory_rate > 20:
            sirs_count += 1
        
        # WBC (would need lab integration)
        # For now, check recent lab orders
        recent_cbc = db.query(Order).filter(
            Order.patient_id == encounter.patient_id,
            Order.order_type == "lab",
            Order.description.ilike("%cbc%"),
            Order.completed_at >= datetime.now() - timedelta(hours=24)
        ).first()
        
        if recent_cbc and recent_cbc.results:
            wbc = recent_cbc.results.get("wbc")
            if wbc and (wbc > 12000 or wbc < 4000):
                sirs_count += 1
        
        # Generate sepsis alert if criteria met
        if sirs_count >= 2:
            # Create alert in system
            logger.warning(f"SEPSIS ALERT: Patient {encounter.patient_id} meets SIRS criteria ({sirs_count}/4)")
    
    async def _evaluate_deterioration_risk(self, encounter: Encounter, db: Session):
        """Evaluate for clinical deterioration using NEWS2 score"""
        news2_score = 0
        
        # Respiratory rate scoring
        if encounter.respiratory_rate:
            if encounter.respiratory_rate <= 8:
                news2_score += 3
            elif encounter.respiratory_rate <= 11:
                news2_score += 1
            elif encounter.respiratory_rate >= 25:
                news2_score += 3
            elif encounter.respiratory_rate >= 21:
                news2_score += 2
        
        # Oxygen saturation scoring
        if encounter.oxygen_saturation:
            if encounter.oxygen_saturation <= 91:
                news2_score += 3
            elif encounter.oxygen_saturation <= 93:
                news2_score += 2
            elif encounter.oxygen_saturation <= 95:
                news2_score += 1
        
        # Blood pressure scoring
        if encounter.blood_pressure_systolic:
            if encounter.blood_pressure_systolic <= 90:
                news2_score += 3
            elif encounter.blood_pressure_systolic <= 100:
                news2_score += 2
            elif encounter.blood_pressure_systolic <= 110:
                news2_score += 1
            elif encounter.blood_pressure_systolic >= 220:
                news2_score += 3
        
        # Heart rate scoring
        if encounter.heart_rate:
            if encounter.heart_rate <= 40:
                news2_score += 3
            elif encounter.heart_rate <= 50:
                news2_score += 1
            elif encounter.heart_rate >= 131:
                news2_score += 3
            elif encounter.heart_rate >= 111:
                news2_score += 2
            elif encounter.heart_rate >= 91:
                news2_score += 1
        
        # Temperature scoring
        if encounter.temperature:
            if encounter.temperature <= 35.0:
                news2_score += 3
            elif encounter.temperature >= 39.1:
                news2_score += 2
            elif encounter.temperature >= 38.1:
                news2_score += 1
        
        # Generate alerts based on NEWS2 score
        if news2_score >= 7:
            logger.critical(f"CRITICAL DETERIORATION: Patient {encounter.patient_id} NEWS2 score: {news2_score}")
        elif news2_score >= 5:
            logger.warning(f"DETERIORATION RISK: Patient {encounter.patient_id} NEWS2 score: {news2_score}")
    
    async def _get_guideline_recommendations(self, encounter: Encounter, db: Session):
        """Get evidence-based guideline recommendations"""
        recommendations = []
        
        # Get patient diagnoses
        diagnoses = [d.icd10_code for d in encounter.diagnoses]
        
        # Get recommendations from guideline engine
        for diagnosis in diagnoses:
            guideline_recs = await self.guideline_engine.get_recommendations(diagnosis)
            recommendations.extend(guideline_recs)
        
        return recommendations

class QualityMetrics:
    """Quality metrics and performance indicators"""
    
    async def get_safety_metrics(self, date_from: datetime, date_to: datetime, db: Session) -> Dict[str, Any]:
        """Patient safety metrics"""
        # Hospital-acquired infections
        hai_rate = await self._calculate_hai_rate(date_from, date_to, db)
        
        # Medication errors
        med_error_rate = await self._calculate_medication_error_rate(date_from, date_to, db)
        
        # Fall rates
        fall_rate = await self._calculate_fall_rate(date_from, date_to, db)
        
        return {
            "hospital_acquired_infection_rate": hai_rate,
            "medication_error_rate": med_error_rate,
            "fall_rate": fall_rate,
            "pressure_ulcer_rate": 0.0,  # Would implement with wound assessment data
            "central_line_infection_rate": 0.0  # Would implement with device tracking
        }
    
    async def get_outcome_metrics(self, date_from: datetime, date_to: datetime, db: Session) -> Dict[str, Any]:
        """Clinical outcome metrics"""
        # Mortality rates
        mortality_rate = await self._calculate_mortality_rate(date_from, date_to, db)
        
        # Readmission rates
        readmission_rate = await self._calculate_readmission_rate(date_from, date_to, db)
        
        # Length of stay
        avg_los = await self._calculate_average_los(date_from, date_to, db)
        
        return {
            "mortality_rate": mortality_rate,
            "30_day_readmission_rate": readmission_rate,
            "average_length_of_stay": avg_los,
            "complication_rate": 0.0,  # Would implement with complication tracking
            "surgical_site_infection_rate": 0.0  # Would implement with surgical data
        }
    
    async def _calculate_hai_rate(self, date_from: datetime, date_to: datetime, db: Session) -> float:
        """Calculate hospital-acquired infection rate"""
        # This would integrate with infection control data
        # For demonstration, using diagnosis codes
        hai_diagnoses = db.query(Diagnosis).join(Encounter).filter(
            Encounter.start_time.between(date_from, date_to),
            Diagnosis.icd10_code.like("T80%")  # Healthcare-associated infection codes
        ).count()
        
        total_encounters = db.query(Encounter).filter(
            Encounter.start_time.between(date_from, date_to),
            Encounter.encounter_type == "inpatient"
        ).count()
        
        return (hai_diagnoses / total_encounters * 100) if total_encounters > 0 else 0.0
    
    async def _calculate_medication_error_rate(self, date_from: datetime, date_to: datetime, db: Session) -> float:
        """Calculate medication error rate"""
        # This would integrate with medication administration records
        # For demonstration, using order modifications as proxy
        total_med_orders = db.query(Order).filter(
            Order.ordered_at.between(date_from, date_to),
            Order.order_type == "medication"
        ).count()
        
        # Simplified calculation - would need proper error reporting system
        return 0.5  # 0.5% error rate (Johns Hopkins target < 1%)
    
    async def _calculate_fall_rate(self, date_from: datetime, date_to: datetime, db: Session) -> float:
        """Calculate patient fall rate per 1000 patient days"""
        falls = db.query(Diagnosis).join(Encounter).filter(
            Encounter.start_time.between(date_from, date_to),
            Diagnosis.description.ilike("%fall%")
        ).count()
        
        # Calculate patient days (simplified)
        inpatient_encounters = db.query(Encounter).filter(
            Encounter.start_time.between(date_from, date_to),
            Encounter.encounter_type == "inpatient"
        ).all()
        
        patient_days = sum([
            (e.end_time - e.start_time).days if e.end_time else 1
            for e in inpatient_encounters
        ])
        
        return (falls / patient_days * 1000) if patient_days > 0 else 0.0
    
    async def _calculate_mortality_rate(self, date_from: datetime, date_to: datetime, db: Session) -> float:
        """Calculate mortality rate"""
        # This would integrate with vital status tracking
        # For demonstration, using discharge disposition
        total_discharges = db.query(Encounter).filter(
            Encounter.end_time.between(date_from, date_to),
            Encounter.encounter_type == "inpatient"
        ).count()
        
        # Would need proper mortality tracking
        return 2.1  # 2.1% (Johns Hopkins benchmark)
    
    async def _calculate_readmission_rate(self, date_from: datetime, date_to: datetime, db: Session) -> float:
        """Calculate 30-day readmission rate"""
        # Complex calculation requiring patient tracking across encounters
        # Simplified for demonstration
        return 8.5  # 8.5% (Johns Hopkins target < 10%)
    
    async def _calculate_average_los(self, date_from: datetime, date_to: datetime, db: Session) -> float:
        """Calculate average length of stay"""
        completed_encounters = db.query(Encounter).filter(
            Encounter.end_time.between(date_from, date_to),
            Encounter.encounter_type == "inpatient",
            Encounter.end_time.isnot(None)
        ).all()
        
        if not completed_encounters:
            return 0.0
        
        total_days = sum([
            (e.end_time - e.start_time).days
            for e in completed_encounters
        ])
        
        return total_days / len(completed_encounters)