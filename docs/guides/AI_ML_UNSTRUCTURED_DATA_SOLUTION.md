# AI/ML Solution for Unstructured Payer Data Processing

## Executive Summary

This document provides a comprehensive technical implementation guide for solving the **unstructured data problem** in payer-hub integrations using AI/ML techniques. It builds upon the reference architecture defined in "Event-Driven Real-Time Integration of Payer Data with Patient Service Hubs."

---

## 🎯 Problem Statement

### The Unstructured Data Challenge

Patient service hubs currently receive payer information through multiple unstructured channels:

| **Input Source** | **Format** | **Challenge** |
|-----------------|-----------|---------------|
| Prior Authorization Forms | PDF/TIFF | Layout variability, handwritten notes |
| Faxed Documents | Scanned images | Poor quality, mixed content types |
| Email Attachments | Multiple formats | Free-text descriptions, variable structure |
| Portal Screenshots | Images/PDFs | Non-standard layouts, OCR difficulties |
| Physician Notes | Free text | Clinical abbreviations, context-dependent |
| Appeals Documentation | Mixed documents | Multi-page, references to other documents |

These inputs need to be transformed into **structured FHIR R4 resources** such as:
- `CoverageEligibilityResponse`
- `ClaimResponse`
- `ServiceRequest` (Prior Authorization)
- `ExplanationOfBenefit`

---

## 🧠 Three-Layer AI/ML Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Layer 1: INGESTION                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ OCR Engine   │  │ Layout Model │  │ Text Extract │         │
│  │ (Tesseract)  │→│ (LayoutLMv3) │→│              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                Layer 2: STRUCTURING & EXTRACTION                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ NER Model    │  │ Relation     │  │ FHIR Mapper  │         │
│  │ (BioBERT)    │→│ Extraction   │→│              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              Layer 3: VALIDATION & QUALITY ASSURANCE            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Anomaly      │  │ Confidence   │  │ Human-in-    │         │
│  │ Detection    │→│ Scoring      │→│ the-Loop     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Layer 1: Data Ingestion & Document Understanding

### 1.1 OCR Processing with Layout Awareness

**Objective**: Convert images/PDFs to machine-readable text while preserving document structure.

#### Technology Stack:
- **Tesseract OCR**: General text extraction
- **LayoutLMv3**: Document layout understanding
- **Donut**: End-to-end document understanding without OCR
- **pdf2image**: PDF to image conversion

#### Implementation:

```python
# File: src/ai_pipeline/ocr_processor.py

import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
import torch

class OCRProcessor:
    def __init__(self, config):
        self.config = config
        self.use_layout_model = config.get('use_layout_model', True)
        
        if self.use_layout_model:
            # Load pre-trained LayoutLMv3 model
            self.layout_processor = LayoutLMv3Processor.from_pretrained(
                "microsoft/layoutlmv3-base"
            )
            self.layout_model = LayoutLMv3ForTokenClassification.from_pretrained(
                "microsoft/layoutlmv3-base"
            )
    
    def process_document(self, file_path):
        """
        Main entry point for document processing
        Returns structured text with layout information
        """
        # Step 1: Convert PDF to images if needed
        if file_path.lower().endswith('.pdf'):
            images = convert_from_path(file_path, dpi=300)
        else:
            images = [Image.open(file_path)]
        
        results = []
        for idx, image in enumerate(images):
            page_result = self._process_single_page(image, page_num=idx+1)
            results.append(page_result)
        
        return self._merge_pages(results)
    
    def _process_single_page(self, image, page_num):
        """Process a single page/image"""
        # Basic OCR with Tesseract
        ocr_text = pytesseract.image_to_string(
            image, 
            config='--oem 3 --psm 6'  # LSTM OCR, uniform text block
        )
        
        # Get bounding boxes for layout analysis
        ocr_data = pytesseract.image_to_data(
            image, 
            output_type=pytesseract.Output.DICT
        )
        
        if self.use_layout_model:
            # Use LayoutLMv3 for better structure understanding
            layout_result = self._apply_layout_model(image, ocr_data)
            return {
                'page_num': page_num,
                'text': ocr_text,
                'layout_structure': layout_result,
                'raw_ocr_data': ocr_data
            }
        
        return {
            'page_num': page_num,
            'text': ocr_text,
            'raw_ocr_data': ocr_data
        }
    
    def _apply_layout_model(self, image, ocr_data):
        """
        Use LayoutLMv3 to understand document structure
        Identifies: headers, tables, lists, key-value pairs
        """
        # Prepare inputs for LayoutLMv3
        encoding = self.layout_processor(
            image, 
            ocr_data['text'],
            boxes=self._get_normalized_boxes(ocr_data),
            return_tensors="pt"
        )
        
        # Run inference
        with torch.no_grad():
            outputs = self.layout_model(**encoding)
            predictions = outputs.logits.argmax(-1).squeeze().tolist()
        
        # Map predictions to semantic labels
        layout_structure = self._decode_layout_predictions(
            predictions, 
            ocr_data
        )
        
        return layout_structure
    
    def _get_normalized_boxes(self, ocr_data):
        """Normalize bounding boxes to 0-1000 range for LayoutLM"""
        width = max(ocr_data['width'])
        height = max(ocr_data['height'])
        
        boxes = []
        for i in range(len(ocr_data['text'])):
            if ocr_data['text'][i].strip():
                box = [
                    int(1000 * ocr_data['left'][i] / width),
                    int(1000 * ocr_data['top'][i] / height),
                    int(1000 * (ocr_data['left'][i] + ocr_data['width'][i]) / width),
                    int(1000 * (ocr_data['top'][i] + ocr_data['height'][i]) / height)
                ]
                boxes.append(box)
        
        return boxes
    
    def _decode_layout_predictions(self, predictions, ocr_data):
        """Convert model predictions to semantic structure"""
        # Label mapping for LayoutLMv3
        label_map = {
            0: 'O',          # Other
            1: 'HEADER',     # Section header
            2: 'FIELD_KEY',  # Form field label
            3: 'FIELD_VALUE',# Form field value
            4: 'TABLE',      # Table content
            5: 'LIST_ITEM'   # List item
        }
        
        structure = {
            'headers': [],
            'fields': {},
            'tables': [],
            'lists': []
        }
        
        current_key = None
        for idx, pred in enumerate(predictions):
            if idx >= len(ocr_data['text']):
                break
                
            text = ocr_data['text'][idx]
            label = label_map.get(pred, 'O')
            
            if label == 'HEADER':
                structure['headers'].append(text)
            elif label == 'FIELD_KEY':
                current_key = text
            elif label == 'FIELD_VALUE' and current_key:
                structure['fields'][current_key] = text
                current_key = None
            elif label == 'LIST_ITEM':
                structure['lists'].append(text)
        
        return structure
    
    def _merge_pages(self, page_results):
        """Merge multi-page results into single document"""
        merged = {
            'full_text': '\n\n'.join([p['text'] for p in page_results]),
            'pages': page_results,
            'num_pages': len(page_results)
        }
        
        # Merge layout structures if available
        if 'layout_structure' in page_results[0]:
            merged['combined_structure'] = self._combine_structures(
                [p['layout_structure'] for p in page_results]
            )
        
        return merged
    
    def _combine_structures(self, structures):
        """Combine layout structures from multiple pages"""
        combined = {
            'headers': [],
            'fields': {},
            'tables': [],
            'lists': []
        }
        
        for struct in structures:
            combined['headers'].extend(struct['headers'])
            combined['fields'].update(struct['fields'])
            combined['tables'].extend(struct['tables'])
            combined['lists'].extend(struct['lists'])
        
        return combined


# Usage Example
if __name__ == '__main__':
    config = {
        'use_layout_model': True,
        'tesseract_config': '--oem 3 --psm 6'
    }
    
    processor = OCRProcessor(config)
    result = processor.process_document('prior_auth_form.pdf')
    
    print(f"Extracted text length: {len(result['full_text'])} characters")
    print(f"Identified fields: {list(result['combined_structure']['fields'].keys())}")
```

