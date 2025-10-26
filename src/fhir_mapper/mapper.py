"""
FHIR Mapper - Convert extracted data to FHIR resources
Supports CoverageEligibilityResponse, ClaimResponse, PriorAuthorization, and more
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
import uuid
import json

from fhir.resources.coverageeligibilityresponse import CoverageEligibilityResponse
from fhir.resources.claimresponse import ClaimResponse
from fhir.resources.claim import Claim
from fhir.resources.patient import Patient
from fhir.resources.coverage import Coverage
from fhir.resources.organization import Organization
from fhir.resources.identifier import Identifier
from fhir.resources.period import Period
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.reference import Reference
from fhir.resources.money import Money
from fhir.resources.quantity import Quantity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FHIRConversionResult:
    """FHIR conversion result"""
    resource_type: str
    fhir_resource: Any
    resource_id: str
    validation_status: bool
    validation_errors: List[str]
    metadata: Dict[str, Any]


class FHIRMapper:
    """
    Convert extracted healthcare data to FHIR R4 resources
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('fhir_base_url', 'https://fhir.payerhub.com')
        
        logger.info("FHIR Mapper initialized")
    
    def generate_fhir_id(self) -> str:
        """Generate a unique FHIR resource ID"""
        return str(uuid.uuid4())
    
    def create_patient_resource(self, patient_data: Dict[str, Any]) -> Patient:
        """
        Create a FHIR Patient resource
        """
        patient_id = self.generate_fhir_id()
        
        # Create identifier
        identifiers = []
        if 'patient_id' in patient_data:
            identifier = Identifier(**{
                'system': 'http://hospital.org/patient-id',
                'value': patient_data['patient_id']
            })
            identifiers.append(identifier)
        
        if 'ssn' in patient_data:
            ssn_identifier = Identifier(**{
                'system': 'http://hl7.org/fhir/sid/us-ssn',
                'value': patient_data['ssn']
            })
            identifiers.append(ssn_identifier)
        
        # Parse name
        name_parts = []
        if 'name' in patient_data:
            from fhir.resources.humanname import HumanName
            name = HumanName(**{
                'text': patient_data['name'],
                'family': patient_data.get('last_name', ''),
                'given': [patient_data.get('first_name', '')]
            })
            name_parts.append(name)
        
        # Parse DOB
        birth_date = None
        if 'date_of_birth' in patient_data:
            # Assuming format MM/DD/YYYY
            try:
                dob = datetime.strptime(patient_data['date_of_birth'], '%m/%d/%Y')
                birth_date = dob.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        # Create telecom
        telecoms = []
        if 'phone' in patient_data:
            from fhir.resources.contactpoint import ContactPoint
            phone = ContactPoint(**{
                'system': 'phone',
                'value': patient_data['phone']
            })
            telecoms.append(phone)
        
        # Build patient resource
        patient = Patient(**{
            'id': patient_id,
            'identifier': identifiers if identifiers else None,
            'name': name_parts if name_parts else None,
            'birthDate': birth_date,
            'telecom': telecoms if telecoms else None
        })
        
        return patient
    
    def create_coverage_resource(
        self, 
        insurance_data: Dict[str, Any],
        patient_reference: str
    ) -> Coverage:
        """
        Create a FHIR Coverage resource
        """
        coverage_id = self.generate_fhir_id()
        
        # Create identifier
        identifiers = []
        if 'member_id' in insurance_data or 'insurance_id' in insurance_data:
            member_id = insurance_data.get('member_id') or insurance_data.get('insurance_id')
            identifier = Identifier(**{
                'system': 'http://insurance.org/member-id',
                'value': member_id
            })
            identifiers.append(identifier)
        
        # Create payor reference
        payor_reference = None
        if 'payer_name' in insurance_data:
            payor_reference = Reference(**{
                'display': insurance_data['payer_name']
            })
        
        # Create period
        period = None
        if 'effective_date' in insurance_data or 'expiry_date' in insurance_data:
            period_data = {}
            if 'effective_date' in insurance_data:
                period_data['start'] = insurance_data['effective_date']
            if 'expiry_date' in insurance_data:
                period_data['end'] = insurance_data['expiry_date']
            period = Period(**period_data)
        
        # Build coverage resource
        coverage = Coverage(**{
            'id': coverage_id,
            'identifier': identifiers if identifiers else None,
            'status': 'active',
            'beneficiary': Reference(**{'reference': patient_reference}),
            'payor': [payor_reference] if payor_reference else None,
            'period': period
        })
        
        return coverage
    
    def create_eligibility_response(
        self,
        eligibility_data: Dict[str, Any],
        patient_data: Dict[str, Any],
        insurance_data: Dict[str, Any]
    ) -> FHIRConversionResult:
        """
        Create FHIR CoverageEligibilityResponse resource
        """
        try:
            # Create patient
            patient = self.create_patient_resource(patient_data)
            patient_ref = f"Patient/{patient.id}"
            
            # Create coverage
            coverage = self.create_coverage_resource(insurance_data, patient_ref)
            coverage_ref = f"Coverage/{coverage.id}"
            
            # Build eligibility response
            response_id = self.generate_fhir_id()
            
            # Create insurance items
            insurance_items = []
            from fhir.resources.coverageeligibilityresponse import CoverageEligibilityResponseInsurance, CoverageEligibilityResponseInsuranceItem
            
            insurance = CoverageEligibilityResponseInsurance(**{
                'coverage': Reference(**{'reference': coverage_ref}),
                'inforce': eligibility_data.get('coverage_status', 'active') == 'active'
            })
            
            # Add benefit items
            if 'benefits' in eligibility_data:
                items = []
                for benefit in eligibility_data['benefits']:
                    item = CoverageEligibilityResponseInsuranceItem(**{
                        'category': CodeableConcept(**{
                            'coding': [Coding(**{
                                'system': 'http://terminology.hl7.org/CodeSystem/ex-benefitcategory',
                                'code': benefit.get('category', 'medical')
                            })]
                        }),
                        'network': CodeableConcept(**{
                            'coding': [Coding(**{
                                'system': 'http://terminology.hl7.org/CodeSystem/benefit-network',
                                'code': benefit.get('network', 'in')
                            })]
                        })
                    })
                    items.append(item)
                
                insurance.item = items
            
            insurance_items.append(insurance)
            
            # Build response
            eligibility_response = CoverageEligibilityResponse(**{
                'id': response_id,
                'status': 'active',
                'purpose': ['validation'],
                'patient': Reference(**{'reference': patient_ref}),
                'created': datetime.now().isoformat(),
                'insurer': Reference(**{
                    'display': insurance_data.get('payer_name', 'Unknown Insurer')
                }),
                'outcome': 'complete',
                'insurance': insurance_items
            })
            
            # Validate
            validation_errors = []
            try:
                eligibility_response.dict()  # Validates the resource
                validation_status = True
            except Exception as e:
                validation_errors.append(str(e))
                validation_status = False
            
            return FHIRConversionResult(
                resource_type='CoverageEligibilityResponse',
                fhir_resource=eligibility_response,
                resource_id=response_id,
                validation_status=validation_status,
                validation_errors=validation_errors,
                metadata={
                    'created_at': datetime.now().isoformat(),
                    'source': 'PayerHub Integration'
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create eligibility response: {e}")
            raise
    
    def create_claim_resource(
        self,
        claim_data: Dict[str, Any],
        patient_data: Dict[str, Any],
        insurance_data: Dict[str, Any]
    ) -> FHIRConversionResult:
        """
        Create FHIR Claim resource
        """
        try:
            # Create patient
            patient = self.create_patient_resource(patient_data)
            patient_ref = f"Patient/{patient.id}"
            
            # Create coverage
            coverage = self.create_coverage_resource(insurance_data, patient_ref)
            coverage_ref = f"Coverage/{coverage.id}"
            
            # Build claim
            claim_id = self.generate_fhir_id()
            
            # Create identifier
            identifiers = []
            if 'claim_number' in claim_data:
                identifier = Identifier(**{
                    'system': 'http://hospital.org/claim-id',
                    'value': claim_data['claim_number']
                })
                identifiers.append(identifier)
            
            # Create diagnosis
            diagnoses = []
            if 'diagnosis_codes' in claim_data or 'icd_codes' in claim_data:
                from fhir.resources.claim import ClaimDiagnosis
                codes = claim_data.get('diagnosis_codes') or claim_data.get('icd_codes', [])
                
                for idx, code in enumerate(codes):
                    diagnosis = ClaimDiagnosis(**{
                        'sequence': idx + 1,
                        'diagnosisCodeableConcept': CodeableConcept(**{
                            'coding': [Coding(**{
                                'system': 'http://hl7.org/fhir/sid/icd-10',
                                'code': code
                            })]
                        })
                    })
                    diagnoses.append(diagnosis)
            
            # Create items (procedures/services)
            items = []
            if 'procedure_codes' in claim_data or 'cpt_codes' in claim_data:
                from fhir.resources.claim import ClaimItem
                codes = claim_data.get('procedure_codes') or claim_data.get('cpt_codes', [])
                
                for idx, code in enumerate(codes):
                    item = ClaimItem(**{
                        'sequence': idx + 1,
                        'productOrService': CodeableConcept(**{
                            'coding': [Coding(**{
                                'system': 'http://www.ama-assn.org/go/cpt',
                                'code': code
                            })]
                        }),
                        'servicedDate': claim_data.get('service_date', datetime.now().strftime('%Y-%m-%d'))
                    })
                    
                    # Add amount if available
                    if 'billed_amount' in claim_data:
                        item.unitPrice = Money(**{
                            'value': float(claim_data['billed_amount']),
                            'currency': 'USD'
                        })
                    
                    items.append(item)
            
            # Create insurance
            insurance_items = []
            from fhir.resources.claim import ClaimInsurance
            insurance = ClaimInsurance(**{
                'sequence': 1,
                'focal': True,
                'coverage': Reference(**{'reference': coverage_ref})
            })
            insurance_items.append(insurance)
            
            # Create total
            total = None
            if 'billed_amount' in claim_data:
                total = Money(**{
                    'value': float(claim_data['billed_amount']),
                    'currency': 'USD'
                })
            
            # Build claim
            claim = Claim(**{
                'id': claim_id,
                'identifier': identifiers if identifiers else None,
                'status': claim_data.get('status', 'active'),
                'type': CodeableConcept(**{
                    'coding': [Coding(**{
                        'system': 'http://terminology.hl7.org/CodeSystem/claim-type',
                        'code': 'professional'
                    })]
                }),
                'use': 'claim',
                'patient': Reference(**{'reference': patient_ref}),
                'created': claim_data.get('created_date', datetime.now().isoformat()),
                'insurer': Reference(**{
                    'display': insurance_data.get('payer_name', 'Unknown Insurer')
                }),
                'provider': Reference(**{
                    'display': claim_data.get('provider_name', 'Unknown Provider')
                }),
                'priority': CodeableConcept(**{
                    'coding': [Coding(**{
                        'system': 'http://terminology.hl7.org/CodeSystem/processpriority',
                        'code': 'normal'
                    })]
                }),
                'diagnosis': diagnoses if diagnoses else None,
                'insurance': insurance_items,
                'item': items if items else None,
                'total': total
            })
            
            # Validate
            validation_errors = []
            try:
                claim.dict()
                validation_status = True
            except Exception as e:
                validation_errors.append(str(e))
                validation_status = False
            
            return FHIRConversionResult(
                resource_type='Claim',
                fhir_resource=claim,
                resource_id=claim_id,
                validation_status=validation_status,
                validation_errors=validation_errors,
                metadata={
                    'created_at': datetime.now().isoformat(),
                    'source': 'PayerHub Integration'
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create claim: {e}")
            raise
    
    def create_prior_authorization(
        self,
        auth_data: Dict[str, Any],
        patient_data: Dict[str, Any],
        insurance_data: Dict[str, Any]
    ) -> FHIRConversionResult:
        """
        Create FHIR resources for Prior Authorization
        Uses Claim with use='preauthorization'
        """
        try:
            # Prior auth uses Claim resource with use='preauthorization'
            claim_data = {
                'claim_number': auth_data.get('auth_number'),
                'status': 'active',
                'created_date': auth_data.get('approval_date', datetime.now().isoformat()),
                'diagnosis_codes': auth_data.get('diagnosis_codes', []),
                'procedure_codes': auth_data.get('procedure_codes', []),
                'service_date': auth_data.get('service_date'),
                'billed_amount': auth_data.get('estimated_cost')
            }
            
            # Create patient
            patient = self.create_patient_resource(patient_data)
            patient_ref = f"Patient/{patient.id}"
            
            # Create coverage
            coverage = self.create_coverage_resource(insurance_data, patient_ref)
            coverage_ref = f"Coverage/{coverage.id}"
            
            # Build prior auth claim
            auth_id = self.generate_fhir_id()
            
            # Create identifier
            identifiers = []
            if 'auth_number' in auth_data:
                identifier = Identifier(**{
                    'system': 'http://insurance.org/prior-auth-id',
                    'value': auth_data['auth_number']
                })
                identifiers.append(identifier)
            
            # Create diagnosis
            diagnoses = []
            if 'diagnosis_codes' in auth_data:
                from fhir.resources.claim import ClaimDiagnosis
                
                for idx, code in enumerate(auth_data['diagnosis_codes']):
                    diagnosis = ClaimDiagnosis(**{
                        'sequence': idx + 1,
                        'diagnosisCodeableConcept': CodeableConcept(**{
                            'coding': [Coding(**{
                                'system': 'http://hl7.org/fhir/sid/icd-10',
                                'code': code
                            })]
                        })
                    })
                    diagnoses.append(diagnosis)
            
            # Create items
            items = []
            if 'medication' in auth_data or 'procedure_codes' in auth_data:
                from fhir.resources.claim import ClaimItem
                
                item = ClaimItem(**{
                    'sequence': 1,
                    'productOrService': CodeableConcept(**{
                        'text': auth_data.get('medication', 'Unknown')
                    }),
                    'servicedDate': auth_data.get('service_date', datetime.now().strftime('%Y-%m-%d'))
                })
                items.append(item)
            
            # Create insurance
            insurance_items = []
            from fhir.resources.claim import ClaimInsurance
            insurance = ClaimInsurance(**{
                'sequence': 1,
                'focal': True,
                'coverage': Reference(**{'reference': coverage_ref})
            })
            insurance_items.append(insurance)
            
            # Build prior authorization claim
            prior_auth = Claim(**{
                'id': auth_id,
                'identifier': identifiers if identifiers else None,
                'status': 'active',
                'type': CodeableConcept(**{
                    'coding': [Coding(**{
                        'system': 'http://terminology.hl7.org/CodeSystem/claim-type',
                        'code': 'professional'
                    })]
                }),
                'use': 'preauthorization',
                'patient': Reference(**{'reference': patient_ref}),
                'created': auth_data.get('approval_date', datetime.now().isoformat()),
                'insurer': Reference(**{
                    'display': insurance_data.get('payer_name', 'Unknown Insurer')
                }),
                'provider': Reference(**{
                    'display': auth_data.get('provider_name', 'Unknown Provider')
                }),
                'priority': CodeableConcept(**{
                    'coding': [Coding(**{
                        'system': 'http://terminology.hl7.org/CodeSystem/processpriority',
                        'code': 'stat'
                    })]
                }),
                'diagnosis': diagnoses if diagnoses else None,
                'insurance': insurance_items,
                'item': items if items else None
            })
            
            # Validate
            validation_errors = []
            try:
                prior_auth.dict()
                validation_status = True
            except Exception as e:
                validation_errors.append(str(e))
                validation_status = False
            
            return FHIRConversionResult(
                resource_type='Claim',
                fhir_resource=prior_auth,
                resource_id=auth_id,
                validation_status=validation_status,
                validation_errors=validation_errors,
                metadata={
                    'created_at': datetime.now().isoformat(),
                    'source': 'PayerHub Integration',
                    'type': 'prior_authorization'
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create prior authorization: {e}")
            raise
    
    def convert_to_fhir(
        self,
        extracted_data: Dict[str, Any]
    ) -> FHIRConversionResult:
        """
        Main entry point - convert extracted data to appropriate FHIR resource
        """
        document_type = extracted_data.get('document_type', 'UNKNOWN')
        
        patient_data = extracted_data.get('patient_info', {})
        insurance_data = extracted_data.get('insurance_info', {})
        
        if document_type == 'PRIOR_AUTHORIZATION':
            return self.create_prior_authorization(
                extracted_data.get('clinical_info', {}),
                patient_data,
                insurance_data
            )
        
        elif document_type == 'ELIGIBILITY_VERIFICATION':
            return self.create_eligibility_response(
                extracted_data.get('eligibility_data', {}),
                patient_data,
                insurance_data
            )
        
        elif document_type in ['CLAIM', 'EXPLANATION_OF_BENEFITS']:
            return self.create_claim_resource(
                extracted_data.get('claim_data', {}),
                patient_data,
                insurance_data
            )
        
        else:
            raise ValueError(f"Unsupported document type: {document_type}")


# Example usage
if __name__ == "__main__":
    config = {
        'fhir_base_url': 'https://fhir.payerhub.com'
    }
    
    mapper = FHIRMapper(config)
    
    # Example extracted data
    sample_data = {
        'document_type': 'PRIOR_AUTHORIZATION',
        'patient_info': {
            'patient_id': 'PAT123456',
            'name': 'John Doe',
            'date_of_birth': '01/15/1970'
        },
        'insurance_info': {
            'member_id': 'INS789012',
            'payer_name': 'Blue Cross Blue Shield'
        },
        'clinical_info': {
            'auth_number': 'AUTH-2024-001',
            'medication': 'Humira 40mg',
            'diagnosis_codes': ['M06.9'],
            'approval_date': '2024-10-15'
        }
    }
    
    # Convert to FHIR
    result = mapper.convert_to_fhir(sample_data)
    
    print(f"Resource Type: {result.resource_type}")
    print(f"Resource ID: {result.resource_id}")
    print(f"Validation Status: {result.validation_status}")
    print(f"FHIR Resource: {result.fhir_resource.json(indent=2)}")
