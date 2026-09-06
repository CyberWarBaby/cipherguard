import uvicorn
from fastapi import FastAPI, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone

app = FastAPI(
    title="ShipFast Logistics API (Simulated Third-Party Carrier)",
    description="Simulated logistics and dispatch partner for CipherGuard telemetry and policy demonstration.",
    version="1.0.0"
)

# ------------------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------------------
class OrderResponse(BaseModel):
    order_id: str
    status: str
    carrier: str
    tracking_number: str
    estimated_delivery: str
    created_at: str

class CreateOrderRequest(BaseModel):
    customer_id: str = Field(..., example="cust_101")
    destination_city: str = Field(..., example="Abuja")
    items_count: int = Field(default=1, ge=1)

class CustomerAddressResponse(BaseModel):
    customer_id: str
    city: str
    country: str
    postal_code: str
    address_type: str

# ------------------------------------------------------------------------------
# Health Probes
# ------------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "shipfast-api",
        "version": "1.0.0"
    }

@app.get("/ready", tags=["Health"])
def readiness_check():
    return {"ready": True}

# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------
@app.get("/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
def get_order(order_id: str):
    """
    Simulated third-party order tracking lookup.
    """
    clean_id = order_id.strip()
    if not clean_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order ID cannot be empty.")
    
    return OrderResponse(
        order_id=clean_id,
        status="shipped",
        carrier="ShipFast Logistics",
        tracking_number=f"SF-NG-{clean_id.replace('-', '')[:8].upper()}",
        estimated_delivery="2026-09-05",
        created_at=datetime.now(timezone.utc).isoformat()
    )

@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, tags=["Orders"])
def create_order(payload: CreateOrderRequest):
    """
    Simulated order dispatch endpoint.
    """
    generated_id = f"ord_{int(datetime.now(timezone.utc).timestamp())}"
    return OrderResponse(
        order_id=generated_id,
        status="processing",
        carrier="ShipFast Logistics",
        tracking_number=f"SF-NG-{generated_id}",
        estimated_delivery="2026-09-08",
        created_at=datetime.now(timezone.utc).isoformat()
    )

@app.get("/customers/{customer_id}/address", response_model=CustomerAddressResponse, tags=["Customers"])
def get_customer_address(customer_id: str):
    """
    Simulated customer shipping destination lookup. Non-PII synthetic data.
    """
    clean_id = customer_id.strip()
    if not clean_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer ID cannot be empty.")

    return CustomerAddressResponse(
        customer_id=clean_id,
        city="Abuja",
        country="Nigeria",
        postal_code="900001",
        address_type="shipping"
    )

# Simulated restricted admin endpoint to demonstrate policy violations
@app.get("/admin/internal-stats", tags=["Simulated Restricted"])
def get_internal_stats():
    """Restricted administrative endpoint used for testing CipherGuard policy blockers."""
    return {"message": "Simulated ShipFast admin metrics"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
