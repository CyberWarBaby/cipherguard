import uvicorn
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

app = FastAPI(
    title="PayFlex Payments API (Simulated Third-Party Financial Partner)",
    description="Simulated fintech payment processing partner used to verify CipherGuard's multi-vendor generic security architecture.",
    version="1.0.0"
)

# ------------------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------------------
class ChargeRequest(BaseModel):
    amount: float = Field(..., gt=0, example=5000.0)
    currency: str = Field(default="NGN", max_length=3, example="NGN")
    customer_id: str = Field(..., example="cust_982")
    reference: Optional[str] = Field(None, example="ref_trx_1001")

class ChargeResponse(BaseModel):
    payment_id: str
    amount: float
    currency: str
    customer_id: str
    status: str
    channel: str
    reference: str
    authorized_by: str
    created_at: str

# ------------------------------------------------------------------------------
# Health Probes
# ------------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "payflex-api",
        "version": "1.0.0"
    }

@app.get("/ready", tags=["Health"])
def readiness_check():
    return {"ready": True}

# ------------------------------------------------------------------------------
# Payment Endpoints
# ------------------------------------------------------------------------------
@app.post("/payments/charge", response_model=ChargeResponse, status_code=status.HTTP_200_OK, tags=["Payments"])
def charge_payment(payload: ChargeRequest, request: Request):
    """
    Simulated third-party payment processing endpoint.
    Accepts charge request and checks for upstream injected API key if present.
    """
    gen_id = f"pay_{int(datetime.now(timezone.utc).timestamp())}"
    ref = payload.reference or f"ref_{gen_id}"
    
    # Verify whether server-side API Key was injected by CipherGuard
    injected_key = request.headers.get("x-api-key")
    auth_agent = "Authenticated by CipherGuard injected key" if injected_key else "Standard direct charge"

    return ChargeResponse(
        payment_id=gen_id,
        amount=payload.amount,
        currency=payload.currency,
        customer_id=payload.customer_id,
        status="succeeded",
        channel="debit_card",
        reference=ref,
        authorized_by=auth_agent,
        created_at=datetime.now(timezone.utc).isoformat()
    )

@app.get("/payments/{payment_id}", response_model=ChargeResponse, tags=["Payments"])
def get_payment(payment_id: str):
    """
    Simulated lookup of an existing payment transaction.
    """
    clean_id = payment_id.strip()
    if not clean_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment ID cannot be empty.")

    return ChargeResponse(
        payment_id=clean_id,
        amount=5000.0,
        currency="NGN",
        customer_id="cust_982",
        status="succeeded",
        channel="bank_transfer",
        reference=f"ref_{clean_id}",
        authorized_by="PayFlex Core Engine",
        created_at=datetime.now(timezone.utc).isoformat()
    )

# ------------------------------------------------------------------------------
# Simulated Restricted Administrative Endpoints
# ------------------------------------------------------------------------------
@app.get("/admin/vault-keys", tags=["Simulated Restricted"])
def get_vault_keys():
    """
    Restricted payment gateway vault endpoint.
    Used to demonstrate CipherGuard policy blocking on PayFlex.
    """
    return {"keys": ["vault_sec_master_key_991823"]}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
