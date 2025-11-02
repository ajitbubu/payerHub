from src.connectors.base_connector import BasePayerConnector, BaseHubConnector

class BasePayerConnector(ABC):
    # Methods all payer connectors must implement:
    - authenticate()
    - check_eligibility()
    - get_prior_authorization_status()
    - submit_prior_authorization()
    - get_claim_status()
    - submit_appeal()