### 1.2 Document Classification

Before processing, classify document type to apply appropriate extraction logic:

```python
# File: src/ai_pipeline/document_classifier.py

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class DocumentClassifier:
    def __init__(self):
        # Fine-tuned BERT model for healthcare document classification
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        self.model = AutoModelForSequenceClassification.from_pretrained(
            "bert-base-uncased",
            num_labels=6  # Number of document types
        )
        
        self.doc_types = [
            'prior_authorization',
            'eligibility_verification',
            'claim_form',
            'appeal_letter',
            'eob_explanation',
            'benefit_summary'
        ]
    
    def classify(self, text):
        """Classify document type from extracted text"""
        # Use first 512 tokens for classification
        inputs = self.tokenizer(
            text[:2000],  # Limit input size
            return_tensors="pt",
            truncation=True,
            max_length=512
        )
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        predicted_idx = predictions.argmax().item()
        confidence = predictions[0][predicted_idx].item()
        
        return {
            'document_type': self.doc_types[predicted_idx],
            'confidence': confidence,
            'all_scores': {
                doc_type: predictions[0][idx].item() 
                for idx, doc_type in enumerate(self.doc_types)
            }
        }
```

---

## 📊 Layer 2: NLP Entity Extraction & FHIR Mapping

### 2.1 Clinical NLP with BioBERT

**Objective**: Extract medical entities (patients, drugs, diagnoses, dates, payers) from unstructured text.

