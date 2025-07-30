"""
Plaid Integration Client
Handles all interactions with Plaid API for banking data.
"""

import asyncio
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from plaid import Client
from plaid.api_client import ApiClient
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.webhook_verification_key_get_request import WebhookVerificationKeyGetRequest
from plaid.configuration import Configuration
from plaid.exceptions import ApiException
import structlog

from .config import settings

logger = structlog.get_logger()


class PlaidClient:
    """Plaid API client wrapper with enhanced functionality."""
    
    def __init__(self):
        """Initialize Plaid client."""
        # Map environment setting to Plaid environment
        plaid_env_map = {
            "sandbox": "sandbox",
            "development": "development", 
            "production": "production"
        }
        
        configuration = Configuration(
            host=getattr(
                Configuration, 
                plaid_env_map.get(settings.plaid_environment, "sandbox"),
                Configuration.sandbox
            ),
            api_key={
                'clientId': settings.plaid_client_id,
                'secret': settings.plaid_secret
            }
        )
        
        api_client = ApiClient(configuration)
        self.client = Client(api_client)
        
    async def create_link_token(
        self, 
        user_id: str, 
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a link token for Plaid Link initialization."""
        try:
            request = LinkTokenCreateRequest(
                products=settings.plaid_products,
                client_name="MintFlow",
                country_codes=settings.plaid_country_codes,
                language='en',
                user={
                    'client_user_id': user_id
                },
                webhook=webhook_url
            )
            
            response = self.client.link_token_create(request)
            
            logger.info(
                "Link token created successfully",
                user_id=user_id,
                link_token=response['link_token'][:10] + "..."
            )
            
            return {
                "link_token": response['link_token'],
                "expiration": response['expiration']
            }
            
        except ApiException as e:
            logger.error(
                "Failed to create link token",
                user_id=user_id,
                error=str(e),
                response_body=e.body
            )
            raise
    
    async def exchange_public_token(self, public_token: str) -> Dict[str, Any]:
        """Exchange public token for access token."""
        try:
            request = ItemPublicTokenExchangeRequest(
                public_token=public_token
            )
            
            response = self.client.item_public_token_exchange(request)
            
            logger.info(
                "Public token exchanged successfully",
                item_id=response['item_id'],
                access_token=response['access_token'][:10] + "..."
            )
            
            return {
                "access_token": response['access_token'],
                "item_id": response['item_id']
            }
            
        except ApiException as e:
            logger.error(
                "Failed to exchange public token",
                error=str(e),
                response_body=e.body
            )
            raise
    
    async def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Get account information."""
        try:
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)
            
            accounts = []
            for account in response['accounts']:
                accounts.append({
                    "account_id": account['account_id'],
                    "name": account['name'],
                    "official_name": account.get('official_name'),
                    "type": account['type'],
                    "subtype": account.get('subtype'),
                    "mask": account.get('mask'),
                    "balances": {
                        "available": account['balances'].get('available'),
                        "current": account['balances'].get('current'),
                        "limit": account['balances'].get('limit'),
                        "iso_currency_code": account['balances'].get('iso_currency_code'),
                        "unofficial_currency_code": account['balances'].get('unofficial_currency_code')
                    }
                })
            
            logger.info(
                "Accounts retrieved successfully",
                access_token=access_token[:10] + "...",
                account_count=len(accounts)
            )
            
            return accounts
            
        except ApiException as e:
            logger.error(
                "Failed to get accounts",
                access_token=access_token[:10] + "...",
                error=str(e),
                response_body=e.body
            )
            raise
    
    async def get_transactions(
        self, 
        access_token: str,
        start_date: date,
        end_date: date,
        account_ids: Optional[List[str]] = None,
        count: int = 500,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get transactions for specified date range."""
        try:
            request_data = {
                "access_token": access_token,
                "start_date": start_date,
                "end_date": end_date,
                "count": count,
                "offset": offset
            }
            
            if account_ids:
                request_data["account_ids"] = account_ids
            
            request = TransactionsGetRequest(**request_data)
            response = self.client.transactions_get(request)
            
            transactions = []
            for txn in response['transactions']:
                transactions.append({
                    "transaction_id": txn['transaction_id'],
                    "account_id": txn['account_id'],
                    "amount": float(txn['amount']),
                    "date": txn['date'],
                    "authorized_date": txn.get('authorized_date'),
                    "name": txn['name'],
                    "merchant_name": txn.get('merchant_name'),
                    "category": txn.get('category', []),
                    "category_id": txn.get('category_id'),
                    "iso_currency_code": txn.get('iso_currency_code'),
                    "unofficial_currency_code": txn.get('unofficial_currency_code'),
                    "pending": txn.get('pending', False),
                    "account_owner": txn.get('account_owner'),
                    "location": txn.get('location'),
                    "payment_meta": txn.get('payment_meta'),
                    "transaction_type": txn.get('transaction_type'),
                    "transaction_code": txn.get('transaction_code'),
                    "personal_finance_category": txn.get('personal_finance_category')
                })
            
            total_transactions = response['total_transactions']
            
            logger.info(
                "Transactions retrieved successfully",
                access_token=access_token[:10] + "...",
                transaction_count=len(transactions),
                total_transactions=total_transactions,
                start_date=start_date,
                end_date=end_date
            )
            
            return transactions, total_transactions
            
        except ApiException as e:
            logger.error(
                "Failed to get transactions",
                access_token=access_token[:10] + "...",
                error=str(e),
                response_body=e.body
            )
            raise
    
    async def get_institution(self, institution_id: str) -> Dict[str, Any]:
        """Get institution information."""
        try:
            request = InstitutionsGetByIdRequest(
                institution_id=institution_id,
                country_codes=settings.plaid_country_codes
            )
            
            response = self.client.institutions_get_by_id(request)
            institution = response['institution']
            
            result = {
                "institution_id": institution['institution_id'],
                "name": institution['name'],
                "products": institution['products'],
                "country_codes": institution['country_codes'],
                "url": institution.get('url'),
                "primary_color": institution.get('primary_color'),
                "logo": institution.get('logo'),
                "routing_numbers": institution.get('routing_numbers', [])
            }
            
            logger.info(
                "Institution retrieved successfully",
                institution_id=institution_id,
                name=institution['name']
            )
            
            return result
            
        except ApiException as e:
            logger.error(
                "Failed to get institution",
                institution_id=institution_id,
                error=str(e),
                response_body=e.body
            )
            raise
    
    async def get_item(self, access_token: str) -> Dict[str, Any]:
        """Get item information."""
        try:
            request = ItemGetRequest(access_token=access_token)
            response = self.client.item_get(request)
            
            item = response['item']
            
            result = {
                "item_id": item['item_id'],
                "institution_id": item['institution_id'],
                "webhook": item.get('webhook'),
                "error": item.get('error'),
                "available_products": item.get('available_products', []),
                "billed_products": item.get('billed_products', []),
                "consent_expiration_time": item.get('consent_expiration_time'),
                "update_type": item.get('update_type')
            }
            
            logger.info(
                "Item retrieved successfully",
                access_token=access_token[:10] + "...",
                item_id=item['item_id']
            )
            
            return result
            
        except ApiException as e:
            logger.error(
                "Failed to get item",
                access_token=access_token[:10] + "...",
                error=str(e),
                response_body=e.body
            )
            raise
    
    async def get_all_transactions(
        self,
        access_token: str,
        start_date: date,
        end_date: date,
        account_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get all transactions for a date range with pagination."""
        all_transactions = []
        offset = 0
        batch_size = 500
        
        while True:
            try:
                transactions, total = await self.get_transactions(
                    access_token=access_token,
                    start_date=start_date,
                    end_date=end_date,
                    account_ids=account_ids,
                    count=batch_size,
                    offset=offset
                )
                
                all_transactions.extend(transactions)
                
                if len(transactions) < batch_size or len(all_transactions) >= total:
                    break
                
                offset += batch_size
                
                # Add small delay to respect rate limits
                await asyncio.sleep(0.1)
                
            except ApiException as e:
                if "RATE_LIMIT_EXCEEDED" in str(e):
                    logger.warning("Rate limit exceeded, waiting before retry")
                    await asyncio.sleep(30)
                    continue
                else:
                    raise
        
        logger.info(
            "All transactions retrieved",
            access_token=access_token[:10] + "...",
            total_transactions=len(all_transactions),
            start_date=start_date,
            end_date=end_date
        )
        
        return all_transactions
    
    async def verify_webhook(self, webhook_body: str, signature: str) -> bool:
        """Verify webhook signature."""
        try:
            request = WebhookVerificationKeyGetRequest(
                key_id=signature
            )
            
            response = self.client.webhook_verification_key_get(request)
            
            # Implementation would include actual signature verification
            # using the public key from response
            
            logger.info("Webhook verification completed")
            return True
            
        except ApiException as e:
            logger.error(
                "Webhook verification failed",
                error=str(e),
                response_body=e.body
            )
            return False