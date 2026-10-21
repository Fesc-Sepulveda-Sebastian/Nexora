from fastapi import APIRouter, Request, Header, HTTPException, status
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks e Integraciones Externas"])

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    """
    RN-06 & RF-22: Webhook contract placeholder for future Stripe Connect integration.
    Does not hold custody of funds in MVP.
    """
    payload = await request.body()
    logger.info(f"Received simulated Stripe Connect webhook event. Payload size: {len(payload)} bytes")
    
    # Contract response acknowledging event receipt
    return {
        "received": True,
        "event_type": "account.updated or payment_intent.succeeded",
        "contract_status": "READY_FOR_PHASE_2_STRIPE_CONNECT"
    }