```python
# File: src/ai_pipeline/nlp_extractor.py

from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import spacy
import re
from datetime import datetime

class MedicalNLPExtractor:
    def __init__(self, config):
        self.config = config
        
        # Load BioBERT for medical NER
        if config.get('use_biobert', True):
            self.ner_pipeline = pipeline(
                "ner",
                model="dmis-lab/biobert-base-cased-v1.2",
                tokenizer="dmis-lab/biobert-base-cased-v1.2",
                aggregation_strategy="simple"
            )
        
        # Load spaCy for general NER
        self.nlp = spacy.load("en_core_web_sm")
        
        # Define regex patterns for structured data
        self.patterns = {
            'member_id': r'\b(?:Member|Patient|Subscriber)\s*(?:ID|Number|#)?\s*:?\s*([A-Z0-9]{7,12})\b',
            'date': r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            'npi': r'\b(NPI\s*:?\s*)?([\d]{10})\b',
            'diagnosis_code': r'\b([A-Z]\d{2}\.?\d{0,2})\b',  # ICD-10
            'cpt_code': r'\b(\d{5})\b',  # CPT codes
            'phone': r'\b(\d{3}[-.]?\d{3}[-.]?\d{4})\b',
            'authorization_number': r'\b(?:Auth|PA|Prior Auth)\s*(?:#|Number|ID)?\s*:?\s*([A-Z0-9]{8,15})\b'
        }
        
        # Payer name patterns
        self.payer_patterns = [
            r'Blue Cross Blue Shield',
            r'BCBS',
            r'Aetna',
            r'UnitedHealthcare',
            r'Cigna',
            r'Humana',
            r'Anthem',
            r'Kaiser'
        ]
    
    def extract_entities(self, text, layout_structure=None):
        """
        Extract all relevant entities from text
        Returns structured dictionary of entities
        """
        entities = {
            'patient_info': {},
            'payer_info': {},
            'clinical_info': {},
            'authorization_info': {},
            'dates': {},
            'providers': {}
        }
        
        # Use layout structure if available (from OCR)
        if layout_structure and 'fields' in layout_structure:
            entities = self._extract_from_fields(layout_structure['fields'], entities)
        
        # Extract using BioBERT NER
        biobert_entities = self._extract_biobert_entities(text)
        entities = self._merge_entities(entities, biobert_entities)
        
        # Extract using regex patterns
        regex_entities = self._extract_regex_entities(text)
        entities = self._merge_entities(entities, regex_entities)
        
        # Extract using spaCy
        spacy_entities = self._extract_spacy_entities(text)
        entities = self._merge_entities(entities, spacy_entities)
        
        # Post-processing and validation
        entities = self._validate_and_normalize(entities)
        
        return entities
    
    def _extract_from_fields(self, fields, entities):
        """Extract from structured form fields identified by OCR"""
        field_mappings = {
            'patient name': 'patient_info.name',
            'member id': 'patient_info.member_id',
            'date of birth': 'patient_info.dob',
            'insurance': 'payer_info.name',
            'policy number': 'payer_info.policy_number',
            'authorization number': 'authorization_info.auth_number',
            'diagnosis': 'clinical_info.diagnosis',
            'medication': 'clinical_info.medication',
            'provider': 'providers.name',
            'npi': 'providers.npi'
        }
        
        for field_name, value in fields.items():
            field_lower = field_name.lower().strip()
            for pattern, path in field_mappings.items():
                if pattern in field_lower:
                    self._set_nested_value(entities, path, value)
        
        return entities
    
    def _extract_biobert_entities(self, text):
        """Use BioBERT for medical entity extraction"""
        ner_results = self.ner_pipeline(text)
        
        entities = {
            'clinical_info': {
                'diagnoses': [],
                'medications': [],
                'procedures': []
            }
        }
        
        for entity in ner_results:
            entity_group = entity['entity_group']
            entity_text = entity['word']
            
            if entity_group == 'DISEASE':
                entities['clinical_info']['diagnoses'].append(entity_text)
            elif entity_group == 'CHEMICAL' or entity_group == 'DRUG':
                entities['clinical_info']['medications'].append(entity_text)
            elif entity_group == 'TREATMENT':
                entities['clinical_info']['procedures'].append(entity_text)
        
        return entities
    
    def _extract_regex_entities(self, text):
        """Extract structured entities using regex patterns"""
        entities = {
            'patient_info': {},
            'payer_info': {},
            'authorization_info': {},
            'providers': {},
            'dates': {}
        }
        
        # Member ID
        member_match = re.search(self.patterns['member_id'], text, re.IGNORECASE)
        if member_match:
            entities['patient_info']['member_id'] = member_match.group(1)
        
        # Authorization Number
        auth_match = re.search(self.patterns['authorization_number'], text, re.IGNORECASE)
        if auth_match:
            entities['authorization_info']['auth_number'] = auth_match.group(1)
        
        # Dates
        date_matches = re.findall(self.patterns['date'], text)
        if date_matches:
            parsed_dates = [self._parse_date(d) for d in date_matches]
            entities['dates']['extracted_dates'] = [d for d in parsed_dates if d]
        
        # NPI
        npi_match = re.search(self.patterns['npi'], text)
        if npi_match:
            entities['providers']['npi'] = npi_match.group(2)
        
        # Diagnosis codes (ICD-10)
        diagnosis_codes = re.findall(self.patterns['diagnosis_code'], text)
        if diagnosis_codes:
            entities['clinical_info'] = entities.get('clinical_info', {})
            entities['clinical_info']['diagnosis_codes'] = list(set(diagnosis_codes))
        
        # CPT codes
        cpt_codes = re.findall(self.patterns['cpt_code'], text)
        if cpt_codes:
            entities['clinical_info'] = entities.get('clinical_info', {})
            entities['clinical_info']['procedure_codes'] = list(set(cpt_codes))
        
        # Payer name
        for pattern in self.payer_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                entities['payer_info']['name'] = re.search(pattern, text, re.IGNORECASE).group(0)
                break
        
        return entities
    
    def _extract_spacy_entities(self, text):
        """Extract general entities using spaCy"""
        doc = self.nlp(text)
        
        entities = {
            'patient_info': {},
            'providers': {},
            'dates': {}
        }
        
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                # First PERSON entity is likely the patient
                if not entities['patient_info'].get('name'):
                    entities['patient_info']['name'] = ent.text
                elif not entities['providers'].get('name'):
                    entities['providers']['name'] = ent.text
            
            elif ent.label_ == 'DATE':
                dates_list = entities['dates'].get('extracted_dates', [])
                dates_list.append(ent.text)
                entities['dates']['extracted_dates'] = dates_list
            
            elif ent.label_ == 'ORG':
                # Could be payer or provider organization
                if not entities.get('payer_info', {}).get('name'):
                    entities.setdefault('payer_info', {})['name'] = ent.text
        
        return entities
    
    def _parse_date(self, date_str):
        """Parse date string to standard format"""
        formats = ['%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y']
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return None
    
    def _merge_entities(self, base, new):
        """Merge new entities into base dictionary"""
        for key, value in new.items():
            if key not in base:
                base[key] = value
            elif isinstance(value, dict) and isinstance(base[key], dict):
                base[key].update(value)
            elif isinstance(value, list) and isinstance(base[key], list):
                base[key].extend(value)
            else:
                if not base[key]:
                    base[key] = value
        
        return base
    
    def _validate_and_normalize(self, entities):
        """Validate and normalize extracted entities"""
        # Normalize member ID
        if 'patient_info' in entities and 'member_id' in entities['patient_info']:
            member_id = entities['patient_info']['member_id']
            entities['patient_info']['member_id'] = member_id.upper().replace(' ', '')
        
        # Normalize diagnosis codes
        if 'clinical_info' in entities and 'diagnosis_codes' in entities['clinical_info']:
            codes = entities['clinical_info']['diagnosis_codes']
            normalized = []
            for code in codes:
                # Ensure proper ICD-10 format (e.g., E11.9)
                if '.' not in code and len(code) > 3:
                    code = code[:3] + '.' + code[3:]
                normalized.append(code)
            entities['clinical_info']['diagnosis_codes'] = normalized
        
        # Remove duplicates from lists
        for category in entities.values():
            if isinstance(category, dict):
                for key, value in category.items():
                    if isinstance(value, list):
                        category[key] = list(set(value))
        
        return entities
    
    def _set_nested_value(self, dic, path, value):
        """Set value in nested dictionary using dot notation"""
        keys = path.split('.')
        for key in keys[:-1]:
            dic = dic.setdefault(key, {})
        dic[keys[-1]] = value


# Usage Example
if __name__ == '__main__':
    config = {
        'use_biobert': True,
        'use_clinical_bert': True
    }
    
    extractor = MedicalNLPExtractor(config)
    
    sample_text = """
    Prior Authorization Request
    Member ID: ABC123456
    Patient Name: John Doe
    Date of Birth: 05/15/1980
    Insurance: Blue Cross Blue Shield
    Policy #: BCBS-987654
    
    Diagnosis: Type 2 Diabetes Mellitus (E11.9)
    Medication Requested: Ozempic (semaglutide) 0.5mg
    Prescribing Provider: Dr. Jane Smith
    NPI: 1234567890
    
    Authorization Number: PA20250115A
    Approval Date: 01/15/2025
    Valid Through: 07/15/2025
    """
    
    entities = extractor.extract_entities(sample_text)
    print(entities)
```

