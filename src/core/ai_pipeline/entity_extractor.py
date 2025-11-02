"""
NLP Entity Extractor for Healthcare Documents
Uses BioBERT, ClinicalBERT, and specialized medical NER models
Extracts patient information, medications, diagnoses, dates, and insurance data
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
import re

import spacy
from transformers import (
    AutoTokenizer, 
    AutoModelForTokenClassification,
    pipeline
)
import torch
from scispacy.linking import EntityLinker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Extracted entity"""
    text: str
    type: str
    start: int
    end: int
    confidence: float
    normalized_code: Optional[str] = None


@dataclass
class ExtractionResult:
    """Complete extraction result"""
    entities: List[Entity]
    patient_info: Dict[str, Any]
    insurance_info: Dict[str, Any]
    clinical_info: Dict[str, Any]
    temporal_info: Dict[str, Any]
    raw_text: str
    metadata: Dict[str, Any]


class EntityExtractor:
    """
    Advanced NLP entity extraction for healthcare documents
    Combines multiple models for comprehensive information extraction
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.device = torch.device('cuda' if config.get('use_gpu', False) else 'cpu')
        
        # Load BioBERT for biomedical NER
        self.biobert_model = config.get('biobert_model', 'dmis-lab/biobert-base-cased-v1.1')
        self.tokenizer = AutoTokenizer.from_pretrained(self.biobert_model)
        self.model = AutoModelForTokenClassification.from_pretrained(self.biobert_model)
        self.model.to(self.device)
        
        # Load spaCy for general NER
        self.nlp = spacy.load("en_core_web_sm")
        
        # Load scispacy for medical entity linking
        try:
            self.sci_nlp = spacy.load("en_core_sci_md")
            self.sci_nlp.add_pipe("scispacy_linker", config={"resolve_abbreviations": True})
        except Exception as e:
            logger.warning(f"SciSpacy not available: {e}")
            self.sci_nlp = None
        
        # Initialize HuggingFace NER pipeline
        self.ner_pipeline = pipeline(
            "ner",
            model=self.biobert_model,
            tokenizer=self.tokenizer,
            device=0 if config.get('use_gpu', False) else -1,
            aggregation_strategy="simple"
        )
        
        # Regex patterns for specific entities
        self.patterns = self._compile_patterns()
        
        logger.info("Entity Extractor initialized")
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for entity extraction"""
        return {
            'patient_id': re.compile(r'\b(?:MRN|Patient ID|Medical Record)[\s:]+([A-Z0-9\-]+)\b', re.IGNORECASE),
            'insurance_id': re.compile(r'\b(?:Member ID|Insurance ID|Policy)[\s:]+([A-Z0-9\-]+)\b', re.IGNORECASE),
            'date': re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'auth_number': re.compile(r'\b(?:Auth|Authorization)[\s#:]+([A-Z0-9\-]+)\b', re.IGNORECASE),
            'npi': re.compile(r'\b(?:NPI|National Provider)[\s:]+(\d{10})\b', re.IGNORECASE),
            'icd_code': re.compile(r'\b([A-Z]\d{2}(?:\.\d{1,4})?)\b'),
            'cpt_code': re.compile(r'\b(\d{5})\b'),
            'ndc_code': re.compile(r'\b(\d{5}-\d{4}-\d{2}|\d{11})\b')
        }
    
    def extract_entities_biobert(self, text: str) -> List[Entity]:
        """
        Extract entities using BioBERT NER pipeline
        """
        try:
            results = self.ner_pipeline(text)
            
            entities = []
            for result in results:
                entity = Entity(
                    text=result['word'],
                    type=result['entity_group'],
                    start=result['start'],
                    end=result['end'],
                    confidence=result['score']
                )
                entities.append(entity)
            
            return entities
            
        except Exception as e:
            logger.error(f"BioBERT extraction failed: {e}")
            return []
    
    def extract_entities_spacy(self, text: str) -> List[Entity]:
        """
        Extract entities using spaCy
        """
        try:
            doc = self.nlp(text)
            
            entities = []
            for ent in doc.ents:
                entity = Entity(
                    text=ent.text,
                    type=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=1.0  # spaCy doesn't provide confidence
                )
                entities.append(entity)
            
            return entities
            
        except Exception as e:
            logger.error(f"spaCy extraction failed: {e}")
            return []
    
    def extract_medical_entities_scispacy(self, text: str) -> List[Entity]:
        """
        Extract and link medical entities using SciSpacy
        """
        if not self.sci_nlp:
            return []
        
        try:
            doc = self.sci_nlp(text)
            
            entities = []
            for ent in doc.ents:
                # Get linked entity codes (UMLS CUI)
                linked_entities = ent._.kb_ents if hasattr(ent._, 'kb_ents') else []
                normalized_code = linked_entities[0][0] if linked_entities else None
                
                entity = Entity(
                    text=ent.text,
                    type=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=1.0,
                    normalized_code=normalized_code
                )
                entities.append(entity)
            
            return entities
            
        except Exception as e:
            logger.error(f"SciSpacy extraction failed: {e}")
            return []
    
    def extract_regex_patterns(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities using regex patterns
        """
        matches = {}
        
        for pattern_name, pattern in self.patterns.items():
            found = pattern.findall(text)
            if found:
                matches[pattern_name] = found
        
        return matches
    
    def extract_patient_info(
        self, 
        text: str, 
        entities: List[Entity],
        regex_matches: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Extract patient demographic information
        """
        patient_info = {}
        
        # Extract patient name (PERSON entities from spaCy)
        person_entities = [e for e in entities if e.type == 'PERSON']
        if person_entities:
            patient_info['name'] = person_entities[0].text
        
        # Extract patient ID from regex
        if 'patient_id' in regex_matches:
            patient_info['patient_id'] = regex_matches['patient_id'][0]
        
        # Extract dates of birth
        if 'date' in regex_matches:
            patient_info['dates'] = regex_matches['date']
        
        # Extract contact information
        if 'phone' in regex_matches:
            patient_info['phone'] = regex_matches['phone'][0]
        
        # Extract SSN (if present)
        if 'ssn' in regex_matches:
            patient_info['ssn'] = regex_matches['ssn'][0]
        
        return patient_info
    
    def extract_insurance_info(
        self, 
        text: str,
        entities: List[Entity],
        regex_matches: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Extract insurance and payer information
        """
        insurance_info = {}
        
        # Extract insurance/payer name (ORG entities)
        org_entities = [e for e in entities if e.type == 'ORG']
        if org_entities:
            insurance_info['payer_name'] = org_entities[0].text
        
        # Extract insurance ID
        if 'insurance_id' in regex_matches:
            insurance_info['member_id'] = regex_matches['insurance_id'][0]
        
        # Extract authorization number
        if 'auth_number' in regex_matches:
            insurance_info['auth_number'] = regex_matches['auth_number'][0]
        
        return insurance_info
    
    def extract_clinical_info(
        self, 
        text: str,
        entities: List[Entity],
        regex_matches: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Extract clinical information (diagnoses, procedures, medications)
        """
        clinical_info = {}
        
        # Extract diagnosis codes (ICD)
        if 'icd_code' in regex_matches:
            clinical_info['icd_codes'] = regex_matches['icd_code']
        
        # Extract procedure codes (CPT)
        if 'cpt_code' in regex_matches:
            clinical_info['cpt_codes'] = regex_matches['cpt_code']
        
        # Extract medication codes (NDC)
        if 'ndc_code' in regex_matches:
            clinical_info['ndc_codes'] = regex_matches['ndc_code']
        
        # Extract medical conditions from entities
        condition_entities = [e for e in entities if e.type in ['DISEASE', 'CONDITION', 'SYMPTOM']]
        if condition_entities:
            clinical_info['conditions'] = [e.text for e in condition_entities]
        
        # Extract medications from entities
        drug_entities = [e for e in entities if e.type in ['DRUG', 'MEDICATION', 'CHEMICAL']]
        if drug_entities:
            clinical_info['medications'] = [e.text for e in drug_entities]
        
        # Extract provider NPI
        if 'npi' in regex_matches:
            clinical_info['provider_npi'] = regex_matches['npi'][0]
        
        return clinical_info
    
    def extract_temporal_info(
        self, 
        text: str,
        entities: List[Entity],
        regex_matches: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Extract temporal information (dates, durations)
        """
        temporal_info = {}
        
        # Extract dates
        if 'date' in regex_matches:
            temporal_info['dates'] = regex_matches['date']
        
        # Extract date entities from NER
        date_entities = [e for e in entities if e.type == 'DATE']
        if date_entities:
            temporal_info['ner_dates'] = [e.text for e in date_entities]
        
        # Try to identify specific date types from context
        text_lower = text.lower()
        
        if 'approval date' in text_lower or 'approved on' in text_lower:
            # Find date near "approval"
            approval_idx = text_lower.find('approval')
            nearby_text = text[max(0, approval_idx-50):approval_idx+100]
            dates = self.patterns['date'].findall(nearby_text)
            if dates:
                temporal_info['approval_date'] = dates[0]
        
        if 'expir' in text_lower:
            # Find date near "expir"
            expiry_idx = text_lower.find('expir')
            nearby_text = text[max(0, expiry_idx-50):expiry_idx+100]
            dates = self.patterns['date'].findall(nearby_text)
            if dates:
                temporal_info['expiry_date'] = dates[0]
        
        return temporal_info
    
    def extract_all(self, text: str) -> ExtractionResult:
        """
        Perform complete entity extraction using all methods
        """
        logger.info("Starting entity extraction")
        
        # Extract entities using different methods
        biobert_entities = self.extract_entities_biobert(text)
        spacy_entities = self.extract_entities_spacy(text)
        scispacy_entities = self.extract_medical_entities_scispacy(text)
        
        # Combine all entities
        all_entities = biobert_entities + spacy_entities + scispacy_entities
        
        # Deduplicate entities
        unique_entities = self._deduplicate_entities(all_entities)
        
        # Extract using regex patterns
        regex_matches = self.extract_regex_patterns(text)
        
        # Extract structured information
        patient_info = self.extract_patient_info(text, unique_entities, regex_matches)
        insurance_info = self.extract_insurance_info(text, unique_entities, regex_matches)
        clinical_info = self.extract_clinical_info(text, unique_entities, regex_matches)
        temporal_info = self.extract_temporal_info(text, unique_entities, regex_matches)
        
        return ExtractionResult(
            entities=unique_entities,
            patient_info=patient_info,
            insurance_info=insurance_info,
            clinical_info=clinical_info,
            temporal_info=temporal_info,
            raw_text=text,
            metadata={
                'num_entities': len(unique_entities),
                'extraction_timestamp': datetime.now().isoformat(),
                'models_used': ['BioBERT', 'spaCy', 'SciSpacy']
            }
        )
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Remove duplicate entities based on text and position
        """
        seen = set()
        unique = []
        
        for entity in entities:
            key = (entity.text.lower(), entity.start, entity.end)
            if key not in seen:
                seen.add(key)
                unique.append(entity)
        
        return unique


# Example usage
if __name__ == "__main__":
    config = {
        'biobert_model': 'dmis-lab/biobert-base-cased-v1.1',
        'use_gpu': True
    }
    
    extractor = EntityExtractor(config)
    
    # Example text
    sample_text = """
    Patient: John Doe
    MRN: 12345678
    DOB: 01/15/1970
    Insurance: Blue Cross Blue Shield
    Member ID: BC123456789
    Authorization Number: AUTH-2024-001
    
    Diagnosis: Type 2 Diabetes Mellitus (E11.9)
    Medication: Metformin 1000mg
    Procedure: Glucose tolerance test (CPT: 82951)
    
    Prior Authorization approved on 10/15/2024
    Valid through 01/15/2025
    """
    
    # Extract entities
    result = extractor.extract_all(sample_text)
    
    print(f"Extracted {len(result.entities)} entities")
    print(f"Patient Info: {result.patient_info}")
    print(f"Insurance Info: {result.insurance_info}")
    print(f"Clinical Info: {result.clinical_info}")
    print(f"Temporal Info: {result.temporal_info}")
