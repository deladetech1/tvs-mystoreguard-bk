from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.utils.auth import CustomAuthService, get_org_bus_loc_with_permission, verify_subscription_active
from src.entities.gift_cards.gift_cards_service import GiftCardsService
from src.entities.gift_cards.gift_cards_write_dto import (
    CreateGiftCardControllerWriteDto,
    UpdateGiftCardControllerWriteDto,
    DeleteGiftCardControllerWriteDto,
)
from src.entities.gift_cards.gift_cards_read_dto import (
    CreateGiftCardControllerReadDto,
    UpdateGiftCardControllerReadDto,
    DeleteGiftCardControllerReadDto,
    GetGiftCardControllerReadDto,
    GetGiftCardsControllerReadDto,
    GetGiftCardsStatisticsControllerReadDto,
)
from src.entities.shared.sh_response import Respons
from src.configs.logging import get_logger
from src.utils.logging_utils import LogContext
from trovesuite import AuthService

gift_cards_router = APIRouter(prefix="/gift-cards", tags=["Gift Cards"])
logger = get_logger("gift_cards")


# 1. Create Gift Card
@gift_cards_router.post("/add", response_model=Respons[CreateGiftCardControllerReadDto])
def create_gift_card(
    data: CreateGiftCardControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Create a new gift card"""
    with LogContext(
        "gift_cards",
        "create_gift_card",
        gift_card_code=data.gift_card_code if data.gift_card_code else "auto-generated",
    ):
        logger.info(
            "Processing create gift card request",
            extra={
                "extra_fields": {
                    "endpoint": "/gift-cards/add",
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-gift-cards-create"]
        )

        if not is_authorized:
            logger.warning(
                "Create gift card failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/add",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = GiftCardsService.create_gift_card(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            created_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Gift card created successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/add",
                        "gift_card_id": (
                            service_result.data.id 
                            if service_result.data and hasattr(service_result.data, 'id')
                            else (service_result.data[0].id if isinstance(service_result.data, list) and service_result.data else None)
                        ),
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Gift card creation failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/add",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 2. Update Gift Card
@gift_cards_router.put("/update", response_model=Respons[UpdateGiftCardControllerReadDto])
def update_gift_card(
    data: UpdateGiftCardControllerWriteDto,
    gift_card_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Update a gift card"""
    with LogContext(
        "gift_cards",
        "update_gift_card",
        gift_card_id=gift_card_id,
    ):
        logger.info(
            "Processing update gift card request",
            extra={
                "extra_fields": {
                    "endpoint": "/gift-cards/update",
                    "gift_card_id": gift_card_id,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-gift-cards-update"]
        )

        if not is_authorized:
            logger.warning(
                "Update gift card failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/update",
                        "gift_card_id": gift_card_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = GiftCardsService.update_gift_card(
            data=data,
            gift_card_id=gift_card_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            updated_by=current_user.data[0].user_id,
        )

        if service_result.success:
            logger.info(
                "Gift card updated successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/update",
                        "gift_card_id": gift_card_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Gift card update failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/update",
                        "gift_card_id": gift_card_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 3. Get Gift Card by ID
@gift_cards_router.get("/get", response_model=Respons[GetGiftCardControllerReadDto])
def get_gift_card(
    gift_card_id: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a single gift card by ID"""
    with LogContext(
        "gift_cards",
        "get_gift_card",
        gift_card_id=gift_card_id,
    ):
        logger.info(
            "Processing get gift card request",
            extra={
                "extra_fields": {
                    "endpoint": "/gift-cards/get",
                    "gift_card_id": gift_card_id,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-gift-cards-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get gift card failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/get",
                        "gift_card_id": gift_card_id,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = GiftCardsService.get_gift_card(
            gift_card_id=gift_card_id,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        if service_result.success:
            logger.info(
                "Gift card retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/get",
                        "gift_card_id": gift_card_id,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Gift card retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/get",
                        "gift_card_id": gift_card_id,
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 4. Get Gift Card by Code
@gift_cards_router.get("/get-by-code", response_model=Respons[GetGiftCardControllerReadDto])
def get_gift_card_by_code(
    gift_card_code: str = Query(...),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get a gift card by code"""
    with LogContext(
        "gift_cards",
        "get_gift_card_by_code",
        gift_card_code=gift_card_code,
    ):
        logger.info(
            "Processing get gift card by code request",
            extra={
                "extra_fields": {
                    "endpoint": "/gift-cards/get-by-code",
                    "gift_card_code": gift_card_code,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-gift-cards-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get gift card by code failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/get-by-code",
                        "gift_card_code": gift_card_code,
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = GiftCardsService.get_gift_card_by_code(
            gift_card_code=gift_card_code,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        return service_result


# 5. Get Gift Cards (List)
@gift_cards_router.get("/list", response_model=Respons[GetGiftCardsControllerReadDto])
def get_gift_cards(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, USED, EXPIRED, CANCELLED)"),
    search: Optional[str] = Query(None, description="Search by gift card code or description"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size (max 100)"),
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get list of gift cards with filters and pagination"""
    with LogContext(
        "gift_cards",
        "get_gift_cards",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get gift cards request",
            extra={
                "extra_fields": {
                    "endpoint": "/gift-cards/list",
                    "filters": {
                        "is_active": is_active,
                        "status": status,
                        "search": search,
                        "page": page,
                        "size": size,
                    },
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-gift-cards-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get gift cards failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/list",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = GiftCardsService.get_gift_cards(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            is_active=is_active,
            status=status,
            search=search,
            page=page,
            size=size,
        )

        if service_result.success:
            logger.info(
                "Gift cards retrieved successfully",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/list",
                        "count": len(service_result.data) if service_result.data else 0,
                        "status": "success",
                    }
                },
            )
        else:
            logger.warning(
                f"Gift cards retrieval failed: {service_result.detail}",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/list",
                        "error": service_result.error,
                        "status": "failed",
                    }
                },
            )

        return service_result


# 6. Delete Gift Card
@gift_cards_router.delete("/delete", response_model=Respons[DeleteGiftCardControllerReadDto])
def delete_gift_card(
    data: DeleteGiftCardControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user),
    _subscription_check: dict = Depends(verify_subscription_active),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Delete a gift card"""
    with LogContext(
        "gift_cards",
        "delete_gift_card",
        gift_card_id=data.gift_card_id if hasattr(data, "gift_card_id") else "unknown",
    ):
        logger.info(
            "Processing delete gift card request",
            extra={
                "extra_fields": {
                    "endpoint": "/gift-cards/delete",
                    "gift_card_id": data.gift_card_id,
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-gift-cards-delete"]
        )

        if not is_authorized:
            logger.warning(
                "Delete gift card failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/delete",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = GiftCardsService.delete_gift_card(
            data=data,
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
            deleted_by=current_user.data[0].user_id,
        )

        return service_result


# 7. Get Gift Cards Statistics
@gift_cards_router.get("/statistics", response_model=Respons[GetGiftCardsStatisticsControllerReadDto])
def get_gift_cards_statistics(
    current_user: dict = Depends(CustomAuthService.get_current_user),
    org_bus_loc: dict = Depends(get_org_bus_loc_with_permission),
):
    """Get gift cards statistics"""
    with LogContext(
        "gift_cards",
        "get_gift_cards_statistics",
        tenant_id=current_user.data[0].tenant_id,
    ):
        logger.info(
            "Processing get gift cards statistics request",
            extra={
                "extra_fields": {
                    "endpoint": "/gift-cards/statistics",
                }
            },
        )

        is_authorized = AuthService.has_any_permission(
            user_roles=current_user.data,
            required_permissions=["permission-msg-gift-cards-get"]
        )

        if not is_authorized:
            logger.warning(
                "Get gift cards statistics failed - unauthorized access",
                extra={
                    "extra_fields": {
                        "endpoint": "/gift-cards/statistics",
                        "error": "Unauthorized access",
                        "status": "failed",
                    }
                },
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")

        service_result = GiftCardsService.get_gift_cards_statistics(
            tenant_id=current_user.data[0].tenant_id,
            org_id=org_bus_loc["org_id"],
            bus_id=org_bus_loc["bus_id"],
        )

        return service_result

