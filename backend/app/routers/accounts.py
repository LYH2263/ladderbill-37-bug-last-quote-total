from fastapi import APIRouter, HTTPException

from app.services.billing_service import BillingService

router = APIRouter(tags=["accounts"])


@router.get("/accounts")
def list_accounts():
    with BillingService() as svc:
        return {"items": svc.list_accounts()}


@router.get("/accounts/{account_id}")
def get_account(account_id: int):
    with BillingService() as svc:
        row = svc.get_account(account_id)
        if not row:
            raise HTTPException(404, "account not found")
        readings = svc.readings_for_account(account_id)
        return {"account": row, "readings": readings}


@router.get("/accounts/{account_id}/last-calc")
def get_last_calc(account_id: int):
    with BillingService() as svc:
        summary = svc.get_last_calc(account_id)
        if not summary:
            raise HTTPException(404, "no successful calc yet")
        return summary


@router.delete("/accounts/{account_id}/last-calc")
def clear_last_calc(account_id: int):
    with BillingService() as svc:
        deleted = svc.clear_last_calc(account_id)
        return {"deleted": deleted}
