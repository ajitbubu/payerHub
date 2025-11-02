"""
Anomaly Detection for Payer Data Quality
Detects inconsistencies, missing fields, and data quality issues
Uses Isolation Forest, Autoencoders, and rule-based validation
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Anomaly detection result"""
    is_anomaly: bool
    anomaly_score: float
    anomaly_type: str
    issues: List[Dict[str, Any]]
    confidence: float
    details: Dict[str, Any]


class Autoencoder(nn.Module):
    """
    Autoencoder neural network for anomaly detection
    Learns normal data patterns and flags deviations
    """
    
    def __init__(self, input_dim: int, encoding_dim: int = 32):
        super(Autoencoder, self).__init__()
        
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, encoding_dim),
            nn.ReLU()
        )
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(encoding_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, input_dim),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded


class DataQualityDetector:
    """
    Comprehensive data quality and anomaly detection
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.device = torch.device('cuda' if config.get('use_gpu', False) else 'cpu')
        
        # Initialize models
        self.isolation_forest = None
        self.one_class_svm = None
        self.autoencoder = None
        self.scaler = StandardScaler()
        
        # Thresholds
        self.anomaly_threshold = config.get('anomaly_threshold', 0.5)
        self.reconstruction_threshold = config.get('reconstruction_threshold', 0.1)
        
        # Required fields for different document types
        self.required_fields = self._define_required_fields()
        
        # Validation rules
        self.validation_rules = self._define_validation_rules()
        
        logger.info("Anomaly Detector initialized")
    
    def _define_required_fields(self) -> Dict[str, List[str]]:
        """Define required fields for each document type"""
        return {
            'PRIOR_AUTHORIZATION': [
                'patient_id', 'patient_name', 'insurance_id', 
                'auth_number', 'diagnosis', 'medication',
                'approval_date', 'expiry_date'
            ],
            'ELIGIBILITY_VERIFICATION': [
                'patient_id', 'insurance_id', 'payer_name',
                'coverage_status', 'effective_date'
            ],
            'EXPLANATION_OF_BENEFITS': [
                'patient_id', 'claim_number', 'service_date',
                'billed_amount', 'allowed_amount', 'payment_status'
            ],
            'CLAIM': [
                'patient_id', 'claim_number', 'service_date',
                'diagnosis_codes', 'procedure_codes', 'billed_amount'
            ]
        }
    
    def _define_validation_rules(self) -> Dict[str, Any]:
        """Define validation rules"""
        return {
            'patient_id': {
                'type': 'string',
                'min_length': 5,
                'max_length': 20,
                'pattern': r'^[A-Z0-9\-]+$'
            },
            'insurance_id': {
                'type': 'string',
                'min_length': 6,
                'max_length': 25
            },
            'dates': {
                'type': 'date',
                'format': ['MM/DD/YYYY', 'YYYY-MM-DD']
            },
            'amounts': {
                'type': 'numeric',
                'min_value': 0,
                'max_value': 1000000
            },
            'icd_codes': {
                'type': 'list',
                'pattern': r'^[A-Z]\d{2}\.?\d*$'
            },
            'cpt_codes': {
                'type': 'list',
                'pattern': r'^\d{5}$'
            }
        }
    
    def train_isolation_forest(self, training_data: pd.DataFrame):
        """
        Train Isolation Forest model on normal data
        """
        logger.info("Training Isolation Forest")
        
        # Prepare features
        X = self._prepare_features(training_data)
        
        # Scale data
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.isolation_forest = IsolationForest(
            contamination=self.config.get('contamination', 0.1),
            random_state=42,
            n_estimators=100
        )
        self.isolation_forest.fit(X_scaled)
        
        logger.info("Isolation Forest training complete")
    
    def train_one_class_svm(self, training_data: pd.DataFrame):
        """
        Train One-Class SVM for anomaly detection
        """
        logger.info("Training One-Class SVM")
        
        X = self._prepare_features(training_data)
        X_scaled = self.scaler.fit_transform(X)
        
        self.one_class_svm = OneClassSVM(
            kernel='rbf',
            gamma='auto',
            nu=self.config.get('nu', 0.1)
        )
        self.one_class_svm.fit(X_scaled)
        
        logger.info("One-Class SVM training complete")
    
    def train_autoencoder(
        self, 
        training_data: pd.DataFrame, 
        epochs: int = 50
    ):
        """
        Train autoencoder for anomaly detection
        """
        logger.info("Training Autoencoder")
        
        X = self._prepare_features(training_data)
        X_scaled = self.scaler.fit_transform(X)
        
        input_dim = X_scaled.shape[1]
        self.autoencoder = Autoencoder(input_dim).to(self.device)
        
        # Training setup
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.autoencoder.parameters(), lr=0.001)
        
        # Convert to tensor
        X_tensor = torch.FloatTensor(X_scaled).to(self.device)
        
        # Training loop
        for epoch in range(epochs):
            self.autoencoder.train()
            
            # Forward pass
            reconstructed = self.autoencoder(X_tensor)
            loss = criterion(reconstructed, X_tensor)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}")
        
        logger.info("Autoencoder training complete")
    
    def _prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """
        Convert data to feature vectors for ML models
        """
        # Extract numeric and categorical features
        features = []
        
        for idx, row in data.iterrows():
            feature_vector = []
            
            # Add numeric features
            if 'confidence' in row:
                feature_vector.append(row['confidence'])
            
            # Add field completeness ratio
            required_fields = self.required_fields.get(row.get('document_type', 'UNKNOWN'), [])
            if required_fields:
                present_fields = sum(1 for field in required_fields if field in row and row[field])
                completeness = present_fields / len(required_fields)
                feature_vector.append(completeness)
            else:
                feature_vector.append(0.5)
            
            # Add text length features
            if 'text' in row:
                feature_vector.append(len(str(row['text'])))
            
            # Add entity count
            if 'entities' in row:
                feature_vector.append(len(row['entities']) if isinstance(row['entities'], list) else 0)
            
            # One-hot encode document type
            doc_types = ['PRIOR_AUTHORIZATION', 'ELIGIBILITY_VERIFICATION', 
                        'EXPLANATION_OF_BENEFITS', 'CLAIM', 'UNKNOWN']
            doc_type = row.get('document_type', 'UNKNOWN')
            feature_vector.extend([1 if dt == doc_type else 0 for dt in doc_types])
            
            features.append(feature_vector)
        
        return np.array(features)
    
    def detect_missing_fields(
        self, 
        data: Dict[str, Any], 
        document_type: str
    ) -> List[Dict[str, Any]]:
        """
        Detect missing required fields
        """
        issues = []
        required_fields = self.required_fields.get(document_type, [])
        
        for field in required_fields:
            if field not in data or not data[field]:
                issues.append({
                    'type': 'MISSING_FIELD',
                    'field': field,
                    'severity': 'HIGH',
                    'message': f"Required field '{field}' is missing"
                })
        
        return issues
    
    def detect_format_violations(
        self, 
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect format and validation rule violations
        """
        issues = []
        
        for field, value in data.items():
            if field in self.validation_rules:
                rule = self.validation_rules[field]
                
                # Type check
                if rule['type'] == 'string' and not isinstance(value, str):
                    issues.append({
                        'type': 'TYPE_MISMATCH',
                        'field': field,
                        'severity': 'MEDIUM',
                        'message': f"Field '{field}' should be string"
                    })
                
                # Length check
                if isinstance(value, str):
                    if 'min_length' in rule and len(value) < rule['min_length']:
                        issues.append({
                            'type': 'INVALID_LENGTH',
                            'field': field,
                            'severity': 'MEDIUM',
                            'message': f"Field '{field}' is too short"
                        })
                    
                    if 'max_length' in rule and len(value) > rule['max_length']:
                        issues.append({
                            'type': 'INVALID_LENGTH',
                            'field': field,
                            'severity': 'MEDIUM',
                            'message': f"Field '{field}' is too long"
                        })
                
                # Numeric range check
                if rule['type'] == 'numeric' and isinstance(value, (int, float)):
                    if 'min_value' in rule and value < rule['min_value']:
                        issues.append({
                            'type': 'OUT_OF_RANGE',
                            'field': field,
                            'severity': 'HIGH',
                            'message': f"Field '{field}' value is below minimum"
                        })
                    
                    if 'max_value' in rule and value > rule['max_value']:
                        issues.append({
                            'type': 'OUT_OF_RANGE',
                            'field': field,
                            'severity': 'HIGH',
                            'message': f"Field '{field}' value exceeds maximum"
                        })
        
        return issues
    
    def detect_cross_field_anomalies(
        self, 
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect cross-field inconsistencies
        """
        issues = []
        
        # Check date consistency
        if 'approval_date' in data and 'expiry_date' in data:
            # In a real implementation, parse and compare dates
            # For now, just check they exist
            pass
        
        # Check amount consistency
        if 'billed_amount' in data and 'allowed_amount' in data:
            try:
                billed = float(data['billed_amount'])
                allowed = float(data['allowed_amount'])
                
                if allowed > billed:
                    issues.append({
                        'type': 'INCONSISTENT_AMOUNTS',
                        'fields': ['billed_amount', 'allowed_amount'],
                        'severity': 'HIGH',
                        'message': 'Allowed amount exceeds billed amount'
                    })
            except (ValueError, TypeError):
                pass
        
        # Check patient-insurance consistency
        if 'patient_id' in data and 'insurance_id' in data:
            # In real implementation, check against database
            pass
        
        return issues
    
    def detect_ml_anomalies(self, data: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Use ML models to detect anomalies
        """
        # Prepare data
        df = pd.DataFrame([data])
        X = self._prepare_features(df)
        X_scaled = self.scaler.transform(X)
        
        anomaly_scores = []
        
        # Isolation Forest
        if self.isolation_forest:
            if_pred = self.isolation_forest.predict(X_scaled)[0]
            if_score = self.isolation_forest.score_samples(X_scaled)[0]
            anomaly_scores.append((if_pred == -1, abs(if_score)))
        
        # One-Class SVM
        if self.one_class_svm:
            svm_pred = self.one_class_svm.predict(X_scaled)[0]
            anomaly_scores.append((svm_pred == -1, 0.5))
        
        # Autoencoder
        if self.autoencoder:
            X_tensor = torch.FloatTensor(X_scaled).to(self.device)
            with torch.no_grad():
                reconstructed = self.autoencoder(X_tensor)
                reconstruction_error = torch.mean((X_tensor - reconstructed) ** 2).item()
            
            is_anomaly = reconstruction_error > self.reconstruction_threshold
            anomaly_scores.append((is_anomaly, reconstruction_error))
        
        # Aggregate scores
        if anomaly_scores:
            is_anomalies = [score[0] for score in anomaly_scores]
            scores = [score[1] for score in anomaly_scores]
            
            # Majority vote
            is_anomaly = sum(is_anomalies) > len(is_anomalies) / 2
            avg_score = np.mean(scores)
            
            return is_anomaly, avg_score
        
        return False, 0.0
    
    def detect(self, data: Dict[str, Any]) -> AnomalyResult:
        """
        Perform complete anomaly detection
        """
        logger.info("Performing anomaly detection")
        
        document_type = data.get('document_type', 'UNKNOWN')
        issues = []
        
        # Rule-based detection
        missing_fields = self.detect_missing_fields(data, document_type)
        format_violations = self.detect_format_violations(data)
        cross_field_anomalies = self.detect_cross_field_anomalies(data)
        
        issues.extend(missing_fields)
        issues.extend(format_violations)
        issues.extend(cross_field_anomalies)
        
        # ML-based detection
        ml_is_anomaly, ml_score = self.detect_ml_anomalies(data)
        
        # Determine overall anomaly status
        high_severity_count = sum(1 for issue in issues if issue['severity'] == 'HIGH')
        rule_based_anomaly = high_severity_count > 0
        
        is_anomaly = rule_based_anomaly or ml_is_anomaly
        
        # Determine anomaly type
        if missing_fields:
            anomaly_type = 'INCOMPLETE_DATA'
        elif format_violations:
            anomaly_type = 'FORMAT_VIOLATION'
        elif cross_field_anomalies:
            anomaly_type = 'INCONSISTENT_DATA'
        elif ml_is_anomaly:
            anomaly_type = 'ML_DETECTED_ANOMALY'
        else:
            anomaly_type = 'NONE'
        
        # Calculate confidence
        confidence = 1.0 - ml_score if ml_score < 1.0 else 0.0
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            anomaly_score=ml_score,
            anomaly_type=anomaly_type,
            issues=issues,
            confidence=confidence,
            details={
                'rule_based_issues': len(issues),
                'ml_anomaly_score': ml_score,
                'document_type': document_type,
                'timestamp': datetime.now().isoformat()
            }
        )


# Example usage
if __name__ == "__main__":
    config = {
        'use_gpu': False,
        'anomaly_threshold': 0.5,
        'reconstruction_threshold': 0.1,
        'contamination': 0.1
    }
    
    detector = DataQualityDetector(config)
    
    # Example data
    sample_data = {
        'patient_id': 'PAT123456',
        'insurance_id': 'INS789012',
        'document_type': 'PRIOR_AUTHORIZATION',
        'confidence': 0.95,
        'text': 'Prior authorization document...',
        'entities': ['patient', 'insurance', 'medication']
    }
    
    # Detect anomalies
    result = detector.detect(sample_data)
    
    print(f"Is Anomaly: {result.is_anomaly}")
    print(f"Anomaly Type: {result.anomaly_type}")
    print(f"Issues Found: {len(result.issues)}")
    for issue in result.issues:
        print(f"  - {issue['type']}: {issue['message']}")