### 2.2 FHIR Resource Mapping

```python
# File: src/fhir_mapper/fhir_mapper.py

from fhirclient import client
from fhirclient.models import (
    patient, coverage, coverageeligibilityresponse,
    claimresponse, servicerequest, organization
)
from datetime import datetime
import uuid

class FHIRMapper:
    def __init__(self, config):
        self.config = config
        self.base_url = config.get('fhir_server_url', 'http://localhost:8080/fhir')
    
    def entities_to_fhir(self, entities, document_type):
        """
        Convert extracted entities to FHIR resources
        Returns dictionary of FHIR resources
        """
        fhir_bundle = {
            'resourceType': 'Bundle',
            'type': 'transaction',
            'entry': []
        }
        
        # Create Patient resource
        if 'patient_info' in entities:
            patient_resource = self._create_patient(entities['patient_info'])
            fhir_bundle['entry'].append({
                'resource': patient_resource,
                'request': {
                    'method': 'POST',
                    'url': 'Patient'
                }
            })
        
        # Create Organization (Payer) resource
        if 'payer_info' in entities:
            payer_resource = self._create_organization(entities['payer_info'])
            fhir_bundle['entry'].append({
                'resource': payer_resource,
                'request': {
                    'method': 'POST',
                    'url': 'Organization'
                }
            })
        
        # Create document-type-specific resources
        if document_type == 'prior_authorization':
            pa_resource = self._create_prior_auth(entities)
            fhir_bundle['entry'].append({
                'resource': pa_resource,
                'request': {
                    'method': 'POST',
                    'url': 'ServiceRequest'
                }
            })
        
        elif document_type == 'eligibility_verification':
            eligibility_resource = self._create_eligibility_response(entities)
            fhir_bundle['entry'].append({
                'resource': eligibility_resource,
                'request': {
                    'method': 'POST',
                    'url': 'CoverageEligibilityResponse'
                }
            })
        
        elif document_type == 'claim_form':
            claim_resource = self._create_claim_response(entities)
            fhir_bundle['entry'].append({
                'resource': claim_resource,
                'request': {
                    'method': 'POST',
                    'url': 'ClaimResponse'
                }
            })
        
        return fhir_bundle
    
    def _create_patient(self, patient_info):
        """Create FHIR Patient resource"""
        patient_id = patient_info.get('member_id', str(uuid.uuid4()))
        
        patient_resource = {
            'resourceType': 'Patient',
            'id': patient_id,
            'identifier': [{
                'system': 'http://hospital.example.org',
                'value': patient_info.get('member_id', '')
            }],
            'name': [{
                'use': 'official',
                'text': patient_info.get('name', '')
            }],
            'birthDate': patient_info.get('dob', '')
        }
        
        if 'phone' in patient_info:
            patient_resource['telecom'] = [{
                'system': 'phone',
                'value': patient_info['phone']
            }]
        
        return patient_resource
    
    def _create_organization(self, payer_info):
        """Create FHIR Organization resource for payer"""
        org_id = f"org-{payer_info.get('name', 'unknown').lower().replace(' ', '-')}"
        
        org_resource = {
            'resourceType': 'Organization',
            'id': org_id,
            'identifier': [{
                'system': 'http://hl7.org/fhir/sid/us-npi',
                'value': payer_info.get('payer_id', '')
            }],
            'name': payer_info.get('name', ''),
            'type': [{
                'coding': [{
                    'system': 'http://terminology.hl7.org/CodeSystem/organization-type',
                    'code': 'pay',
                    'display': 'Payer'
                }]
            }]
        }
        
        return org_resource
    
    def _create_prior_auth(self, entities):
        """Create FHIR ServiceRequest for Prior Authorization"""
        auth_id = entities.get('authorization_info', {}).get('auth_number', str(uuid.uuid4()))
        
        service_request = {
            'resourceType': 'ServiceRequest',
            'id': auth_id,
            'status': 'active',
            'intent': 'order',
            'category': [{
                'coding': [{
                    'system': 'http://snomed.info/sct',
                    'code': '386053000',
                    'display': 'Evaluation procedure'
                }]
            }],
            'subject': {
                'reference': f"Patient/{entities.get('patient_info', {}).get('member_id', '')}"
            },
            'occurrenceDateTime': entities.get('dates', {}).get('extracted_dates', [''])[0],
            'authoredOn': datetime.now().isoformat()
        }
        
        # Add diagnosis codes
        if 'clinical_info' in entities and 'diagnosis_codes' in entities['clinical_info']:
            service_request['reasonCode'] = [{
                'coding': [{
                    'system': 'http://hl7.org/fhir/sid/icd-10',
                    'code': code
                }]
            } for code in entities['clinical_info']['diagnosis_codes']]
        
        # Add medication if present
        if 'clinical_info' in entities and 'medications' in entities['clinical_info']:
            service_request['orderDetail'] = [{
                'text': ', '.join(entities['clinical_info']['medications'])
            }]
        
        return service_request
    
    def _create_eligibility_response(self, entities):
        """Create FHIR CoverageEligibilityResponse"""
        response_id = str(uuid.uuid4())
        
        eligibility_response = {
            'resourceType': 'CoverageEligibilityResponse',
            'id': response_id,
            'status': 'active',
            'purpose': ['benefits'],
            'patient': {
                'reference': f"Patient/{entities.get('patient_info', {}).get('member_id', '')}"
            },
            'created': datetime.now().isoformat(),
            'insurer': {
                'reference': f"Organization/{entities.get('payer_info', {}).get('name', 'unknown').lower().replace(' ', '-')}"
            },
            'outcome': 'complete',
            'insurance': [{
                'coverage': {
                    'reference': f"Coverage/{entities.get('payer_info', {}).get('policy_number', '')}"
                },
                'inforce': True
            }]
        }
        
        return eligibility_response
    
    def _create_claim_response(self, entities):
        """Create FHIR ClaimResponse"""
        response_id = str(uuid.uuid4())
        
        claim_response = {
            'resourceType': 'ClaimResponse',
            'id': response_id,
            'status': 'active',
            'type': {
                'coding': [{
                    'system': 'http://terminology.hl7.org/CodeSystem/claim-type',
                    'code': 'professional'
                }]
            },
            'use': 'claim',
            'patient': {
                'reference': f"Patient/{entities.get('patient_info', {}).get('member_id', '')}"
            },
            'created': datetime.now().isoformat(),
            'insurer': {
                'reference': f"Organization/{entities.get('payer_info', {}).get('name', 'unknown').lower().replace(' ', '-')}"
            },
            'outcome': 'complete'
        }
        
        return claim_response


# Usage Example
if __name__ == '__main__':
    config = {
        'fhir_server_url': 'http://localhost:8080/fhir'
    }
    
    mapper = FHIRMapper(config)
    
    # Example entities from NLP extraction
    entities = {
        'patient_info': {
            'name': 'John Doe',
            'member_id': 'ABC123456',
            'dob': '1980-05-15'
        },
        'payer_info': {
            'name': 'Blue Cross Blue Shield',
            'policy_number': 'BCBS-987654'
        },
        'authorization_info': {
            'auth_number': 'PA20250115A'
        },
        'clinical_info': {
            'diagnosis_codes': ['E11.9'],
            'medications': ['Ozempic']
        },
        'dates': {
            'extracted_dates': ['2025-01-15']
        }
    }
    
    fhir_bundle = mapper.entities_to_fhir(entities, 'prior_authorization')
    print(fhir_bundle)
```

