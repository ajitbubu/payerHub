from src.connectors.payers.bcbs_connector import BCBSConnector

config = {
    'payer_id': 'bcbs',
    'payer_name': 'Blue Cross Blue Shield',
    'base_url': 'https://api.bcbs.com',
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret'
}

bcbs = BCBSConnector(config)
bcbs.authenticate()

# Check eligibility
result = bcbs.check_eligibility('ABC123456')
print(f"Eligible: {result['eligible']}")

# Submit prior authorization
pa_request = {
    'member_id': 'ABC123456',
    'diagnosis_codes': ['E11.9'],
    'procedure_code': '99213',
    'provider_npi': '1234567890',
    'service_date': '2025-02-01'
}

pa_result = bcbs.submit_prior_authorization(pa_request)
print(f"Auth Number: {pa_result['auth_number']}")