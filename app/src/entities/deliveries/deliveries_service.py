from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date
from src.entities.deliveries.deliveries_read_dto import (
    CreateDeliveryServiceReadDto,
    UpdateDeliveryServiceReadDto,
    GetDeliveryServiceReadDto,
    GetDeliveriesServiceReadDto,
    DeliveryItemReadBase,
    DeliveryReadBase,
    UpdateDeliveryStatusServiceReadDto,
    DispatchDeliveryServiceReadDto,
    CompleteDeliveryServiceReadDto,
    CancelDeliveryServiceReadDto,
    DeleteDeliveryServiceReadDto,
    GetDeliveriesStatisticsServiceReadDto,
)
from src.entities.deliveries.deliveries_write_dto import (
    CreateDeliveryServiceWriteDto,
    UpdateDeliveryServiceWriteDto,
    UpdateDeliveryStatusServiceWriteDto,
    DispatchDeliveryServiceWriteDto,
    CompleteDeliveryServiceWriteDto,
    CancelDeliveryServiceWriteDto,
    DeleteDeliveryServiceWriteDto,
)
from src.entities.shared.sh_response import Respons, PaginationMeta
from src.entities.shared.sh_service import ActivityLogService
from src.configs.settings import db_settings
from src.configs.database import DatabaseManager
from src.configs.logging import get_logger
from trovesuite.utils import Helper

logger = get_logger("deliveries_service")