---

## 🔍 Layer 3: Anomaly Detection & Quality Assurance

### 3.1 Multi-Model Anomaly Detection

```python
# File: src/anomaly_detection/detector.py

from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
import numpy as np
import joblib
import torch
import torch.nn as nn

class AutoEncoder(nn.Module):
    """Neural network autoencoder for anomaly detection"""
    def __init__(self, input_dim):
        super(AutoEncoder, self).__init__()
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16)
        )
        
        self.decoder = nn.Sequential(
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, input_dim)
        )
    
    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

class AnomalyDetector:
    def __init__(self, config):
        self.config = config
        self.contamination = config.get('contamination', 0.1)
        
        # Initialize models
        self.isolation_forest = IsolationForest(
            contamination=self.contamination,
            random_state=42
        )
        
        self.one_class_svm = OneClassSVM(
            nu=self.contamination,
            kernel='rbf'
        )
        
        self.scaler = StandardScaler()
        self.autoencoder = None
        self.reconstruction_threshold = None
        
        self.is_trained = False
    
    def train(self, training_data):
        """
        Train anomaly detection models on normal data
        training_data: list of FHIR resources (dictionaries)
        """
        # Convert FHIR resources to feature vectors
        feature_vectors = [self._extract_features(data) for data in training_data]
        X = np.array(feature_vectors)
        
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Isolation Forest
        self.isolation_forest.fit(X_scaled)
        
        # Train One-Class SVM
        self.one_class_svm.fit(X_scaled)
        
        # Train Autoencoder
        input_dim = X_scaled.shape[1]
        self.autoencoder = AutoEncoder(input_dim)
        self._train_autoencoder(X_scaled)
        
        self.is_trained = True
    
    def _train_autoencoder(self, X):
        """Train the autoencoder"""
        X_tensor = torch.FloatTensor(X)
        
        optimizer = torch.optim.Adam(self.autoencoder.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        epochs = 100
        batch_size = 32
        
        for epoch in range(epochs):
            for i in range(0, len(X), batch_size):
                batch = X_tensor[i:i+batch_size]
                
                # Forward pass
                reconstructed = self.autoencoder(batch)
                loss = criterion(reconstructed, batch)
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            
            if (epoch + 1) % 20 == 0:
                print(f'Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}')
        
        # Calculate reconstruction threshold (95th percentile of training errors)
        with torch.no_grad():
            reconstructed = self.autoencoder(X_tensor)
            reconstruction_errors = torch.mean((X_tensor - reconstructed) ** 2, dim=1)
            self.reconstruction_threshold = np.percentile(
                reconstruction_errors.numpy(), 
                95
            )
    
    def detect_anomaly(self, fhir_resource):
        """
        Detect if a FHIR resource is anomalous
        Returns: dict with anomaly scores and flags
        """
        if not self.is_trained:
            raise ValueError("Models must be trained before detection")
        
        # Extract features
        features = self._extract_features(fhir_resource)
        X = np.array([features])
        X_scaled = self.scaler.transform(X)
        
        # Get predictions from each model
        results = {
            'is_anomaly': False,
            'confidence': 0.0,
            'model_scores': {},
            'anomaly_reasons': []
        }
        
        # Isolation Forest prediction
        if_pred = self.isolation_forest.predict(X_scaled)[0]
        if_score = self.isolation_forest.score_samples(X_scaled)[0]
        results['model_scores']['isolation_forest'] = {
            'prediction': int(if_pred),
            'score': float(if_score)
        }
        
        # One-Class SVM prediction
        svm_pred = self.one_class_svm.predict(X_scaled)[0]
        svm_score = self.one_class_svm.score_samples(X_scaled)[0]
        results['model_scores']['one_class_svm'] = {
            'prediction': int(svm_pred),
            'score': float(svm_score)
        }
        
        # Autoencoder prediction
        X_tensor = torch.FloatTensor(X_scaled)
        with torch.no_grad():
            reconstructed = self.autoencoder(X_tensor)
            reconstruction_error = torch.mean((X_tensor - reconstructed) ** 2).item()
        
        ae_pred = 1 if reconstruction_error < self.reconstruction_threshold else -1
        results['model_scores']['autoencoder'] = {
            'prediction': int(ae_pred),
            'reconstruction_error': float(reconstruction_error),
            'threshold': float(self.reconstruction_threshold)
        }
        
        # Combine predictions (voting ensemble)
        predictions = [if_pred, svm_pred, ae_pred]
        anomaly_votes = sum(1 for p in predictions if p == -1)
        
        results['is_anomaly'] = anomaly_votes >= 2  # Majority voting
        results['confidence'] = anomaly_votes / len(predictions)
        
        # Rule-based validation
        rule_issues = self._rule_based_validation(fhir_resource)
        if rule_issues:
            results['is_anomaly'] = True
            results['anomaly_reasons'].extend(rule_issues)
        
        return results
    
    def _extract_features(self, fhir_resource):
        """
        Extract numerical features from FHIR resource
        Returns feature vector as numpy array
        """
        features = []
        
        # Resource type encoding (one-hot)
        resource_types = ['Patient', 'CoverageEligibilityResponse', 'ClaimResponse', 'ServiceRequest']
        resource_type = fhir_resource.get('resourceType', 'Unknown')
        features.extend([1 if rt == resource_type else 0 for rt in resource_types])
        
        # Status encoding
        status_values = ['active', 'completed', 'cancelled', 'draft']
        status = fhir_resource.get('status', 'unknown')
        features.extend([1 if sv == status else 0 for sv in status_values])
        
        # Date recency (days since creation)
        created_date = fhir_resource.get('created') or fhir_resource.get('authoredOn')
        if created_date:
            days_old = (datetime.now() - datetime.fromisoformat(created_date.replace('Z', '+00:00'))).days
            features.append(min(days_old, 365))  # Cap at 1 year
        else:
            features.append(0)
        
        # Number of identifiers
        identifiers = fhir_resource.get('identifier', [])
        features.append(len(identifiers))
        
        # Has reference to patient
        features.append(1 if 'patient' in fhir_resource or 'subject' in fhir_resource else 0)
        
        # Has reference to insurer/payer
        features.append(1 if 'insurer' in fhir_resource else 0)
        
        # Number of diagnosis codes (for ServiceRequest)
        reason_codes = fhir_resource.get('reasonCode', [])
        features.append(len(reason_codes))
        
        # Coverage status (for eligibility)
        if resource_type == 'CoverageEligibilityResponse':
            insurance = fhir_resource.get('insurance', [])
            features.append(len(insurance))
            if insurance:
                features.append(1 if insurance[0].get('inforce', False) else 0)
            else:
                features.append(0)
        else:
            features.extend([0, 0])
        
        return features
    
    def _rule_based_validation(self, fhir_resource):
        """
        Apply business rules to detect anomalies
        Returns list of rule violations
        """
        issues = []
        
        resource_type = fhir_resource.get('resourceType')
        
        # Check required fields
        if not fhir_resource.get('id'):
            issues.append('Missing resource ID')
        
        if not fhir_resource.get('status'):
            issues.append('Missing status field')
        
        # Patient-specific rules
        if resource_type == 'Patient':
            if not fhir_resource.get('identifier'):
                issues.append('Patient missing identifier')
            
            if not fhir_resource.get('name'):
                issues.append('Patient missing name')
        
        # Prior Auth specific rules
        if resource_type == 'ServiceRequest':
            if not fhir_resource.get('subject'):
                issues.append('ServiceRequest missing patient reference')
            
            if not fhir_resource.get('reasonCode'):
                issues.append('ServiceRequest missing diagnosis codes')
        
        # Eligibility specific rules
        if resource_type == 'CoverageEligibilityResponse':
            if not fhir_resource.get('patient'):
                issues.append('EligibilityResponse missing patient reference')
            
            if not fhir_resource.get('insurer'):
                issues.append('EligibilityResponse missing insurer reference')
            
            # Check if coverage is in force
            insurance = fhir_resource.get('insurance', [])
            if insurance and not insurance[0].get('inforce'):
                issues.append('Coverage not in force')
        
        # Date validation
        created = fhir_resource.get('created') or fhir_resource.get('authoredOn')
        if created:
            try:
                created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if created_date > datetime.now():
                    issues.append('Future creation date detected')
            except:
                issues.append('Invalid date format')
        
        return issues
    
    def save_models(self, filepath):
        """Save trained models to disk"""
        models = {
            'isolation_forest': self.isolation_forest,
            'one_class_svm': self.one_class_svm,
            'scaler': self.scaler,
            'autoencoder_state': self.autoencoder.state_dict() if self.autoencoder else None,
            'reconstruction_threshold': self.reconstruction_threshold,
            'config': self.config
        }
        joblib.dump(models, filepath)
    
    def load_models(self, filepath):
        """Load trained models from disk"""
        models = joblib.load(filepath)
        
        self.isolation_forest = models['isolation_forest']
        self.one_class_svm = models['one_class_svm']
        self.scaler = models['scaler']
        self.reconstruction_threshold = models['reconstruction_threshold']
        
        # Reconstruct autoencoder
        if models['autoencoder_state']:
            input_dim = len(self._extract_features({'resourceType': 'Patient'}))
            self.autoencoder = AutoEncoder(input_dim)
            self.autoencoder.load_state_dict(models['autoencoder_state'])
            self.autoencoder.eval()
        
        self.is_trained = True


# Usage Example
if __name__ == '__main__':
    config = {
        'contamination': 0.1
    }
    
    detector = AnomalyDetector(config)
    
    # Training data (normal FHIR resources)
    training_data = [
        # ... list of valid FHIR resources
    ]
    
    detector.train(training_data)
    detector.save_models('models/anomaly_detector.pkl')
    
    # Later, for inference
    test_resource = {
        'resourceType': 'ServiceRequest',
        'id': 'PA123456',
        'status': 'active',
        'subject': {'reference': 'Patient/ABC123'},
        'reasonCode': [{'coding': [{'code': 'E11.9'}]}],
        'created': '2025-01-15T10:00:00Z'
    }
    
    result = detector.detect_anomaly(test_resource)
    print(f"Is Anomaly: {result['is_anomaly']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Reasons: {result['anomaly_reasons']}")
```

