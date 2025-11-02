from src.connectors.hub_connector import SalesforceHubConnector

config = {
    'hub_id': 'hub-001',
    'hub_name': 'Patient Services Hub',
    'base_url': 'https://login.salesforce.com',
    'instance_url': 'https://yourinstance.salesforce.com',
    'auth_method': 'password',
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret',
    'username': 'your_username',
    'password': 'your_password',
    'security_token': 'your_security_token'
}

hub = SalesforceHubConnector(config)
hub.authenticate()

# Create a case
case_data = {
    'subject': 'Prior Authorization - John Doe',
    'description': 'Automated case from document processing',
    'status': 'New',
    'priority': 'High',
    'type': 'Prior Authorization',
    'patient_id': 'ABC123456',
    'custom_fields': {
        'Payer__c': 'Blue Cross Blue Shield',
        'Member_ID__c': 'ABC123456'
    }
}

result = hub.create_case(case_data)
case_id = result['case_id']

# Update case
hub.update_case(case_id, {'Status': 'In Progress'})

# Add note to case
hub.add_note(case_id, "Eligibility verified with payer", "clinical")

# Upload document
hub.upload_document(case_id, 'prior_auth.pdf', 'prior_authorization')

# Create task
task_data = {
    'subject': 'Follow up with payer',
    'description': 'Check PA status',
    'priority': 'High',
    'due_date': '2025-11-01',
    'assigned_to': 'user_id_here'
}
hub.create_task(case_id, task_data)

# Query cases
cases = hub.query_cases({
    'patient_id': 'ABC123456',
    'status': 'Open',
    'type': 'Prior Authorization'
})