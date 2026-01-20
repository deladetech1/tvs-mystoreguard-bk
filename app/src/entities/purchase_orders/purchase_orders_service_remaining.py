    @staticmethod
    def update_purchase_order(
        data: UpdatePurchaseOrderServiceWriteDto,
        purchase_order_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        updated_by: str
    ) -> Respons[UpdatePurchaseOrderServiceReadDto]:
        """Update a purchase order with optional items (qty_received cannot be updated directly)"""
        logger.info(
            f"Processing purchase order update: {purchase_order_id}",
            extra={
                "extra_fields": {
                    "purchase_order_id": purchase_order_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                existing_po = cursor.fetchone()
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (purchase_order_id, tenant_id, org_id, bus_id),
                )
                existing_po = cursor.fetchone()

                if not existing_po:
                    return Respons(
                        success=False,
                        detail="Purchase order not found",
                        error="NOT_FOUND",
                    )
                
                old_data = dict(existing_po)

                # Verify supplier if being updated
                if data.supplier_id is not None:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.MSG_SUPPLIERS_TABLE}
                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                        AND id = %s AND delete_status = 'NOT_DELETED'""",
                        (tenant_id, org_id, bus_id, data.supplier_id),
                    )
                    if not cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"Supplier {data.supplier_id} not found",
                            error="SUPPLIER_NOT_FOUND",
                        )

                # Verify assign_to user if being updated
                if data.assign_to is not None:
                    cursor.execute(
                        f"""SELECT id FROM {db_settings.CORE_PLATFORM_USERS_TABLE}
                        WHERE tenant_id = %s AND id = %s""",
                        (tenant_id, data.assign_to),
                    )
                    if not cursor.fetchone():
                        return Respons(
                            success=False,
                            detail=f"User {data.assign_to} not found",
                            error="USER_NOT_FOUND",
                        )

                # Build update query dynamically
                update_fields = []
                params = []

                if data.supplier_id is not None:
                    update_fields.append("supplier_id = %s")
                    params.append(data.supplier_id)
                if data.assign_to is not None:
                    update_fields.append("assign_to = %s")
                    params.append(data.assign_to)
                if data.status is not None:
                    update_fields.append("status = %s")
                    params.append(data.status)
                if data.order_date is not None:
                    update_fields.append("order_date = %s")
                    params.append(data.order_date)
                if data.expected_delivery_date is not None:
                    update_fields.append("expected_delivery_date = %s")
                    params.append(data.expected_delivery_date)
                if data.notes is not None:
                    update_fields.append("notes = %s")
                    params.append(data.notes)

                if update_fields:
                    params.extend([purchase_order_id, tenant_id, org_id, bus_id])
                    cursor.execute(
                        f"""UPDATE {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                        SET {', '.join(update_fields)}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        params,
                    )

                # Handle items if provided (qty_received cannot be updated here)
                if data.items is not None and len(data.items) > 0:
                    for item in data.items:
                        if hasattr(item, 'item_id') and item.item_id:
                            # Update existing item
                            cursor.execute(
                                f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                                WHERE id = %s AND tenant_id = %s AND org_id = %s 
                                AND bus_id = %s AND purchase_order_id = %s""",
                                (item.item_id, tenant_id, org_id, bus_id, purchase_order_id),
                            )
                            existing_item = cursor.fetchone()
                            
                            if not existing_item:
                                logger.warning(f"Item {item.item_id} not found, skipping")
                            else:
                                item_update_fields = []
                                item_params = []

                                if item.product_id is not None:
                                    cursor.execute(
                                        f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                                        WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                                        AND id = %s AND delete_status = 'NOT_DELETED'""",
                                        (tenant_id, org_id, bus_id, item.product_id),
                                    )
                                    if not cursor.fetchone():
                                        raise ValueError(f"Product {item.product_id} not found")
                                    item_update_fields.append("product_id = %s")
                                    item_params.append(item.product_id)
                                
                                if item.qty_ordered is not None:
                                    # When updating qty_ordered, recalculate qty_remaining
                                    existing_qty_received = existing_item.get('qty_received', 0)
                                    new_qty_remaining = item.qty_ordered - existing_qty_received
                                    if new_qty_remaining < 0:
                                        raise ValueError(f"qty_ordered ({item.qty_ordered}) cannot be less than qty_received ({existing_qty_received})")
                                    item_update_fields.append("qty_ordered = %s")
                                    item_params.append(item.qty_ordered)
                                    item_update_fields.append("qty_remaining = %s")
                                    item_params.append(new_qty_remaining)
                                
                                if item.currency_id is not None:
                                    cursor.execute(
                                        f"""SELECT id FROM {db_settings.CORE_PLATFORM_CURRENCY}
                                        WHERE tenant_id = %s AND id = %s""",
                                        (tenant_id, item.currency_id),
                                    )
                                    if not cursor.fetchone():
                                        raise ValueError(f"Currency {item.currency_id} not found")
                                    item_update_fields.append("currency_id = %s")
                                    item_params.append(item.currency_id)
                                if item.cost_price is not None:
                                    item_update_fields.append("cost_price = %s")
                                    item_params.append(item.cost_price)
                                if item.base_selling_price is not None:
                                    item_update_fields.append("base_selling_price = %s")
                                    item_params.append(item.base_selling_price)

                                if item_update_fields:
                                    item_params.extend([item.item_id, tenant_id, org_id, bus_id, purchase_order_id])
                                    cursor.execute(
                                        f"""UPDATE {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                                        SET {', '.join(item_update_fields)}
                                        WHERE id = %s AND tenant_id = %s AND org_id = %s 
                                        AND bus_id = %s AND purchase_order_id = %s""",
                                        item_params,
                                    )
                        else:
                            # Create new item
                            if item.product_id:
                                cursor.execute(
                                    f"""SELECT id FROM {db_settings.MSG_PRODUCTS_TABLE}
                                    WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                                    AND id = %s AND delete_status = 'NOT_DELETED'""",
                                    (tenant_id, org_id, bus_id, item.product_id),
                                )
                                if not cursor.fetchone():
                                    raise ValueError(f"Product {item.product_id} not found")

                            if item.currency_id:
                                cursor.execute(
                                    f"""SELECT id FROM {db_settings.CORE_PLATFORM_CURRENCY}
                                    WHERE tenant_id = %s AND id = %s""",
                                    (tenant_id, item.currency_id),
                                )
                                if not cursor.fetchone():
                                    raise ValueError(f"Currency {item.currency_id} not found")

                            cursor.execute(
                                f"""SELECT id FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                                WHERE tenant_id = %s AND org_id = %s AND bus_id = %s 
                                AND purchase_order_id = %s AND product_id = %s""",
                                (tenant_id, org_id, bus_id, purchase_order_id, item.product_id),
                            )
                            if cursor.fetchone():
                                raise ValueError(f"Product {item.product_id} already exists in this purchase order")

                            item_id = Helper.generate_unique_identifier(prefix="poi")
                            qty_received = 0
                            qty_remaining = item.qty_ordered
                            cursor.execute(
                                f"""INSERT INTO {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                                (id, tenant_id, org_id, bus_id, purchase_order_id, product_id,
                                 qty_ordered, qty_received, qty_remaining, currency_id, cost_price, base_selling_price)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING *""",
                                (
                                    item_id, tenant_id, org_id, bus_id, purchase_order_id,
                                    item.product_id, item.qty_ordered,
                                    qty_received, qty_remaining,
                                    item.currency_id, item.cost_price, item.base_selling_price
                                ),
                            )

                # Get updated purchase order
                cursor.execute(
                    f"""SELECT po.*,
                           creator.fullname as created_by,
                           supplier.fullname as supplier_name,
                           assignee.fullname as assign_to_name
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON po.created_by = creator.id AND po.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} supplier ON po.supplier_id = supplier.id 
                        AND po.tenant_id = supplier.tenant_id 
                        AND po.org_id = supplier.org_id 
                        AND po.bus_id = supplier.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assignee ON po.assign_to = assignee.id AND po.tenant_id = assignee.tenant_id
                    WHERE po.id = %s AND po.tenant_id = %s AND po.org_id = %s AND po.bus_id = %s""",
                    (purchase_order_id, tenant_id, org_id, bus_id),
                )
                po_with_users = cursor.fetchone()

                if po_with_users:
                    po_dict = dict(po_with_users)
                    po_dict['created_by'] = po_dict.get('created_by') or None
                    po_dict['supplier_name'] = po_dict.get('supplier_name') or None
                    po_dict['assign_to_name'] = po_dict.get('assign_to_name') or None
                else:
                    po_dict = dict(existing_po)
                    po_dict['created_by'] = None
                    po_dict['supplier_name'] = None
                    po_dict['assign_to_name'] = None

                # Get items and batches
                items_data = PurchaseOrdersService._get_purchase_order_items(
                    cursor, tenant_id, org_id, bus_id, purchase_order_id
                )
                batches_data = PurchaseOrdersService._get_purchase_order_batches(
                    cursor, tenant_id, org_id, bus_id, purchase_order_id
                )
                batches_list = []
                if batches_data:
                    for batch in batches_data:
                        batch_dict = dict(batch)
                        # Set new field names for batch quantities
                        batch_dict['specific_product_per_batch_received_qty'] = batch_dict.get('qty_received', 0)
                        batch_dict['specific_product_per_batch_remaining_qty'] = batch_dict.get('qty_remaining', 0)
                        batches_list.append(PurchaseBatchReadDto(**batch_dict))

                batches_by_product = {}
                for batch in batches_list:
                    product_id = batch.product_id
                    if product_id not in batches_by_product:
                        batches_by_product[product_id] = []
                    batches_by_product[product_id].append(batch)

                items_list = []
                for item in items_data:
                    item_dict = dict(item)
                    product_id = item_dict.get('product_id')
                    item_dict['batches'] = batches_by_product.get(product_id, None)
                    currency_id = item_dict.get('currency_id')
                    if currency_id:
                        currency_dict = {
                            'id': currency_id,
                            'name': item_dict.pop('currency_name', None),
                            'code': item_dict.pop('currency_code', None),
                            'symbol': item_dict.pop('currency_symbol', None),
                            'decimal_places': item_dict.pop('currency_decimal_places', None),
                            'currency_position': item_dict.pop('currency_position', None),
                        }
                        item_dict['currency'] = CurrencyReadDto(**currency_dict)
                    else:
                        item_dict['currency'] = None
                    items_list.append(PurchaseOrderItemReadDto(**item_dict))

                po_read = UpdatePurchaseOrderServiceReadDto(
                    purchase_order=PurchaseOrderReadBase(**po_dict),
                    items=items_list
                )

                # Log activity
                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (purchase_order_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else po_dict
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-purchase-orders",
                        resource_id=purchase_order_id,
                        action="update",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Purchase order {purchase_order_id} updated successfully",
                        performed_by=updated_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                return Respons(
                    success=True,
                    detail="Purchase order updated successfully",
                    data=[po_read],
                )

        except ValueError as e:
            logger.error(f"Validation error updating purchase order: {str(e)}")
            return Respons(
                success=False,
                detail=str(e),
                error="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error updating purchase order: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to update purchase order: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_purchase_order(
        purchase_order_id: str,
        tenant_id: str,
        org_id: str,
        bus_id: str,
    ) -> Respons[GetPurchaseOrderServiceReadDto]:
        """Get a single purchase order by ID"""
        logger.info(
            f"Processing get purchase order request: {purchase_order_id}",
            extra={
                "extra_fields": {
                    "purchase_order_id": purchase_order_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT po.*,
                           creator.fullname as created_by,
                           supplier.fullname as supplier_name,
                           assignee.fullname as assign_to_name
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON po.created_by = creator.id AND po.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} supplier ON po.supplier_id = supplier.id 
                        AND po.tenant_id = supplier.tenant_id 
                        AND po.org_id = supplier.org_id 
                        AND po.bus_id = supplier.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assignee ON po.assign_to = assignee.id AND po.tenant_id = assignee.tenant_id
                    WHERE po.id = %s AND po.tenant_id = %s AND po.org_id = %s AND po.bus_id = %s""",
                    (purchase_order_id, tenant_id, org_id, bus_id),
                )
                po = cursor.fetchone()

                if not po:
                    return Respons(
                        success=False,
                        detail="Purchase order not found",
                        error="NOT_FOUND",
                    )

                po_dict = dict(po)
                po_dict['created_by'] = po_dict.get('created_by') or None
                po_dict['supplier_name'] = po_dict.get('supplier_name') or None
                po_dict['assign_to_name'] = po_dict.get('assign_to_name') or None

                items_data = PurchaseOrdersService._get_purchase_order_items(
                    cursor, tenant_id, org_id, bus_id, purchase_order_id
                )
                batches_data = PurchaseOrdersService._get_purchase_order_batches(
                    cursor, tenant_id, org_id, bus_id, purchase_order_id
                )
                batches_list = []
                if batches_data:
                    for batch in batches_data:
                        batch_dict = dict(batch)
                        # Set new field names for batch quantities
                        batch_dict['specific_product_per_batch_received_qty'] = batch_dict.get('qty_received', 0)
                        batch_dict['specific_product_per_batch_remaining_qty'] = batch_dict.get('qty_remaining', 0)
                        batches_list.append(PurchaseBatchReadDto(**batch_dict))

                batches_by_product = {}
                for batch in batches_list:
                    product_id = batch.product_id
                    if product_id not in batches_by_product:
                        batches_by_product[product_id] = []
                    batches_by_product[product_id].append(batch)

                items_list = []
                for item in items_data:
                    item_dict = dict(item)
                    product_id = item_dict.get('product_id')
                    item_dict['batches'] = batches_by_product.get(product_id, None)
                    currency_id = item_dict.get('currency_id')
                    if currency_id:
                        currency_dict = {
                            'id': currency_id,
                            'name': item_dict.pop('currency_name', None),
                            'code': item_dict.pop('currency_code', None),
                            'symbol': item_dict.pop('currency_symbol', None),
                            'decimal_places': item_dict.pop('currency_decimal_places', None),
                            'currency_position': item_dict.pop('currency_position', None),
                        }
                        item_dict['currency'] = CurrencyReadDto(**currency_dict)
                    else:
                        item_dict['currency'] = None
                    items_list.append(PurchaseOrderItemReadDto(**item_dict))

                po_read = GetPurchaseOrderServiceReadDto(
                    purchase_order=PurchaseOrderReadBase(**po_dict),
                    items=items_list
                )

                return Respons(
                    success=True,
                    detail="Purchase order retrieved successfully",
                    data=[po_read],
                )

        except Exception as e:
            logger.error(f"Error getting purchase order: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get purchase order: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def get_purchase_orders(
        tenant_id: str,
        org_id: str,
        bus_id: str,
        status: Optional[str] = None,
        supplier_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Respons[list[GetPurchaseOrdersServiceReadDto]]:
        """Get list of purchase orders with pagination"""
        logger.info(
            f"Processing get purchase orders request",
            extra={
                "extra_fields": {
                    "tenant_id": tenant_id,
                    "status": status,
                    "supplier_id": supplier_id,
                    "search": search,
                    "page": page,
                    "size": size,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                where_conditions = [
                    "po.tenant_id = %s",
                    "po.org_id = %s",
                    "po.bus_id = %s"
                ]
                params = [tenant_id, org_id, bus_id]

                if status:
                    where_conditions.append("po.status = %s")
                    params.append(status)

                if supplier_id:
                    where_conditions.append("po.supplier_id = %s")
                    params.append(supplier_id)

                if search:
                    where_conditions.append(
                        "(po.po_number ILIKE %s OR po.notes ILIKE %s)"
                    )
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern])

                where_clause = " AND ".join(where_conditions)

                cursor.execute(
                    f"""SELECT COUNT(*) as total FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    WHERE {where_clause}""",
                    params,
                )
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0

                offset = (page - 1) * size
                pagination_meta = PaginationMeta(
                    page=page,
                    size=size,
                    total=total,
                    total_pages=(total + size - 1) // size if total > 0 else 0,
                    has_next=(page * size) < total
                )

                cursor.execute(
                    f"""SELECT po.*,
                           creator.fullname as created_by,
                           supplier.fullname as supplier_name,
                           assignee.fullname as assign_to_name
                    FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE} po
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} creator ON po.created_by = creator.id AND po.tenant_id = creator.tenant_id
                    LEFT JOIN {db_settings.MSG_SUPPLIERS_TABLE} supplier ON po.supplier_id = supplier.id 
                        AND po.tenant_id = supplier.tenant_id 
                        AND po.org_id = supplier.org_id 
                        AND po.bus_id = supplier.bus_id
                    LEFT JOIN {db_settings.CORE_PLATFORM_USERS_TABLE} assignee ON po.assign_to = assignee.id AND po.tenant_id = assignee.tenant_id
                    WHERE {where_clause}
                    ORDER BY po.cdatetime DESC
                    LIMIT %s OFFSET %s""",
                    params + [size, offset],
                )
                purchase_orders = cursor.fetchall()

                po_list = []
                for po in purchase_orders:
                    po_dict = dict(po)
                    po_dict['created_by'] = po_dict.get('created_by') or None
                    po_dict['supplier_name'] = po_dict.get('supplier_name') or None
                    po_dict['assign_to_name'] = po_dict.get('assign_to_name') or None

                    items_data = PurchaseOrdersService._get_purchase_order_items(
                        cursor, tenant_id, org_id, bus_id, po_dict['id']
                    )
                    batches_data = PurchaseOrdersService._get_purchase_order_batches(
                        cursor, tenant_id, org_id, bus_id, po_dict['id']
                    )
                    batches_list = []
                    if batches_data:
                        for batch in batches_data:
                            batch_dict = dict(batch)
                            # Set new field names for batch quantities
                            batch_dict['specific_product_per_batch_received_qty'] = batch_dict.get('qty_received', 0)
                            batch_dict['specific_product_per_batch_remaining_qty'] = batch_dict.get('qty_remaining', 0)
                            batches_list.append(PurchaseBatchReadDto(**batch_dict))

                    batches_by_product = {}
                    for batch in batches_list:
                        product_id = batch.product_id
                        if product_id not in batches_by_product:
                            batches_by_product[product_id] = []
                        batches_by_product[product_id].append(batch)

                    items_list = []
                    for item in items_data:
                        item_dict = dict(item)
                        product_id = item_dict.get('product_id')
                        item_dict['batches'] = batches_by_product.get(product_id, None)
                        items_list.append(PurchaseOrderItemReadDto(**item_dict))

                    po_list.append(GetPurchaseOrdersServiceReadDto(
                        purchase_order=PurchaseOrderReadBase(**po_dict),
                        items=items_list
                    ))

                return Respons(
                    success=True,
                    detail="Purchase orders retrieved successfully",
                    data=po_list,
                    meta=pagination_meta,
                )

        except Exception as e:
            logger.error(f"Error getting purchase orders: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to get purchase orders: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def cancel_purchase_order(
        data: CancelPurchaseOrderServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        cancelled_by: str
    ) -> Respons[CancelPurchaseOrderServiceReadDto]:
        """Cancel a purchase order by setting status to CANCELLED"""
        logger.info(
            f"Processing purchase order cancellation: {data.purchase_order_id}",
            extra={
                "extra_fields": {
                    "purchase_order_id": data.purchase_order_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.purchase_order_id, tenant_id, org_id, bus_id),
                )
                existing_po = cursor.fetchone()

                if not existing_po:
                    return Respons(
                        success=False,
                        detail="Purchase order not found",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_po)

                cursor.execute(
                    f"""UPDATE {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    SET status = %s
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    ('CANCELLED', data.purchase_order_id, tenant_id, org_id, bus_id),
                )

                try:
                    cursor.execute(
                        f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                        WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                        (data.purchase_order_id, tenant_id, org_id, bus_id),
                    )
                    complete_new_data_record = cursor.fetchone()
                    complete_new_data = dict(complete_new_data_record) if complete_new_data_record else old_data
                    
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-purchase-orders",
                        resource_id=data.purchase_order_id,
                        action="cancel",
                        old_data=old_data,
                        new_data=complete_new_data,
                        description=f"Purchase order {data.purchase_order_id} cancelled",
                        performed_by=cancelled_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                cancel_result = CancelPurchaseOrderServiceReadDto(
                    purchase_order_id=data.purchase_order_id,
                    message="Purchase order cancelled successfully"
                )

                return Respons(
                    success=True,
                    detail="Purchase order cancelled successfully",
                    data=[cancel_result],
                )

        except Exception as e:
            logger.error(f"Error cancelling purchase order: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to cancel purchase order: {str(e)}",
                error="INTERNAL_ERROR",
            )

    @staticmethod
    def permanent_delete_purchase_order(
        data: PermanentDeletePurchaseOrderServiceWriteDto,
        tenant_id: str,
        org_id: str,
        bus_id: str,
        deleted_by: str
    ) -> Respons[PermanentDeletePurchaseOrderServiceReadDto]:
        """Permanently delete a purchase order and its related items"""
        logger.info(
            f"Processing permanent delete purchase order: {data.purchase_order_id}",
            extra={
                "extra_fields": {
                    "purchase_order_id": data.purchase_order_id,
                    "tenant_id": tenant_id,
                }
            },
        )

        try:
            with DatabaseManager.transaction() as cursor:
                cursor.execute(
                    f"""SELECT * FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.purchase_order_id, tenant_id, org_id, bus_id),
                )
                existing_po = cursor.fetchone()

                if not existing_po:
                    return Respons(
                        success=False,
                        detail="Purchase order not found",
                        error="NOT_FOUND",
                    )

                old_data = dict(existing_po)

                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PURCHASE_ORDER_ITEMS_TABLE}
                    WHERE purchase_order_id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.purchase_order_id, tenant_id, org_id, bus_id),
                )
                items_deleted = cursor.rowcount

                cursor.execute(
                    f"""DELETE FROM {db_settings.MSG_PURCHASE_ORDERS_TABLE}
                    WHERE id = %s AND tenant_id = %s AND org_id = %s AND bus_id = %s""",
                    (data.purchase_order_id, tenant_id, org_id, bus_id),
                )

                if cursor.rowcount == 0:
                    raise ValueError("Failed to delete purchase order")

                try:
                    ActivityLogService.log_activity(
                        tenant_id=tenant_id,
                        resource_type="rt-purchase-orders",
                        resource_id=data.purchase_order_id,
                        action="permanent_delete",
                        old_data=old_data,
                        new_data=None,
                        description=f"Purchase order {data.purchase_order_id} permanently deleted along with {items_deleted} items",
                        performed_by=deleted_by,
                        org_id=org_id,
                        bus_id=bus_id,
                        cursor=cursor
                    )
                except Exception as log_err:
                    logger.warning(f"Activity log failed: {log_err}", exc_info=True)

                delete_result = PermanentDeletePurchaseOrderServiceReadDto(
                    purchase_order_id=data.purchase_order_id,
                    message=f"Purchase order permanently deleted successfully. {items_deleted} items were also deleted."
                )

                return Respons(
                    success=True,
                    detail=f"Purchase order permanently deleted successfully. {items_deleted} items were also deleted.",
                    data=[delete_result],
                )

        except Exception as e:
            logger.error(f"Error permanently deleting purchase order: {str(e)}", exc_info=True)
            return Respons(
                success=False,
                detail=f"Failed to permanently delete purchase order: {str(e)}",
                error="INTERNAL_ERROR",
            )