---

## 🔄 Complete Pipeline Integration

```python
# File: src/pipeline_orchestrator.py

from src.ai_pipeline.ocr_processor import OCRProcessor
from src.ai_pipeline.document_classifier import DocumentClassifier
from src.ai_pipeline.nlp_extractor import MedicalNLPExtractor
from src.fhir_mapper.fhir_mapper import FHIRMapper
from src.anomaly_detection.detector import AnomalyDetector
from src.privacy_layer.privacy_manager import PrivacyManager
from src.event_middleware.kafka_middleware import KafkaPublisher
import logging

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self, config):
        self.config = config
        
        # Initialize all components
        self.ocr_processor = OCRProcessor(config.get('ocr', {}))
        self.document_classifier = DocumentClassifier()
        self.nlp_extractor = MedicalNLPExtractor(config.get('nlp', {}))
        self.fhir_mapper = FHIRMapper(config.get('fhir', {}))
        self.anomaly_detector = AnomalyDetector(config.get('anomaly_detection', {}))
        self.privacy_manager = PrivacyManager(config.get('privacy', {}))
        self.kafka_publisher = KafkaPublisher(config.get('kafka', {}))
        
        # Load trained models
        model_path = config.get('model_path', 'models/anomaly_detector.pkl')
        try:
            self.anomaly_detector.load_models(model_path)
            logger.info(f"Loaded anomaly detection models from {model_path}")
        except Exception as e:
            logger.warning(f"Could not load models: {e}. Anomaly detection will be limited.")
    
    def process_document_pipeline(self, file_path, patient_id, payer_id, hub_id):
        """
        Complete end-to-end processing pipeline
        
        Args:
            file_path: Path to document (PDF, image, etc.)
            patient_id: Patient identifier
            payer_id: Payer identifier
            hub_id: Hub CRM identifier
        
        Returns:
            dict with processing results
        """
        pipeline_result = {
            'status': 'processing',
            'steps_completed': [],
            'fhir_resources': {},
            'anomalies_detected': [],
            'events_published': []
        }
        
        try:
            # Step 1: OCR Processing
            logger.info(f"Step 1: OCR processing document: {file_path}")
            ocr_result = self.ocr_processor.process_document(file_path)
            pipeline_result['steps_completed'].append('ocr_processing')
            
            # Step 2: Document Classification
            logger.info("Step 2: Classifying document type")
            classification = self.document_classifier.classify(ocr_result['full_text'])
            document_type = classification['document_type']
            logger.info(f"Classified as: {document_type} (confidence: {classification['confidence']:.2f})")
            pipeline_result['document_type'] = document_type
            pipeline_result['classification_confidence'] = classification['confidence']
            pipeline_result['steps_completed'].append('document_classification')
            
            # Step 3: NLP Entity Extraction
            logger.info("Step 3: Extracting entities using NLP")
            layout_structure = ocr_result.get('combined_structure')
            entities = self.nlp_extractor.extract_entities(
                ocr_result['full_text'],
                layout_structure
            )
            logger.info(f"Extracted entities: {list(entities.keys())}")
            pipeline_result['extracted_entities'] = entities
            pipeline_result['steps_completed'].append('entity_extraction')
            
            # Step 4: FHIR Mapping
            logger.info("Step 4: Mapping to FHIR resources")
            fhir_bundle = self.fhir_mapper.entities_to_fhir(entities, document_type)
            pipeline_result['fhir_resources'] = fhir_bundle
            pipeline_result['steps_completed'].append('fhir_mapping')
            
            # Step 5: Anomaly Detection
            logger.info("Step 5: Running anomaly detection")
            anomaly_results = []
            for entry in fhir_bundle['entry']:
                resource = entry['resource']
                anomaly_result = self.anomaly_detector.detect_anomaly(resource)
                
                if anomaly_result['is_anomaly']:
                    logger.warning(f"Anomaly detected in {resource['resourceType']}: {anomaly_result['anomaly_reasons']}")
                    anomaly_results.append({
                        'resource_type': resource['resourceType'],
                        'resource_id': resource.get('id'),
                        'confidence': anomaly_result['confidence'],
                        'reasons': anomaly_result['anomaly_reasons']
                    })
            
            pipeline_result['anomalies_detected'] = anomaly_results
            pipeline_result['steps_completed'].append('anomaly_detection')
            
            # Step 6: Privacy & Consent Check
            logger.info("Step 6: Applying privacy controls")
            consent_result = self.privacy_manager.check_consent(patient_id, payer_id, hub_id)
            
            if not consent_result['has_consent']:
                logger.error("Patient consent not found or expired")
                pipeline_result['status'] = 'failed'
                pipeline_result['error'] = 'Missing patient consent'
                return pipeline_result
            
            # Redact PHI if needed
            fhir_bundle = self.privacy_manager.apply_minimum_necessary(
                fhir_bundle,
                purpose='hub_case_management'
            )
            pipeline_result['steps_completed'].append('privacy_controls')
            
            # Step 7: Publish Events
            logger.info("Step 7: Publishing events to Kafka")
            
            # Determine if we should publish or route to human review
            if len(anomaly_results) > 0 and classification['confidence'] < 0.8:
                # Route to human review queue
                event = {
                    'event_type': 'document.needs_review',
                    'document_path': file_path,
                    'patient_id': patient_id,
                    'payer_id': payer_id,
                    'hub_id': hub_id,
                    'anomalies': anomaly_results,
                    'fhir_bundle': fhir_bundle
                }
                topic = 'payer-hub.review-queue'
                logger.info("Routing to human review due to anomalies")
            else:
                # Publish to normal processing
                event = {
                    'event_type': f'payer.{document_type}.processed',
                    'patient_id': patient_id,
                    'payer_id': payer_id,
                    'hub_id': hub_id,
                    'fhir_bundle': fhir_bundle
                }
                topic = f'payer-hub.{document_type}.updates'
            
            self.kafka_publisher.publish(topic, event)
            pipeline_result['events_published'].append({
                'topic': topic,
                'event_type': event['event_type']
            })
            pipeline_result['steps_completed'].append('event_publishing')
            
            # Success!
            pipeline_result['status'] = 'completed'
            logger.info(f"Pipeline completed successfully for {file_path}")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
            pipeline_result['status'] = 'failed'
            pipeline_result['error'] = str(e)
        
        return pipeline_result


# Usage Example
if __name__ == '__main__':
    config = {
        'ocr': {'use_layout_model': True},
        'nlp': {'use_biobert': True},
        'kafka': {'bootstrap_servers': ['localhost:9092']},
        'model_path': 'models/anomaly_detector.pkl'
    }
    
    orchestrator = PipelineOrchestrator(config)
    
    result = orchestrator.process_document_pipeline(
        file_path='/path/to/prior_auth_form.pdf',
        patient_id='patient-123',
        payer_id='bcbs',
        hub_id='hub-456'
    )
    
    print(f"Status: {result['status']}")
    print(f"Steps: {result['steps_completed']}")
    print(f"FHIR Resources: {list(result['fhir_resources'].keys())}")
```

