from src.connectors.payers.aetna_connector import AetnaConnector

config = {
    'payer_id': 'aetna',
    'base_url': 'https://api.aetna.com',
    'api_key': 'your_api_key',
    'client_id': 'your_client_id'
}

aetna = AetnaConnector(config)
result = aetna.check_eligibility('MEMBER123')