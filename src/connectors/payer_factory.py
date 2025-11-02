from src.connectors.payer_factory import PayerConnectorFactory

# Initialize with all payer configs
payer_configs = {
    'bcbs': {...},
    'aetna': {...},
    'uhc': {...}
}

factory = PayerConnectorFactory(payer_configs)

# Get any payer connector
bcbs = factory.get_connector('bcbs')
aetna = factory.get_connector('aetna')

# Get all connectors
all_payers = factory.get_all_connectors()

# Verify all credentials
verification = factory.verify_all_credentials()
# Returns: {'bcbs': True, 'aetna': True, 'uhc': True}

# Check if payer is supported
supported = factory.is_payer_supported('bcbs')  # True

# Get list of supported payers
payers = factory.get_supported_payers()
# Returns: ['bcbs', 'aetna', 'uhc']