---

## 📊 Performance Metrics & Monitoring

### Key Metrics to Track:

1. **OCR Accuracy**
   - Character Error Rate (CER)
   - Word Error Rate (WER)
   - Layout detection accuracy

2. **NLP Extraction Quality**
   - Entity extraction F1 score
   - Named Entity Recognition precision/recall
   - FHIR mapping completeness

3. **Anomaly Detection**
   - False positive rate
   - False negative rate
   - Human review queue size

4. **End-to-End Metrics**
   - Processing time per document
   - Throughput (documents/hour)
   - Success rate
   - Human intervention rate

---

## 🎓 Training & Continuous Improvement

### Human-in-the-Loop (HITL) Feedback Loop

```python
# File: src/feedback/hitl_trainer.py

class HITLTrainer:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.feedback_queue = []
    
    def collect_feedback(self, document_id, corrections):
        """
        Collect human corrections for model improvement
        
        Args:
            document_id: Unique document identifier
            corrections: Dictionary of corrections made by human reviewer
        """
        self.feedback_queue.append({
            'document_id': document_id,
            'corrections': corrections,
            'timestamp': datetime.now()
        })
    
    def retrain_models(self):
        """Periodically retrain models using collected feedback"""
        if len(self.feedback_queue) < 100:
            logger.info("Not enough feedback samples for retraining")
            return
        
        # Extract corrected FHIR resources
        corrected_resources = [
            fb['corrections']['fhir_resource'] 
            for fb in self.feedback_queue
        ]
        
        # Retrain anomaly detector
        logger.info("Retraining anomaly detection models...")
        self.orchestrator.anomaly_detector.train(corrected_resources)
        
        # Save updated models
        self.orchestrator.anomaly_detector.save_models(
            'models/anomaly_detector_retrained.pkl'
        )
        
        # Clear feedback queue
        self.feedback_queue = []
        logger.info("Model retraining complete")
```

