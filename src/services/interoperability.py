"""
Healthcare Interoperability Services
HL7 FHIR R4 Implementation for Johns Hopkins Standards
"""
from typing import Dict, List, Any, Optional
import json
import asyncio
import aiohttp
from datetime import datetime
import logging

from src.models.clinical import Patient, Encounter, Diagnosis, Order
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class FHIRService:
    """HL7 FHIR R4 implementation for interoperability"""
    
    def __init__(self):
        self.base_url = settings.fhir_server_url
        self.headers = {
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json"
        }
    
    async def create_patient_resource(self, patient: Patient) -> Dict[str, Any]:
        """Convert patient to FHIR Patient resource"""
        fhir_patient = {
            "resourceType": "Patient",
            "id": str(patient.id),
            "identifier": [
                {
                    "use": "usual",
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                                "code": "MR",
                                "display": "Medical Record Number"
                            }
                        ]
                    },
                    "value": patient.mrn
                }
            ],
            "name": [
                {
                    "use": "official",
                    "family": patient.last_name,
                    "given": [patient.first_name]
                }
            ],
            "gender": patient.gender.lower(),
            "birthDate": patient.date_of_birth.strftime("%Y-%m-%d"),
            "telecom": [],
            "address": []
        }
        
        # Add phone numbers
        if patient.phone_primary:
            fhir_patient["telecom"].append({
                "system": "phone",
                "value": patient.phone_primary,
                "use": "home"
            })
        
        if patient.email:
            fhir_patient["telecom"].append({
                "system": "email",
                "value": patient.email
            })
        
        # Add address
        if patient.address_line1:
            fhir_patient["address"].append({
                "use": "home",
                "line": [patient.address_line1, patient.address_line2] if patient.address_line2 else [patient.address_line1],
                "city": patient.city,
                "state": patient.state,
                "postalCode": patient.zip_code,
                "country": patient.country
            })
        
        return fhir_patient
    
    async def create_encounter_resource(self, encounter: Encounter) -> Dict[str, Any]:
        """Convert encounter to FHIR Encounter resource"""
        fhir_encounter = {
            "resourceType": "Encounter",
            "id": str(encounter.id),
            "status": encounter.status,
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": self._map_encounter_class(encounter.encounter_type),
                "display": encounter.encounter_type.title()
            },
            "subject": {
                "reference": f"Patient/{encounter.patient_id}"
            },
            "participant": [
                {
                    "individual": {
                        "reference": f"Practitioner/{encounter.provider_id}"
                    }
                }
            ],
            "period": {
                "start": encounter.start_time.isoformat()
            }
        }
        
        if encounter.end_time:
            fhir_encounter["period"]["end"] = encounter.end_time.isoformat()
        
        # Add location if available
        if encounter.department:
            fhir_encounter["location"] = [
                {
                    "location": {
                        "display": encounter.department
                    }
                }
            ]
        
        return fhir_encounter
    
    async def create_observation_resource(self, encounter: Encounter, vital_type: str, value: float) -> Dict[str, Any]:
        """Create FHIR Observation for vital signs"""
        vital_codes = {
            "temperature": {"code": "8310-5", "display": "Body temperature"},
            "heart_rate": {"code": "8867-4", "display": "Heart rate"},
            "blood_pressure_systolic": {"code": "8480-6", "display": "Systolic blood pressure"},
            "blood_pressure_diastolic": {"code": "8462-4", "display": "Diastolic blood pressure"},
            "respiratory_rate": {"code": "9279-1", "display": "Respiratory rate"},
            "oxygen_saturation": {"code": "2708-6", "display": "Oxygen saturation"}
        }
        
        if vital_type not in vital_codes:
            raise ValueError(f"Unknown vital sign type: {vital_type}")
        
        code_info = vital_codes[vital_type]
        
        observation = {
            "resourceType": "Observation",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": code_info["code"],
                        "display": code_info["display"]
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{encounter.patient_id}"
            },
            "encounter": {
                "reference": f"Encounter/{encounter.id}"
            },
            "effectiveDateTime": encounter.start_time.isoformat(),
            "valueQuantity": {
                "value": value,
                "unit": self._get_vital_unit(vital_type)
            }
        }
        
        return observation
    
    async def send_to_fhir_server(self, resource: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send FHIR resource to external server"""
        if not self.base_url:
            logger.warning("FHIR server URL not configured")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{resource['resourceType']}"
                async with session.post(url, json=resource, headers=self.headers) as response:
                    if response.status == 201:
                        return await response.json()
                    else:
                        logger.error(f"FHIR server error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error sending to FHIR server: {str(e)}")
            return None
    
    def _map_encounter_class(self, encounter_type: str) -> str:
        """Map internal encounter type to FHIR class codes"""
        mapping = {
            "outpatient": "AMB",
            "inpatient": "IMP",
            "emergency": "EMER",
            "virtual": "VR"
        }
        return mapping.get(encounter_type, "AMB")
    
    def _get_vital_unit(self, vital_type: str) -> str:
        """Get unit for vital sign"""
        units = {
            "temperature": "Cel",
            "heart_rate": "/min",
            "blood_pressure_systolic": "mm[Hg]",
            "blood_pressure_diastolic": "mm[Hg]",
            "respiratory_rate": "/min",
            "oxygen_saturation": "%"
        }
        return units.get(vital_type, "")

class HIEConnector:
    """Health Information Exchange connector"""
    
    def __init__(self):
        self.hie_endpoints = settings.hie_endpoints or {}
    
    async def query_patient_data(self, patient_mrn: str) -> Dict[str, Any]:
        """Query external HIE for patient data"""
        results = {
            "demographics": None,
            "encounters": [],
            "medications": [],
            "allergies": [],
            "lab_results": []
        }
        
        # Query each connected HIE
        for hie_name, endpoint in self.hie_endpoints.items():
            try:
                hie_data = await self._query_hie_endpoint(endpoint, patient_mrn)
                if hie_data:
                    results = self._merge_hie_data(results, hie_data)
            except Exception as e:
                logger.error(f"Error querying HIE {hie_name}: {str(e)}")
        
        return results
    
    async def _query_hie_endpoint(self, endpoint: str, mrn: str) -> Optional[Dict[str, Any]]:
        """Query specific HIE endpoint"""
        # Implementation would depend on HIE specifications
        # Common standards: IHE XDS, FHIR, Direct Trust
        pass
    
    def _merge_hie_data(self, existing: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge HIE data with existing patient data"""
        # Implement data reconciliation logic
        # Handle duplicates, conflicts, and data quality issues
        pass

class ClinicalDataExchange:
    """Clinical data exchange with external systems"""
    
    def __init__(self):
        self.fhir_service = FHIRService()
        self.hie_connector = HIEConnector()
    
    async def export_patient_summary(self, patient_id: str, db) -> Dict[str, Any]:
        """Export comprehensive patient summary in FHIR format"""
        from sqlalchemy.orm import Session
        
        # Get patient data
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise ValueError("Patient not found")
        
        # Create FHIR Bundle
        bundle = {
            "resourceType": "Bundle",
            "id": f"patient-summary-{patient_id}",
            "type": "collection",
            "timestamp": datetime.utcnow().isoformat(),
            "entry": []
        }
        
        # Add patient resource
        patient_resource = await self.fhir_service.create_patient_resource(patient)
        bundle["entry"].append({
            "resource": patient_resource
        })
        
        # Add encounters
        encounters = db.query(Encounter).filter(Encounter.patient_id == patient_id).all()
        for encounter in encounters:
            encounter_resource = await self.fhir_service.create_encounter_resource(encounter)
            bundle["entry"].append({
                "resource": encounter_resource
            })
        
        return bundle
    
    async def import_external_data(self, patient_mrn: str, db) -> Dict[str, Any]:
        """Import patient data from external HIEs"""
        external_data = await self.hie_connector.query_patient_data(patient_mrn)
        
        # Process and validate external data
        import_summary = {
            "records_found": 0,
            "records_imported": 0,
            "conflicts": [],
            "errors": []
        }
        
        # Implementation would include data validation,
        # conflict resolution, and selective import
        
        return import_summary