class DeliveriesService:
    """Service class for deliveries operations"""

    @staticmethod
    def _round_money(value) -> float:
        """Round money value to 2 decimal places"""
        from decimal import ROUND_HALF_UP
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        return round(float(value), 2)

    @staticmethod
    def _generate_delivery_number(
        cursor,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> str:
        """Generate a systematic delivery number in format DEL-YYYYMMDD-NNN"""
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"DEL-{today}"
        
        cursor.execute(
            f"""SELECT delivery_number 
            FROM {db_settings.MSG_DELIVERIES_TABLE}
            WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
            AND delivery_number LIKE %s
            ORDER BY delivery_number DESC
            LIMIT 1""",
            (tenant_id, org_id, bus_id, loc_id, f"{prefix}-%"),
        )
        last_delivery = cursor.fetchone()
        
        if last_delivery and last_delivery.get('delivery_number'):
            last_number = last_delivery['delivery_number']
            try:
                sequence_str = last_number.split('-')[-1]
                sequence_num = int(sequence_str)
                next_sequence = sequence_num + 1
            except (ValueError, IndexError):
                next_sequence = 1
        else:
            next_sequence = 1
        
        delivery_number = f"{prefix}-{next_sequence:03d}"
        
        max_attempts = 1000
        attempts = 0
        while attempts < max_attempts:
            cursor.execute(
                f"""SELECT id FROM {db_settings.MSG_DELIVERIES_TABLE}
                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                AND delivery_number = %s""",
                (tenant_id, org_id, bus_id, loc_id, delivery_number),
            )
            if not cursor.fetchone():
                return delivery_number
            
            next_sequence += 1
            delivery_number = f"{prefix}-{next_sequence:03d}"
            attempts += 1
        
        import time
        timestamp_suffix = int(time.time() * 1000) % 10000
        delivery_number = f"{prefix}-{timestamp_suffix:04d}"
        
        return delivery_number

    @staticmethod
    def create_delivery(
        data: CreateDeliveryServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        created_by: str
    ) -> Respons[CreateDeliveryServiceReadDto]:
        """Create a new delivery"""
        logger.info(
            f"Processing delivery creation",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "bus_id": bus_id,
                    "loc_id": loc_id,
                    "sale_id": data.sale_id,
                    "items_count": len(data.items),
                    "created_by": created_by,
                }
            },
        )

        cdate = Helper.current_date_time()["cdate"]
        ctime = Helper.current_date_time()["ctime"]
        cdatetime = Helper.current_date_time()["cdatetime"]

        try:
            with DatabaseManager.transaction() as cursor:
                # Validate sale exists
                cursor.execute(
                    f"""SELECT id, sale_number, customer_id, status, fulfillment_status
                    FROM {db_settings.MSG_SALES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id),
                )
                sale = cursor.fetchone()
                if not sale:
                    return Respons(
                        success=False,
                        detail=f"Sale {data.sale_id} not found",
                        error="SALE_NOT_FOUND",
                    )

                # Validate delivery type
                valid_delivery_types = ['INTERNAL', 'THIRD_PARTY', 'CUSTOMER_PICKUP']
                delivery_type = data.delivery_type.upper() if data.delivery_type else None
                if delivery_type not in valid_delivery_types:
                    return Respons(
                        success=False,
                        detail=f"Invalid delivery_type. Must be one of: {', '.join(valid_delivery_types)}",
                        error="INVALID_DELIVERY_TYPE",
                    )

                # Validate driver_id if INTERNAL delivery type
                if delivery_type == 'INTERNAL' and data.driver_id:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, data.driver_id),
                    )
                    if not cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"Driver {data.driver_id} not found",
                            error="DRIVER_NOT_FOUND",
                        )

                # Validate sale items exist and get their details
                sale_item_ids = [item.sale_item_id for item in data.items]
                placeholders = ','.join(['%s'] * len(sale_item_ids))
                cursor.execute(
                    f"""SELECT si.id, si.product_id, si.quantity, si.product_name, p.name as product_name_full
                    FROM {db_settings.MSG_SALES_ITEMS_TABLE} si
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON si.product_id = p.id 
                        AND si.tenant_id = p.tenant_id 
                        AND si.org_id = p.org_id 
                        AND si.bus_id = p.bus_id
                    WHERE si.sale_id = %s AND si.tenant_id = %s AND si.org_id = %s AND si.bus_id = %s AND si.loc_id = %s
                    AND si.id IN ({placeholders})""",
                    (data.sale_id, tenant_id, org_id, bus_id, loc_id, *sale_item_ids),
                )
                sale_items = cursor.fetchall()
                sale_items_dict = {item['id']: item for item in sale_items}

                if len(sale_items) != len(sale_item_ids):
                    return Respons(
                        success=False,
                        detail="One or more sale items not found",
                        error="SALE_ITEMS_NOT_FOUND",
                    )

                # Validate delivered quantities don't exceed remaining ordered quantities
                for item in data.items:
                    sale_item = sale_items_dict.get(item.sale_item_id)
                    if not sale_item:
                        return Respons(
                            success=False,
                            detail=f"Sale item {item.sale_item_id} not found",
                            error="SALE_ITEM_NOT_FOUND",
                        )
                    
                    ordered_qty = float(sale_item.get('quantity', 0))
                    
                    # Get total already delivered quantity for this sale item (from existing deliveries)
                    cursor.execute(
                        f"""SELECT COALESCE(SUM(delivered_qty), 0) as total_delivered
                        FROM {db_settings.MSG_DELIVERY_ITEMS_TABLE}
                        WHERE sale_item_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                        (item.sale_item_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    total_delivered_result = cursor.fetchone()
                    already_delivered_qty = float(total_delivered_result.get('total_delivered', 0)) if total_delivered_result else 0.0
                    
                    # Calculate remaining quantity
                    remaining_qty = ordered_qty - already_delivered_qty
                    
                    # Get product name for better error message
                    product_name = sale_item.get('product_name_full') or sale_item.get('product_name') or 'Unknown Product'
                    
                    # Check if new delivered quantity exceeds remaining quantity
                    if item.delivered_qty > remaining_qty:
                        if already_delivered_qty > 0:
                            return Respons(
                                success=False,
                                detail=f"Cannot deliver {item.delivered_qty} units of '{product_name}'. Only {remaining_qty} units remaining (Ordered: {ordered_qty}, Already delivered: {already_delivered_qty})",
                                error="INVALID_DELIVERED_QUANTITY",
                            )
                        else:
                            return Respons(
                                success=False,
                                detail=f"Cannot deliver {item.delivered_qty} units of '{product_name}'. Ordered quantity is only {ordered_qty} units",
                                error="INVALID_DELIVERED_QUANTITY",
                            )

                # Parse scheduled_date if provided
                scheduled_date = None
                if data.scheduled_date:
                    try:
                        scheduled_date = datetime.strptime(data.scheduled_date, "%Y-%m-%d").date()
                    except ValueError:
                        return Respons(
                            success=False,
                            detail="Invalid scheduled_date format. Expected YYYY-MM-DD",
                            error="INVALID_DATE_FORMAT",
                        )

                # Generate delivery number
                delivery_number = DeliveriesService._generate_delivery_number(
                    cursor, tenant_id, org_id, bus_id, loc_id
                )

                # Generate delivery ID
                delivery_id = Helper.generate_unique_identifier(prefix="del")

                # Validate currency_id if provided
                if data.currency_id:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.CORE_PLATFORM_CURRENCY}
                        WHERE id = %s AND tenant_id = %s AND delete_status = 'NOT_DELETED' AND is_active = true""",
                        (data.currency_id, tenant_id),
                    )
                    if not cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"Currency {data.currency_id} not found or inactive",
                            error="CURRENCY_NOT_FOUND",
                        )

                # Insert delivery
                cursor.execute(
                    f"""INSERT INTO {db_settings.MSG_DELIVERIES_TABLE}
                    (id, tenant_id, org_id, bus_id, loc_id, sale_id, delivery_number,
                     delivery_status, delivery_type, scheduled_date, delivery_fee, currency_id, is_paid,
                     recipient_name, recipient_phone, delivery_address, delivery_notes,
                     driver_id, third_party_name, tracking_number,
                     created_by, cdate, ctime, cdatetime)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *""",
                    (
                        delivery_id, tenant_id, org_id, bus_id, loc_id, data.sale_id, delivery_number,
                        'PENDING', delivery_type, scheduled_date, data.delivery_fee, data.currency_id, data.is_paid,
                        data.recipient_name, data.recipient_phone, data.delivery_address, data.delivery_notes,
                        data.driver_id, data.third_party_name, data.tracking_number,
                        created_by, cdate, ctime, cdatetime
                    ),
                )
                delivery_result = cursor.fetchone()

                if not delivery_result:
                    raise ValueError("Failed to create delivery")

                # Insert delivery items
                delivery_items_list = []
                for item in data.items:
                    sale_item = sale_items_dict[item.sale_item_id]
                    item_id = Helper.generate_unique_identifier(prefix="deli")
                    
                    cursor.execute(
                        f"""INSERT INTO {db_settings.MSG_DELIVERY_ITEMS_TABLE}
                        (id, tenant_id, org_id, bus_id, loc_id, delivery_id, sale_item_id, product_id,
                         ordered_qty, delivered_qty, created_by, cdate, ctime, cdatetime)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *""",
                        (
                            item_id, tenant_id, org_id, bus_id, loc_id, delivery_id,
                            item.sale_item_id, item.product_id, item.ordered_qty, item.delivered_qty,
                            created_by, cdate, ctime, cdatetime
                        ),
                    )
                    delivery_item = cursor.fetchone()
                    delivery_items_list.append(delivery_item)

                # Get customer name
                customer_name = None
                if sale.get('customer_id'):
                    cursor.execute(
                        f"""SELECT fullname FROM {db_settings.MSG_CUSTOMERS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (sale['customer_id'], tenant_id, org_id, bus_id),
                    )
                    customer = cursor.fetchone()
                    customer_name = customer.get('fullname') if customer else None

                # Get driver name if provided
                driver_name = None
                if data.driver_id:
                    cursor.execute(
                        f"""SELECT fullname FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, data.driver_id),
                    )
                    driver = cursor.fetchone()
                    driver_name = driver.get('fullname') if driver else None

                # Get currency info if currency_id is provided
                currency_name = None
                currency_symbol = None
                if data.currency_id:
                    cursor.execute(
                        f"""SELECT name, symbol FROM {db_settings.CORE_PLATFORM_CURRENCY}
                        WHERE id = %s AND tenant_id = %s""",
                        (data.currency_id, tenant_id),
                    )
                    currency = cursor.fetchone()
                    if currency:
                        currency_name = currency.get('name')
                        currency_symbol = currency.get('symbol')

                # Build response
                delivery_dict = dict(delivery_result)
                delivery_dict['sale_number'] = sale.get('sale_number')
                delivery_dict['customer_name'] = customer_name
                delivery_dict['driver_name'] = driver_name
                delivery_dict['currency_name'] = currency_name
                delivery_dict['currency_symbol'] = currency_symbol
                
                # Convert items to DTOs
                items_list = []
                for item in delivery_items_list:
                    item_dict = dict(item)
                    sale_item = sale_items_dict.get(item_dict['sale_item_id'])
                    item_dict['product_name'] = sale_item.get('product_name_full') or sale_item.get('product_name') if sale_item else None
                    items_list.append(DeliveryItemReadBase(**item_dict))
                delivery_dict['items'] = items_list

                delivery_read = CreateDeliveryServiceReadDto(**delivery_dict)

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-deliveries",
                        resource_id=delivery_id,
                        action="create",
                        old_data=None,
                        new_data=delivery_dict,
                        description=f"Delivery {delivery_number} created successfully",
                        performed_by=created_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                logger.info(
                    f"Delivery created successfully: {delivery_id}",
                    extra={
                        "extra_fields": {
                            "delivery_id": delivery_id,
                            "delivery_number": delivery_number,
                        }
                    },
                )

                return Respons(
                    success=True,
                    detail="Delivery created successfully",
                    data=[delivery_read],
                )

        except ValueError as e:
            logger.error(f"Validation error creating delivery: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error creating delivery: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to create delivery: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_delivery(
        delivery_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
    ) -> Respons[GetDeliveryServiceReadDto]:
        """Get a single delivery by ID"""
        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT d.*, s.sale_number, c.fullname as customer_name, u.fullname as driver_name,
                           curr.name as currency_name, curr.symbol as currency_symbol
                    FROM {db_settings.MSG_DELIVERIES_TABLE} d
                    LEFT JOIN {db_settings.MSG_SALES_TABLE} s
                        ON d.sale_id = s.id 
                        AND d.tenant_id = s.tenant_id 
                        AND d.org_id = s.org_id 
                        AND d.bus_id = s.bus_id 
                        AND d.loc_id = s.loc_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c
                        ON s.customer_id = c.id 
                        AND s.tenant_id = c.tenant_id 
                        AND s.org_id = c.org_id 
                        AND s.bus_id = c.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} u
                        ON d.driver_id = u.id 
                        AND d.tenant_id = u.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} curr
                        ON d.currency_id = curr.id 
                        AND d.tenant_id = curr.tenant_id
                    WHERE d.id = %s AND d.tenant_id = %s AND d.org_id = %s AND d.bus_id = %s AND d.loc_id = %s""",
                    (delivery_id, tenant_id, org_id, bus_id, loc_id),
                )
                delivery = cursor.fetchone()

                if not delivery:
                    return Respons(
                        success=False,
                        detail="Delivery not found",
                        error="NOT_FOUND",
                    )

                # Get delivery items
                cursor.execute(
                    f"""SELECT di.*, p.name as product_name
                    FROM {db_settings.MSG_DELIVERY_ITEMS_TABLE} di
                    LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                        ON di.product_id = p.id 
                        AND di.tenant_id = p.tenant_id 
                        AND di.org_id = p.org_id 
                        AND di.bus_id = p.bus_id
                    WHERE di.delivery_id = %s AND di.tenant_id = %s AND di.org_id = %s AND di.bus_id = %s AND di.loc_id = %s
                    ORDER BY di.cdatetime ASC""",
                    (delivery_id, tenant_id, org_id, bus_id, loc_id),
                )
                items = cursor.fetchall()

                delivery_dict = dict(delivery)
                delivery_dict['customer_name'] = delivery_dict.get('customer_name') or None
                delivery_dict['driver_name'] = delivery_dict.get('driver_name') or None
                delivery_dict['currency_name'] = delivery_dict.get('currency_name') or None
                delivery_dict['currency_symbol'] = delivery_dict.get('currency_symbol') or None
                
                # Convert items to DTOs
                items_list = []
                for item in items:
                    item_dict = dict(item)
                    items_list.append(DeliveryItemReadBase(**item_dict))
                delivery_dict['items'] = items_list

                delivery_read = GetDeliveryServiceReadDto(**delivery_dict)

                return Respons(
                    success=True,
                    detail="Delivery retrieved successfully",
                    data=[delivery_read],
                )

        except Exception as e:
            logger.error(f"Error getting delivery: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get delivery: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_deliveries(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        sale_id: Optional[str] = None,
        delivery_status: Optional[str] = None,
        delivery_type: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[GetDeliveriesServiceReadDto]:
        """Get list of deliveries with filters and pagination"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "d.tenant_id = %s",
                    "d.org_id = %s",
                    "d.bus_id = %s",
                    "d.loc_id = %s"
                ]
                params = [tenant_id, org_id, bus_id, loc_id]

                if sale_id:
                    where_conditions.append("d.sale_id = %s")
                    params.append(sale_id)

                if delivery_status:
                    where_conditions.append("d.delivery_status = %s")
                    params.append(delivery_status.upper())

                if delivery_type:
                    where_conditions.append("d.delivery_type = %s")
                    params.append(delivery_type.upper())

                if from_date:
                    where_conditions.append("d.cdate >= %s")
                    params.append(from_date)

                if to_date:
                    where_conditions.append("d.cdate <= %s")
                    params.append(to_date)

                if search:
                    where_conditions.append(
                        "(d.delivery_number ILIKE %s OR d.recipient_name ILIKE %s OR d.recipient_phone ILIKE %s OR d.delivery_address ILIKE %s OR s.sale_number ILIKE %s)"
                    )
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern] * 5)

                where_clause = " AND ".join(where_conditions)

                # Get total count
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM {db_settings.MSG_DELIVERIES_TABLE} d
                    LEFT JOIN {db_settings.MSG_SALES_TABLE} s
                        ON d.sale_id = s.id 
                        AND d.tenant_id = s.tenant_id 
                        AND d.org_id = s.org_id 
                        AND d.bus_id = s.bus_id 
                        AND d.loc_id = s.loc_id
                    WHERE {where_clause}
                """
                cursor.execute(count_query, params)
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                # Get deliveries with pagination
                offset = (page - 1) * size
                query = f"""
                    SELECT d.*, s.sale_number, c.fullname as customer_name, u.fullname as driver_name,
                           curr.name as currency_name, curr.symbol as currency_symbol
                    FROM {db_settings.MSG_DELIVERIES_TABLE} d
                    LEFT JOIN {db_settings.MSG_SALES_TABLE} s
                        ON d.sale_id = s.id 
                        AND d.tenant_id = s.tenant_id 
                        AND d.org_id = s.org_id 
                        AND d.bus_id = s.bus_id 
                        AND d.loc_id = s.loc_id
                    LEFT JOIN {db_settings.MSG_CUSTOMERS_TABLE} c
                        ON s.customer_id = c.id 
                        AND s.tenant_id = c.tenant_id 
                        AND s.org_id = c.org_id 
                        AND s.bus_id = c.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} u
                        ON d.driver_id = u.id 
                        AND d.tenant_id = u.tenant_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_CURRENCY} curr
                        ON d.currency_id = curr.id 
                        AND d.tenant_id = curr.tenant_id
                    WHERE {where_clause}
                    ORDER BY d.cdatetime DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(query, params + [size, offset])
                deliveries = cursor.fetchall()

                # Get items for each delivery
                deliveries_list = []
                for delivery in deliveries:
                    delivery_id = delivery['id']
                    cursor.execute(
                        f"""SELECT di.*, p.name as product_name
                        FROM {db_settings.MSG_DELIVERY_ITEMS_TABLE} di
                        LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                            ON di.product_id = p.id 
                            AND di.tenant_id = p.tenant_id 
                            AND di.org_id = p.org_id 
                            AND di.bus_id = p.bus_id
                        WHERE di.delivery_id = %s AND di.tenant_id = %s AND di.org_id = %s AND di.bus_id = %s AND di.loc_id = %s
                        ORDER BY di.cdatetime ASC""",
                        (delivery_id, tenant_id, org_id, bus_id, loc_id),
                    )
                    items = cursor.fetchall()

                    delivery_dict = dict(delivery)
                    delivery_dict['customer_name'] = delivery_dict.get('customer_name') or None
                    delivery_dict['driver_name'] = delivery_dict.get('driver_name') or None
                    delivery_dict['currency_name'] = delivery_dict.get('currency_name') or None
                    delivery_dict['currency_symbol'] = delivery_dict.get('currency_symbol') or None
                    
                    # Convert items to DTOs
                    items_list = []
                    for item in items:
                        item_dict = dict(item)
                        items_list.append(DeliveryItemReadBase(**item_dict))
                    delivery_dict['items'] = items_list

                    deliveries_list.append(DeliveryReadBase(**delivery_dict))

                deliveries_read = GetDeliveriesServiceReadDto(
                    deliveries=deliveries_list,
                    total=total,
                    page=page,
                    size=size
                )

                return Respons(
                    success=True,
                    detail="Deliveries retrieved successfully",
                    data=[deliveries_read],
                )

        except Exception as e:
            logger.error(f"Error getting deliveries: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get deliveries: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_delivery(
        data: UpdateDeliveryServiceWriteDto,
        delivery_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str
    ) -> Respons[UpdateDeliveryServiceReadDto]:
        """Update a delivery"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Check if delivery exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_DELIVERIES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (delivery_id, tenant_id, org_id, bus_id, loc_id),
                )
                existing_delivery = cursor.fetchone()

                if not existing_delivery:
                    return Respons(
                        success=False,
                        detail="Delivery not found",
                        error="NOT_FOUND",
                    )

                # Build update fields
                update_fields = []
                update_params = []

                if data.delivery_status is not None:
                    valid_statuses = ['PENDING', 'SCHEDULED', 'OUT_FOR_DELIVERY', 'DELIVERED', 'FAILED', 'CANCELLED']
                    if data.delivery_status.upper() not in valid_statuses:
                        return Respons(
                            success=False,
                            detail=f"Invalid delivery_status. Must be one of: {', '.join(valid_statuses)}",
                            error="INVALID_STATUS",
                        )
                    update_fields.append("delivery_status = %s")
                    update_params.append(data.delivery_status.upper())

                if data.delivery_type is not None:
                    valid_types = ['INTERNAL', 'THIRD_PARTY', 'CUSTOMER_PICKUP']
                    if data.delivery_type.upper() not in valid_types:
                        return Respons(
                            success=False,
                            detail=f"Invalid delivery_type. Must be one of: {', '.join(valid_types)}",
                            error="INVALID_DELIVERY_TYPE",
                        )
                    update_fields.append("delivery_type = %s")
                    update_params.append(data.delivery_type.upper())

                if data.scheduled_date is not None:
                    try:
                        scheduled_date = datetime.strptime(data.scheduled_date, "%Y-%m-%d").date()
                        update_fields.append("scheduled_date = %s")
                        update_params.append(scheduled_date)
                    except ValueError:
                        return Respons(
                            success=False,
                            detail="Invalid scheduled_date format. Expected YYYY-MM-DD",
                            error="INVALID_DATE_FORMAT",
                        )

                if data.delivery_fee is not None:
                    update_fields.append("delivery_fee = %s")
                    update_params.append(data.delivery_fee)

                if data.currency_id is not None:
                    if data.currency_id:  # If not empty string
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.CORE_PLATFORM_CURRENCY}
                            WHERE id = %s AND tenant_id = %s AND delete_status = 'NOT_DELETED' AND is_active = true""",
                            (data.currency_id, tenant_id),
                        )
                        if not cursor.fetchone():
                            return Respons(
                                success=False,
                                detail=f"Currency {data.currency_id} not found or inactive",
                                error="CURRENCY_NOT_FOUND",
                            )
                    update_fields.append("currency_id = %s")
                    update_params.append(data.currency_id if data.currency_id else None)

                if data.is_paid is not None:
                    update_fields.append("is_paid = %s")
                    update_params.append(data.is_paid)

                if data.recipient_name is not None:
                    update_fields.append("recipient_name = %s")
                    update_params.append(data.recipient_name)

                if data.recipient_phone is not None:
                    update_fields.append("recipient_phone = %s")
                    update_params.append(data.recipient_phone)

                if data.delivery_address is not None:
                    update_fields.append("delivery_address = %s")
                    update_params.append(data.delivery_address)

                if data.delivery_notes is not None:
                    update_fields.append("delivery_notes = %s")
                    update_params.append(data.delivery_notes)

                if data.driver_id is not None:
                    if data.driver_id:  # If not empty string
                        cursor.execute(
                            f"""SELECT id FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                            WHERE tenant_id = %s AND id = %s""",
                            (tenant_id, data.driver_id),
                        )
                        if not cursor.fetchone():
                            return Respons(
                                success=False,
                                detail=f"Driver {data.driver_id} not found",
                                error="DRIVER_NOT_FOUND",
                            )
                    update_fields.append("driver_id = %s")
                    update_params.append(data.driver_id if data.driver_id else None)

                if data.third_party_name is not None:
                    update_fields.append("third_party_name = %s")
                    update_params.append(data.third_party_name)

                if data.tracking_number is not None:
                    update_fields.append("tracking_number = %s")
                    update_params.append(data.tracking_number)

                if not update_fields:
                    return Respons(
                        success=False,
                        detail="No fields to update",
                        error="NO_UPDATE_FIELDS",
                    )

                # Add updated_by and timestamp
                update_fields.append("updated_by = %s")
                update_params.append(updated_by)

                # Update delivery
                update_params.append(delivery_id)
                update_params.extend([tenant_id, org_id, bus_id, loc_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_DELIVERIES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    update_params,
                )
                delivery_result = cursor.fetchone()

                # Update items if provided
                if data.items is not None:
                    # Validate delivered quantities before deleting existing items
                    # Get sale items for validation (with product name)
                    sale_item_ids = [item.sale_item_id for item in data.items]
                    placeholders = ','.join(['%s'] * len(sale_item_ids))
                    cursor.execute(
                        f"""SELECT si.id, si.quantity, si.product_name, p.name as product_name_full
                        FROM {db_settings.MSG_SALES_ITEMS_TABLE} si
                        LEFT JOIN {db_settings.MSG_PRODUCTS_TABLE} p
                            ON si.product_id = p.id 
                            AND si.tenant_id = p.tenant_id 
                            AND si.org_id = p.org_id 
                            AND si.bus_id = p.bus_id
                        WHERE si.tenant_id = %s AND si.org_id = %s AND si.bus_id = %s AND si.loc_id = %s
                        AND si.id IN ({placeholders})""",
                        (tenant_id, org_id, bus_id, loc_id, *sale_item_ids),
                    )
                    sale_items = cursor.fetchall()
                    sale_items_dict = {item['id']: item for item in sale_items}

                    if len(sale_items) != len(sale_item_ids):
                        return Respons(
                            success=False,
                            detail="One or more sale items not found",
                            error="SALE_ITEMS_NOT_FOUND",
                        )

                    # Validate delivered quantities don't exceed remaining ordered quantities
                    for item in data.items:
                        sale_item = sale_items_dict.get(item.sale_item_id)
                        if not sale_item:
                            return Respons(
                                success=False,
                                detail=f"Sale item {item.sale_item_id} not found",
                                error="SALE_ITEM_NOT_FOUND",
                            )
                        
                        ordered_qty = float(sale_item.get('quantity', 0))
                        
                        # Get total already delivered quantity for this sale item (excluding current delivery)
                        cursor.execute(
                            f"""SELECT COALESCE(SUM(delivered_qty), 0) as total_delivered
                            FROM {db_settings.MSG_DELIVERY_ITEMS_TABLE}
                            WHERE sale_item_id = %s AND delivery_id != %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                            (item.sale_item_id, delivery_id, tenant_id, org_id, bus_id, loc_id),
                        )
                        total_delivered_result = cursor.fetchone()
                        already_delivered_qty = float(total_delivered_result.get('total_delivered', 0)) if total_delivered_result else 0.0
                        
                        # Calculate remaining quantity
                        remaining_qty = ordered_qty - already_delivered_qty
                        
                        # Get product name for better error message
                        product_name = sale_item.get('product_name_full') or sale_item.get('product_name') or 'Unknown Product'
                        
                        # Check if new delivered quantity exceeds remaining quantity
                        if item.delivered_qty > remaining_qty:
                            if already_delivered_qty > 0:
                                return Respons(
                                    success=False,
                                    detail=f"Cannot deliver {item.delivered_qty} units of '{product_name}'. Only {remaining_qty} units remaining (Ordered: {ordered_qty}, Already delivered: {already_delivered_qty})",
                                    error="INVALID_DELIVERED_QUANTITY",
                                )
                            else:
                                return Respons(
                                    success=False,
                                    detail=f"Cannot deliver {item.delivered_qty} units of '{product_name}'. Ordered quantity is only {ordered_qty} units",
                                    error="INVALID_DELIVERED_QUANTITY",
                                )

                    # Delete existing items
                    cursor.execute(
                        f"""DELETE FROM {db_settings.MSG_DELIVERY_ITEMS_TABLE}
                        WHERE delivery_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                        (delivery_id, tenant_id, org_id, bus_id, loc_id),
                    )

                    # Insert new items
                    cdate = Helper.current_date_time()["cdate"]
                    ctime = Helper.current_date_time()["ctime"]
                    cdatetime = Helper.current_date_time()["cdatetime"]

                    for item in data.items:
                        item_id = Helper.generate_unique_identifier(prefix="deli")
                        cursor.execute(
                            f"""INSERT INTO {db_settings.MSG_DELIVERY_ITEMS_TABLE}
                            (id, tenant_id, org_id, bus_id, loc_id, delivery_id, sale_item_id, product_id,
                             ordered_qty, delivered_qty, created_by, cdate, ctime, cdatetime)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                item_id, tenant_id, org_id, bus_id, loc_id, delivery_id,
                                item.sale_item_id, item.product_id, item.ordered_qty, item.delivered_qty,
                                updated_by, cdate, ctime, cdatetime
                            ),
                        )

                # Get updated delivery with joins
                return DeliveriesService.get_delivery(delivery_id, tenant_id, org_id, bus_id, loc_id)

        except Exception as e:
            logger.error(f"Error updating delivery: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update delivery: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def update_delivery_status(
        data: UpdateDeliveryStatusServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str
    ) -> Respons[UpdateDeliveryStatusServiceReadDto]:
        """Update delivery status"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Check if delivery exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_DELIVERIES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.delivery_id, tenant_id, org_id, bus_id, loc_id),
                )
                delivery = cursor.fetchone()

                if not delivery:
                    return Respons(
                        success=False,
                        detail="Delivery not found",
                        error="NOT_FOUND",
                    )

                # Validate status
                valid_statuses = ['PENDING', 'SCHEDULED', 'OUT_FOR_DELIVERY', 'DELIVERED', 'FAILED', 'CANCELLED']
                if data.delivery_status.upper() not in valid_statuses:
                    return Respons(
                        success=False,
                        detail=f"Invalid delivery_status. Must be one of: {', '.join(valid_statuses)}",
                        error="INVALID_STATUS",
                    )

                # Update status
                cursor.execute(
                    f"""UPDATE {db_settings.MSG_DELIVERIES_TABLE}
                    SET delivery_status = %s, updated_by = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    (data.delivery_status.upper(), updated_by, data.delivery_id, tenant_id, org_id, bus_id, loc_id),
                )

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-deliveries",
                        resource_id=data.delivery_id,
                        action="update_status",
                        old_data={"delivery_status": delivery.get('delivery_status')},
                        new_data={"delivery_status": data.delivery_status.upper()},
                        description=f"Delivery status updated to {data.delivery_status.upper()}" + (f": {data.notes}" if data.notes else ""),
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Get updated delivery
                return DeliveriesService.get_delivery(data.delivery_id, tenant_id, org_id, bus_id, loc_id)

        except Exception as e:
            logger.error(f"Error updating delivery status: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update delivery status: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def dispatch_delivery(
        data: DispatchDeliveryServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str
    ) -> Respons[DispatchDeliveryServiceReadDto]:
        """Dispatch a delivery"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Check if delivery exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_DELIVERIES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.delivery_id, tenant_id, org_id, bus_id, loc_id),
                )
                delivery = cursor.fetchone()

                if not delivery:
                    return Respons(
                        success=False,
                        detail="Delivery not found",
                        error="NOT_FOUND",
                    )

                # Validate delivery can be dispatched
                current_status = delivery.get('delivery_status')
                if current_status not in ['PENDING', 'SCHEDULED']:
                    return Respons(
                        success=False,
                        detail=f"Cannot dispatch delivery with status {current_status}. Only PENDING or SCHEDULED deliveries can be dispatched.",
                        error="INVALID_STATUS_TRANSITION",
                    )

                # Validate driver if INTERNAL delivery
                if delivery.get('delivery_type') == 'INTERNAL':
                    if not data.driver_id:
                        return Respons(
                            success=False,
                            detail="Driver ID is required for INTERNAL delivery type",
                            error="DRIVER_REQUIRED",
                        )
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, data.driver_id),
                    )
                    if not cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"Driver {data.driver_id} not found",
                            error="DRIVER_NOT_FOUND",
                        )

                # Update delivery
                update_fields = ["delivery_status = 'OUT_FOR_DELIVERY'", "dispatched_at = NOW()", "updated_by = %s"]
                update_params = [updated_by]

                if data.driver_id:
                    update_fields.append("driver_id = %s")
                    update_params.append(data.driver_id)

                if data.tracking_number:
                    update_fields.append("tracking_number = %s")
                    update_params.append(data.tracking_number)

                if data.notes:
                    # Append notes to existing delivery_notes
                    existing_notes = delivery.get('delivery_notes') or ""
                    new_notes = f"{existing_notes}\n[DISPATCH] {data.notes}" if existing_notes else f"[DISPATCH] {data.notes}"
                    update_fields.append("delivery_notes = %s")
                    update_params.append(new_notes)

                update_params.extend([data.delivery_id, tenant_id, org_id, bus_id, loc_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_DELIVERIES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    update_params,
                )

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-deliveries",
                        resource_id=data.delivery_id,
                        action="dispatch",
                        old_data={"delivery_status": current_status},
                        new_data={"delivery_status": "OUT_FOR_DELIVERY"},
                        description=f"Delivery dispatched" + (f": {data.notes}" if data.notes else ""),
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Get updated delivery
                return DeliveriesService.get_delivery(data.delivery_id, tenant_id, org_id, bus_id, loc_id)

        except Exception as e:
            logger.error(f"Error dispatching delivery: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to dispatch delivery: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def complete_delivery(
        data: CompleteDeliveryServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str
    ) -> Respons[CompleteDeliveryServiceReadDto]:
        """Complete a delivery"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Check if delivery exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_DELIVERIES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.delivery_id, tenant_id, org_id, bus_id, loc_id),
                )
                delivery = cursor.fetchone()

                if not delivery:
                    return Respons(
                        success=False,
                        detail="Delivery not found",
                        error="NOT_FOUND",
                    )

                # Validate delivery can be completed
                current_status = delivery.get('delivery_status')
                if current_status not in ['OUT_FOR_DELIVERY', 'SCHEDULED']:
                    return Respons(
                        success=False,
                        detail=f"Cannot complete delivery with status {current_status}. Only OUT_FOR_DELIVERY or SCHEDULED deliveries can be completed.",
                        error="INVALID_STATUS_TRANSITION",
                    )

                # Update delivery
                update_fields = ["delivery_status = 'DELIVERED'", "delivered_at = NOW()", "updated_by = %s"]
                update_params = [updated_by]

                if data.notes:
                    # Append notes to existing delivery_notes
                    existing_notes = delivery.get('delivery_notes') or ""
                    new_notes = f"{existing_notes}\n[COMPLETED] {data.notes}" if existing_notes else f"[COMPLETED] {data.notes}"
                    update_fields.append("delivery_notes = %s")
                    update_params.append(new_notes)

                update_params.extend([data.delivery_id, tenant_id, org_id, bus_id, loc_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_DELIVERIES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    update_params,
                )

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-deliveries",
                        resource_id=data.delivery_id,
                        action="complete",
                        old_data={"delivery_status": current_status},
                        new_data={"delivery_status": "DELIVERED"},
                        description=f"Delivery completed" + (f": {data.notes}" if data.notes else ""),
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Get updated delivery
                return DeliveriesService.get_delivery(data.delivery_id, tenant_id, org_id, bus_id, loc_id)

        except Exception as e:
            logger.error(f"Error completing delivery: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to complete delivery: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def cancel_delivery(
        data: CancelDeliveryServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        updated_by: str
    ) -> Respons[CancelDeliveryServiceReadDto]:
        """Cancel a delivery"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Check if delivery exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_DELIVERIES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.delivery_id, tenant_id, org_id, bus_id, loc_id),
                )
                delivery = cursor.fetchone()

                if not delivery:
                    return Respons(
                        success=False,
                        detail="Delivery not found",
                        error="NOT_FOUND",
                    )

                # Validate delivery can be cancelled
                current_status = delivery.get('delivery_status')
                if current_status == 'DELIVERED':
                    return Respons(
                        success=False,
                        detail="Cannot cancel a delivery that has already been delivered",
                        error="INVALID_STATUS_TRANSITION",
                    )

                # Update delivery
                update_fields = ["delivery_status = 'CANCELLED'", "updated_by = %s"]
                update_params = [updated_by]

                if data.reason:
                    # Append reason to existing delivery_notes
                    existing_notes = delivery.get('delivery_notes') or ""
                    new_notes = f"{existing_notes}\n[CANCELLED] {data.reason}" if existing_notes else f"[CANCELLED] {data.reason}"
                    update_fields.append("delivery_notes = %s")
                    update_params.append(new_notes)

                update_params.extend([data.delivery_id, tenant_id, org_id, bus_id, loc_id])

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_DELIVERIES_TABLE}
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s
                    RETURNING *""",
                    update_params,
                )

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-deliveries",
                        resource_id=data.delivery_id,
                        action="cancel",
                        old_data={"delivery_status": current_status},
                        new_data={"delivery_status": "CANCELLED"},
                        description=f"Delivery cancelled" + (f": {data.reason}" if data.reason else ""),
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Get updated delivery
                return DeliveriesService.get_delivery(data.delivery_id, tenant_id, org_id, bus_id, loc_id)

        except Exception as e:
            logger.error(f"Error cancelling delivery: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to cancel delivery: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def delete_delivery(
        data: DeleteDeliveryServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        deleted_by: str
    ) -> Respons[DeleteDeliveryServiceReadDto]:
        """Hard delete a delivery"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Check if delivery exists
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_DELIVERIES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.delivery_id, tenant_id, org_id, bus_id, loc_id),
                )
                delivery = cursor.fetchone()

                if not delivery:
                    return Respons(
                        success=False,
                        detail="Delivery not found",
                        error="NOT_FOUND",
                    )

                # Delete delivery items first (CASCADE should handle this, but being explicit)
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_DELIVERY_ITEMS_TABLE}
                    WHERE delivery_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.delivery_id, tenant_id, org_id, bus_id, loc_id),
                )

                # Hard delete delivery
                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_DELIVERIES_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s AND loc_id = %s""",
                    (data.delivery_id, tenant_id, org_id, bus_id, loc_id),
                )

                # Log activity
                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-deliveries",
                        resource_id=data.delivery_id,
                        action="delete",
                        old_data=dict(delivery),
                        new_data=None,
                        description=f"Delivery {delivery.get('delivery_number')} deleted",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        loc_id=loc_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                # Get deleted delivery (before deletion)
                delivery_dict = dict(delivery)
                delivery_read = DeleteDeliveryServiceReadDto(**delivery_dict)

                return Respons(
                    success=True,
                    detail="Delivery deleted successfully",
                    data=[delivery_read],
                )

        except Exception as e:
            logger.error(f"Error deleting delivery: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to delete delivery: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_deliveries_statistics(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        loc_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Respons[GetDeliveriesStatisticsServiceReadDto]:
        """Get delivery statistics"""
        try:
            with DatabaseManager.transaction() as cursor:
                # Build WHERE clause
                where_conditions = [
                    "tenant_id = %s",
                    "org_id = %s",
                    "bus_id = %s",
                    "loc_id = %s"
                ]
                params = [tenant_id, org_id, bus_id, loc_id]

                if from_date:
                    where_conditions.append("cdate >= %s")
                    params.append(from_date)

                if to_date:
                    where_conditions.append("cdate <= %s")
                    params.append(to_date)

                where_clause = " AND ".join(where_conditions)

                # Overall statistics
                cursor.execute(
                    f"""SELECT 
                        COUNT(*) as total_deliveries,
                        COALESCE(SUM(delivery_fee), 0) as total_delivery_fee,
                        COUNT(CASE WHEN delivery_status = 'PENDING' THEN 1 END) as total_pending,
                        COUNT(CASE WHEN delivery_status = 'DELIVERED' THEN 1 END) as total_delivered,
                        COUNT(CASE WHEN delivery_status = 'FAILED' THEN 1 END) as total_failed,
                        COUNT(CASE WHEN delivery_status = 'CANCELLED' THEN 1 END) as total_cancelled,
                        COUNT(CASE WHEN delivery_status = 'OUT_FOR_DELIVERY' THEN 1 END) as total_out_for_delivery
                    FROM {db_settings.MSG_DELIVERIES_TABLE}
                    WHERE {where_clause}""",
                    params,
                )
                overall_stats = cursor.fetchone()

                total_deliveries = overall_stats['total_deliveries'] or 0
                total_delivery_fee = DeliveriesService._round_money(overall_stats['total_delivery_fee'] or 0)
                total_pending = overall_stats['total_pending'] or 0
                total_delivered = overall_stats['total_delivered'] or 0
                total_failed = overall_stats['total_failed'] or 0
                total_cancelled = overall_stats['total_cancelled'] or 0
                total_out_for_delivery = overall_stats['total_out_for_delivery'] or 0
                average_delivery_fee = DeliveriesService._round_money(
                    total_delivery_fee / total_deliveries if total_deliveries > 0 else 0
                )

                statistics = GetDeliveriesStatisticsServiceReadDto(
                    total_deliveries=total_deliveries,
                    total_delivery_fee=total_delivery_fee,
                    total_pending=total_pending,
                    total_delivered=total_delivered,
                    total_failed=total_failed,
                    total_cancelled=total_cancelled,
                    total_out_for_delivery=total_out_for_delivery,
                    average_delivery_fee=average_delivery_fee,
                    from_date=from_date,
                    to_date=to_date
                )

                return Respons(
                    success=True,
                    detail="Delivery statistics retrieved successfully",
                    data=[statistics],
                )

        except Exception as e:
            logger.error(f"Error getting delivery statistics: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get delivery statistics: {str(e)}",
                error="INTERNAL_ERROR",
            )