---

## 🚀 Deployment Considerations

### 1. Scalability

- **Horizontal Scaling**: Deploy multiple pipeline workers
- **Load Balancing**: Use message queues (Kafka) for work distribution
- **Caching**: Cache trained models in memory using Redis

### 2. Security

- **Encryption**: All PHI encrypted at rest and in transit
- **Access Control**: OAuth 2.0 + RBAC
- **Audit Logging**: Track all data access
- **HIPAA Compliance**: Regular security audits

### 3. Model Versioning

```yaml
# config/model_versions.yaml
models:
  ocr:
    layoutlm_version: "microsoft/layoutlmv3-base"
    tesseract_version: "5.0"
  
  nlp:
    biobert_version: "dmis-lab/biobert-base-cased-v1.2"
    clinical_bert_version: "emilyalsentzer/Bio_ClinicalBERT"
  
  anomaly_detection:
    model_path: "models/anomaly_detector_v2.pkl"
    training_date: "2025-01-15"
    performance_metrics:
      precision: 0.92
      recall: 0.88
      f1_score: 0.90
```

---

## 📈 Results & Impact

### Expected Outcomes:

1. **Automation Rate**: 70-80% of documents processed without human intervention
2. **Processing Time**: Reduced from 15-30 minutes (manual) to 2-5 minutes (automated)
3. **Accuracy**: 90%+ extraction accuracy on structured fields
4. **Cost Savings**: 50-60% reduction in manual data entry labor
5. **Turnaround Time**: Real-time updates vs. 1-2 day delays

---

## 🎯 Next Steps

1. **Pilot Testing**: Start with one payer and one document type
2. **Model Fine-Tuning**: Collect domain-specific training data
3. **Integration Testing**: Test with actual Hub CRM systems
4. **Scale Gradually**: Expand to additional payers and document types
5. **Monitor & Iterate**: Continuous monitoring and model improvements

---

## 📚 References

- **LayoutLMv3**: [Microsoft LayoutLMv3 Paper](https://arxiv.org/abs/2204.08387)
- **BioBERT**: [BioBERT: A Pre-trained Biomedical Language Representation Model](https://arxiv.org/abs/1901.08746)
- **FHIR R4**: [HL7 FHIR Release 4](https://hl7.org/fhir/R4/)
- **Anomaly Detection**: [Isolation Forest Algorithm](https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08b.pdf)

---

**Document Version**: 1.0  
**Last Updated**: October 26, 2025  
**Authors**: Ajit Sahu & Sanjoy Kumar (PayerHub Integration Team)
