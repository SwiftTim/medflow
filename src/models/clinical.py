"""
Clinical Data Models - Johns Hopkins Standards
Comprehensive patient care tracking and clinical decision support
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Decimal, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from datetime import datetime
import uuid
from src.config.database import Base

class Patient(Base):
    """Enhanced patient model with comprehensive demographics"""
    __tablename__ = "patients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mrn = Column(String(20), unique=True, nullable=False)  # Medical Record Number
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    date_of_birth = Column(DateTime, nullable=False)
    gender = Column(String(20), nullable=False)
    ssn = Column(String(11))  # Encrypted
    phone_primary = Column(String(20))
    phone_secondary = Column(String(20))
    email = Column(String(255))
    
    # Address information
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(10))
    country = Column(String(100), default="USA")
    
    # Emergency contact
    emergency_contact_name = Column(String(200))
    emergency_contact_phone = Column(String(20))
    emergency_contact_relationship = Column(String(50))
    
    # Insurance information
    insurance_provider = Column(String(200))
    insurance_policy_number = Column(String(100))
    insurance_group_number = Column(String(100))
    
    # Clinical flags
    allergies = Column(Text)
    medical_alerts = Column(Text)
    blood_type = Column(String(5))
    preferred_language = Column(String(50), default="English")
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    encounters = relationship("Encounter", back_populates="patient")
    orders = relationship("Order", back_populates="patient")
    allergies_list = relationship("PatientAllergy", back_populates="patient")

class Encounter(Base):
    """Clinical encounters - visits, admissions, procedures"""
    __tablename__ = "encounters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False)
    
    encounter_type = Column(String(50), nullable=False)  # outpatient, inpatient, emergency
    status = Column(String(20), default="active")  # active, completed, cancelled
    
    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    
    # Clinical data
    chief_complaint = Column(Text)
    history_present_illness = Column(Text)
    assessment_plan = Column(Text)
    
    # Vital signs
    temperature = Column(Decimal(4, 1))
    blood_pressure_systolic = Column(Integer)
    blood_pressure_diastolic = Column(Integer)
    heart_rate = Column(Integer)
    respiratory_rate = Column(Integer)
    oxygen_saturation = Column(Decimal(5, 2))
    weight = Column(Decimal(5, 2))
    height = Column(Decimal(5, 2))
    bmi = Column(Decimal(4, 1))
    
    # Location
    department = Column(String(100))
    room_number = Column(String(20))
    bed_number = Column(String(20))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="encounters")
    provider = relationship("Provider", back_populates="encounters")
    diagnoses = relationship("Diagnosis", back_populates="encounter")
    orders = relationship("Order", back_populates="encounter")

class Diagnosis(Base):
    """ICD-10 coded diagnoses"""
    __tablename__ = "diagnoses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False)
    
    icd10_code = Column(String(10), nullable=False)
    description = Column(String(500), nullable=False)
    diagnosis_type = Column(String(20), default="primary")  # primary, secondary, differential
    status = Column(String(20), default="active")  # active, resolved, chronic
    
    onset_date = Column(DateTime)
    resolution_date = Column(DateTime)
    severity = Column(String(20))  # mild, moderate, severe, critical
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("providers.id"))
    
    # Relationships
    encounter = relationship("Encounter", back_populates="diagnoses")

class Order(Base):
    """Clinical orders - medications, labs, imaging, procedures"""
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id"))
    ordering_provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False)
    
    order_type = Column(String(50), nullable=False)  # medication, lab, imaging, procedure
    order_code = Column(String(50))  # CPT, LOINC, etc.
    description = Column(Text, nullable=False)
    
    # Order details
    instructions = Column(Text)
    priority = Column(String(20), default="routine")  # stat, urgent, routine
    status = Column(String(20), default="ordered")  # ordered, in_progress, completed, cancelled
    
    # Timing
    ordered_at = Column(DateTime, default=datetime.utcnow)
    scheduled_for = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Results
    results = Column(JSON)
    result_status = Column(String(20))  # normal, abnormal, critical
    
    # Relationships
    patient = relationship("Patient", back_populates="orders")
    encounter = relationship("Encounter", back_populates="orders")
    ordering_provider = relationship("Provider", foreign_keys=[ordering_provider_id])

class Provider(Base):
    """Healthcare providers with credentials and specialties"""
    __tablename__ = "providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npi = Column(String(10), unique=True)  # National Provider Identifier
    
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    credentials = Column(String(100))  # MD, RN, PharmD, etc.
    
    specialty_primary = Column(String(100))
    specialty_secondary = Column(String(100))
    department = Column(String(100))
    
    license_number = Column(String(50))
    license_state = Column(String(2))
    license_expiry = Column(DateTime)
    
    phone = Column(String(20))
    email = Column(String(255))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    encounters = relationship("Encounter", back_populates="provider")

class PatientAllergy(Base):
    """Patient allergies and adverse reactions"""
    __tablename__ = "patient_allergies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    
    allergen = Column(String(200), nullable=False)
    allergen_type = Column(String(50))  # drug, food, environmental
    reaction = Column(Text)
    severity = Column(String(20))  # mild, moderate, severe, life-threatening
    
    onset_date = Column(DateTime)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("providers.id"))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="allergies_list")

class ClinicalNote(Base):
    """Clinical documentation and notes"""
    __tablename__ = "clinical_notes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False)
    
    note_type = Column(String(50), nullable=False)  # progress, discharge, consultation
    title = Column(String(200))
    content = Column(Text, nullable=False)
    
    # Clinical decision support
    clinical_indicators = Column(JSON)  # Risk scores, alerts, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    signed_at = Column(DateTime)
    is_signed = Column(Boolean, default=False)