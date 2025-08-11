"""
Quality Management Models
Johns Hopkins Quality and Safety Framework
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Decimal, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from src.config.database import Base

class SafetyEvent(Base):
    """Patient safety events and incidents"""
    __tablename__ = "safety_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_number = Column(String(20), unique=True, nullable=False)
    
    # Event classification
    event_type = Column(String(100), nullable=False)  # medication_error, fall, infection, etc.
    category = Column(String(50))  # patient_safety, quality, compliance
    severity = Column(String(20), nullable=False)  # minor, moderate, major, critical
    
    # Event details
    description = Column(Text, nullable=False)
    location = Column(String(100))
    occurred_at = Column(DateTime, nullable=False)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    
    # People involved
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"))
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    involved_staff = Column(JSON)  # List of staff IDs involved
    
    # Analysis and response
    root_cause_analysis = Column(Text)
    contributing_factors = Column(JSON)
    corrective_actions = Column(JSON)
    preventive_measures = Column(JSON)
    
    # Status tracking
    status = Column(String(20), default="reported")  # reported, investigating, resolved, closed
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient")
    reporter = relationship("User", foreign_keys=[reporter_id])
    assignee = relationship("User", foreign_keys=[assigned_to])

class QualityInitiative(Base):
    """Quality improvement initiatives and PDSA cycles"""
    __tablename__ = "quality_initiatives"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Initiative classification
    focus_area = Column(String(100))  # patient_safety, clinical_outcomes, efficiency
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    
    # PDSA cycle tracking
    current_phase = Column(String(20), default="plan")  # plan, do, study, act
    hypothesis = Column(Text)
    measures = Column(JSON)  # Outcome, process, and balancing measures
    
    # Timeline
    start_date = Column(DateTime, nullable=False)
    target_completion = Column(DateTime)
    actual_completion = Column(DateTime)
    
    # Team
    lead_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    team_members = Column(JSON)  # List of team member IDs
    sponsor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Results
    baseline_data = Column(JSON)
    current_data = Column(JSON)
    target_goals = Column(JSON)
    lessons_learned = Column(Text)
    
    # Status
    status = Column(String(20), default="active")  # active, on_hold, completed, cancelled
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    lead = relationship("User", foreign_keys=[lead_id])
    sponsor = relationship("User", foreign_keys=[sponsor_id])
    creator = relationship("User", foreign_keys=[created_by])

class QualityMeasure(Base):
    """Quality measures and indicators"""
    __tablename__ = "quality_measures"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Measure classification
    measure_type = Column(String(50))  # outcome, process, structure, balancing
    category = Column(String(100))  # safety, effectiveness, efficiency, etc.
    
    # Calculation details
    numerator_definition = Column(Text)
    denominator_definition = Column(Text)
    calculation_method = Column(Text)
    
    # Targets and benchmarks
    target_value = Column(Decimal(10, 4))
    benchmark_value = Column(Decimal(10, 4))
    benchmark_source = Column(String(200))
    
    # Reporting
    reporting_frequency = Column(String(20))  # daily, weekly, monthly, quarterly
    responsible_department = Column(String(100))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class QualityMeasureResult(Base):
    """Quality measure results over time"""
    __tablename__ = "quality_measure_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    measure_id = Column(UUID(as_uuid=True), ForeignKey("quality_measures.id"), nullable=False)
    
    # Time period
    reporting_period_start = Column(DateTime, nullable=False)
    reporting_period_end = Column(DateTime, nullable=False)
    
    # Results
    numerator = Column(Integer)
    denominator = Column(Integer)
    rate = Column(Decimal(10, 4))
    
    # Context
    department = Column(String(100))
    unit = Column(String(100))
    population_size = Column(Integer)
    
    # Analysis
    variance_from_target = Column(Decimal(10, 4))
    variance_from_benchmark = Column(Decimal(10, 4))
    trend_direction = Column(String(20))  # improving, declining, stable
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    calculated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    measure = relationship("QualityMeasure")

class InfectionControlEvent(Base):
    """Healthcare-associated infection tracking"""
    __tablename__ = "infection_control_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id"))
    
    # Infection details
    infection_type = Column(String(100), nullable=False)  # CLABSI, CAUTI, SSI, VAP, etc.
    organism = Column(String(200))
    resistance_pattern = Column(String(200))
    
    # Device association
    device_type = Column(String(100))  # central_line, urinary_catheter, ventilator
    device_days = Column(Integer)
    
    # Timeline
    onset_date = Column(DateTime, nullable=False)
    detection_date = Column(DateTime, default=datetime.utcnow)
    resolution_date = Column(DateTime)
    
    # Classification
    healthcare_associated = Column(Boolean, default=True)
    preventable = Column(Boolean)
    
    # Response
    isolation_required = Column(Boolean, default=False)
    isolation_type = Column(String(50))
    contact_tracing_completed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    patient = relationship("Patient")
    encounter = relationship("Encounter")

class MedicationError(Base):
    """Medication errors and near misses"""
    __tablename__ = "medication_errors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"))
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    
    # Error classification
    error_type = Column(String(100), nullable=False)  # wrong_drug, wrong_dose, wrong_patient, etc.
    error_stage = Column(String(50))  # prescribing, transcribing, dispensing, administering
    severity = Column(String(20))  # no_harm, minor, moderate, major, catastrophic
    
    # Error details
    description = Column(Text, nullable=False)
    medication_involved = Column(String(200))
    intended_action = Column(Text)
    actual_action = Column(Text)
    
    # Contributing factors
    contributing_factors = Column(JSON)
    system_factors = Column(JSON)
    human_factors = Column(JSON)
    
    # Outcome
    patient_outcome = Column(String(100))
    harm_occurred = Column(Boolean, default=False)
    intervention_required = Column(Boolean, default=False)
    
    # Reporting
    discovered_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    discovered_at = Column(DateTime, default=datetime.utcnow)
    reported_to_pharmacy = Column(Boolean, default=False)
    reported_to_physician = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient")
    order = relationship("Order")
    discoverer = relationship("User")

class ClinicalAlert(Base):
    """Clinical decision support alerts"""
    __tablename__ = "clinical_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id"))
    
    # Alert details
    alert_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)  # info, warning, critical
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Clinical context
    triggering_data = Column(JSON)
    clinical_context = Column(JSON)
    recommended_actions = Column(JSON)
    
    # Response tracking
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    acknowledged_at = Column(DateTime)
    action_taken = Column(Text)
    override_reason = Column(Text)
    
    # Alert lifecycle
    status = Column(String(20), default="active")  # active, acknowledged, resolved, overridden
    expires_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient")
    encounter = relationship("Encounter")
    acknowledger = relationship("User")