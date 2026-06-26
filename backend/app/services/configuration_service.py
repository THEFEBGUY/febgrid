from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.configuration import CustomFieldDefinition, WorkObjectType
from app.models.work_object import WorkObject
from app.schemas.configuration import CUSTOM_FIELD_TYPES, IndustryTemplateRead
from app.services.event_service import EventService

BUILTIN_WORK_OBJECT_TYPES = {
    "task": {"key": "task", "name": "Task", "description": "General tracked work.", "is_default": True, "sort_order": 10},
}

INDUSTRY_TEMPLATES: dict[str, dict[str, Any]] = {
    "generic_business": {
        "key": "generic_business",
        "name": "Generic Business",
        "industry": "Generic Business",
        "description": "A simple cross-industry setup for operational work.",
        "work_object_types": [
            {"key": "task", "name": "Task", "description": "General tracked work.", "is_default": True, "sort_order": 10},
            {"key": "request", "name": "Request", "description": "Internal request or follow-up.", "sort_order": 20},
            {"key": "approval", "name": "Approval", "description": "Approval workflow placeholder.", "sort_order": 30},
        ],
        "custom_fields": [
            {"type_key": "request", "field_key": "requester", "label": "Requester", "field_type": "text", "sort_order": 10},
            {"type_key": "approval", "field_key": "approval_owner", "label": "Approval owner", "field_type": "text", "sort_order": 10},
        ],
        "metadata": {"dashboard_label": "Operations"},
    },
    "software_it": {
        "key": "software_it",
        "name": "Software / IT",
        "industry": "Software / IT",
        "description": "Types and fields for product, bug, and engineering work.",
        "work_object_types": [
            {"key": "task", "name": "Task", "description": "General engineering task.", "is_default": True, "sort_order": 10},
            {"key": "bug", "name": "Bug", "description": "Defect or regression report.", "sort_order": 20, "color": "red"},
            {"key": "feature", "name": "Feature", "description": "New product capability.", "sort_order": 30, "color": "blue"},
            {"key": "incident", "name": "Incident", "description": "Operational incident or outage.", "sort_order": 40, "color": "amber"},
        ],
        "custom_fields": [
            {"type_key": "bug", "field_key": "severity", "label": "Severity", "field_type": "select", "options": ["low", "medium", "high", "critical"], "sort_order": 10},
            {"type_key": "bug", "field_key": "environment", "label": "Environment", "field_type": "text", "sort_order": 20},
            {"type_key": "bug", "field_key": "steps_to_reproduce", "label": "Steps to reproduce", "field_type": "textarea", "sort_order": 30},
            {"type_key": "feature", "field_key": "target_release", "label": "Target release", "field_type": "text", "sort_order": 10},
            {"type_key": "incident", "field_key": "impact", "label": "Impact", "field_type": "textarea", "sort_order": 10},
        ],
        "metadata": {"dashboard_label": "Product delivery"},
    },
    "marketing_agency": {
        "key": "marketing_agency",
        "name": "Marketing / Agency",
        "industry": "Marketing / Agency",
        "description": "Campaign, asset, and client approval work setup.",
        "work_object_types": [
            {"key": "task", "name": "Task", "is_default": True, "sort_order": 10},
            {"key": "campaign", "name": "Campaign", "description": "Campaign execution work.", "sort_order": 20, "color": "teal"},
            {"key": "approval", "name": "Client Approval", "description": "Client approval or review.", "sort_order": 30, "color": "amber"},
        ],
        "custom_fields": [
            {"type_key": "campaign", "field_key": "channel", "label": "Channel", "field_type": "select", "options": ["social", "email", "paid", "seo", "offline"], "sort_order": 10},
            {"type_key": "campaign", "field_key": "client", "label": "Client", "field_type": "text", "sort_order": 20},
            {"type_key": "approval", "field_key": "approval_due", "label": "Approval due", "field_type": "date", "sort_order": 10},
        ],
        "metadata": {"dashboard_label": "Campaign work"},
    },
    "retail_operations": {
        "key": "retail_operations",
        "name": "Retail / Operations",
        "industry": "Retail / Operations",
        "description": "Store, supplier, stock, and operations defaults.",
        "work_object_types": [
            {"key": "task", "name": "Task", "is_default": True, "sort_order": 10},
            {"key": "stock_check", "name": "Stock Check", "description": "Inventory or shelf check.", "sort_order": 20, "color": "green"},
            {"key": "supplier_order", "name": "Supplier Order", "description": "Supplier or purchase follow-up.", "sort_order": 30},
            {"key": "incident", "name": "Store Incident", "description": "Store issue or exception.", "sort_order": 40, "color": "red"},
        ],
        "custom_fields": [
            {"type_key": "stock_check", "field_key": "store_location", "label": "Store location", "field_type": "text", "sort_order": 10},
            {"type_key": "stock_check", "field_key": "sku", "label": "SKU", "field_type": "text", "sort_order": 20},
            {"type_key": "supplier_order", "field_key": "supplier", "label": "Supplier", "field_type": "text", "sort_order": 10},
        ],
        "metadata": {"dashboard_label": "Store operations"},
    },
    "services_field_team": {
        "key": "services_field_team",
        "name": "Services / Field Team",
        "industry": "Services / Field Team",
        "description": "Field work, delivery, and site visit defaults.",
        "work_object_types": [
            {"key": "task", "name": "Task", "is_default": True, "sort_order": 10},
            {"key": "site_visit", "name": "Site Visit", "description": "Field visit or inspection.", "sort_order": 20, "color": "blue"},
            {"key": "delivery", "name": "Delivery", "description": "Delivery or logistics work.", "sort_order": 30, "color": "green"},
            {"key": "follow_up", "name": "Follow-up", "description": "Customer or field follow-up.", "sort_order": 40},
        ],
        "custom_fields": [
            {"type_key": "site_visit", "field_key": "site_name", "label": "Site name", "field_type": "text", "sort_order": 10},
            {"type_key": "site_visit", "field_key": "location", "label": "Location", "field_type": "text", "sort_order": 20},
            {"type_key": "delivery", "field_key": "vehicle_number", "label": "Vehicle number", "field_type": "text", "sort_order": 10},
            {"type_key": "delivery", "field_key": "proof_required", "label": "Proof required", "field_type": "checkbox", "default_value": True, "sort_order": 20},
        ],
        "metadata": {"dashboard_label": "Field operations"},
    },
}


def metadata_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def normalize_key(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized or not normalized[0].isalpha() or not all(character.isalnum() or character == "_" for character in normalized):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid key")
    return normalized


def list_industry_templates() -> list[IndustryTemplateRead]:
    return [IndustryTemplateRead(**template) for template in INDUSTRY_TEMPLATES.values()]


def get_industry_template(template_key: str) -> IndustryTemplateRead:
    normalized = normalize_key(template_key)
    template = INDUSTRY_TEMPLATES.get(normalized)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Industry template not found")
    return IndustryTemplateRead(**template)


def ensure_default_work_object_type(db: Session, company_id: UUID) -> WorkObjectType:
    existing = db.scalar(
        select(WorkObjectType).where(
            WorkObjectType.company_id == company_id,
            WorkObjectType.key == "task",
        )
    )
    if existing is not None:
        return existing
    default = BUILTIN_WORK_OBJECT_TYPES["task"]
    work_type = WorkObjectType(
        company_id=company_id,
        key="task",
        name=default["name"],
        description=default["description"],
        is_default=True,
        is_active=True,
        sort_order=10,
        metadata_json={},
    )
    db.add(work_type)
    db.flush()
    return work_type


def active_work_object_type(db: Session, company_id: UUID, type_key: str) -> WorkObjectType | None:
    normalized = normalize_key(type_key)
    return db.scalar(
        select(WorkObjectType).where(
            WorkObjectType.company_id == company_id,
            WorkObjectType.key == normalized,
            WorkObjectType.is_active.is_(True),
        )
    )


def validate_work_object_type_key(db: Session, company_id: UUID, raw_type_key: str) -> str:
    normalized = normalize_key(raw_type_key)
    if active_work_object_type(db, company_id, normalized) is not None:
        return normalized
    if normalized in BUILTIN_WORK_OBJECT_TYPES:
        ensure_default_work_object_type(db, company_id)
        return normalized
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid work object type")


def list_custom_fields(db: Session, company_id: UUID, type_key: str | None = None, include_inactive: bool = False) -> list[CustomFieldDefinition]:
    statement = select(CustomFieldDefinition).where(CustomFieldDefinition.company_id == company_id)
    if type_key:
        statement = statement.where(CustomFieldDefinition.type_key == normalize_key(type_key))
    if not include_inactive:
        statement = statement.where(CustomFieldDefinition.is_active.is_(True))
    return list(db.scalars(statement.order_by(CustomFieldDefinition.type_key.asc(), CustomFieldDefinition.sort_order.asc())).all())


def validate_custom_field_values(db: Session, *, company_id: UUID, type_key: str, values: dict[str, Any] | None) -> dict[str, Any]:
    custom_values = dict(values or {})
    definitions = list_custom_fields(db, company_id, type_key, include_inactive=False)
    for definition in definitions:
        value = custom_values.get(definition.field_key, None)
        if value in (None, ""):
            if definition.default_value is not None and definition.field_key not in custom_values:
                custom_values[definition.field_key] = definition.default_value
                value = definition.default_value
            elif definition.required:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{definition.label} is required",
                )
        if value in (None, ""):
            continue
        validate_custom_field_value(definition, value)
    return custom_values


def validate_custom_field_value(definition: CustomFieldDefinition, value: Any) -> None:
    field_type = definition.field_type
    if field_type not in CUSTOM_FIELD_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid custom field type")
    if field_type in {"text", "textarea", "date"}:
        if not isinstance(value, str):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{definition.label} must be text")
    elif field_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{definition.label} must be a number")
    elif field_type == "checkbox":
        if not isinstance(value, bool):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{definition.label} must be true or false")
    elif field_type == "select":
        if not isinstance(value, str) or (definition.options and value not in definition.options):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{definition.label} must be one of the configured options")
    elif field_type == "multiselect":
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{definition.label} must be a list")
        if definition.options and any(item not in definition.options for item in value):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{definition.label} has an invalid option")


def apply_industry_template(
    db: Session,
    *,
    company: Company,
    template_key: str,
    actor_user_id: UUID | None = None,
    actor_employee_id: UUID | None = None,
) -> dict[str, int | str | UUID]:
    template = get_industry_template(template_key)
    created_type_count = 0
    skipped_type_count = 0
    created_custom_field_count = 0
    skipped_custom_field_count = 0
    type_by_key: dict[str, WorkObjectType] = {}
    default_type_key: str | None = None

    for template_type in template.work_object_types:
        key = normalize_key(template_type.key)
        if template_type.is_default:
            default_type_key = key
        existing = db.scalar(select(WorkObjectType).where(WorkObjectType.company_id == company.id, WorkObjectType.key == key))
        if existing is None:
            existing = WorkObjectType(
                company_id=company.id,
                key=key,
                name=template_type.name,
                description=template_type.description,
                icon=template_type.icon,
                color=template_type.color,
                is_default=template_type.is_default,
                is_active=True,
                sort_order=template_type.sort_order,
                metadata_json={},
            )
            db.add(existing)
            db.flush()
            created_type_count += 1
        else:
            skipped_type_count += 1
        type_by_key[key] = existing

    if default_type_key is not None:
        for work_type in db.scalars(select(WorkObjectType).where(WorkObjectType.company_id == company.id)).all():
            work_type.is_default = work_type.key == default_type_key

    for template_field in template.custom_fields:
        type_key = normalize_key(template_field.type_key)
        field_key = normalize_key(template_field.field_key)
        existing_field = db.scalar(
            select(CustomFieldDefinition).where(
                CustomFieldDefinition.company_id == company.id,
                CustomFieldDefinition.type_key == type_key,
                CustomFieldDefinition.field_key == field_key,
            )
        )
        if existing_field is None:
            db.add(
                CustomFieldDefinition(
                    company_id=company.id,
                    work_object_type_id=type_by_key.get(type_key).id if type_key in type_by_key else None,
                    type_key=type_key,
                    field_key=field_key,
                    label=template_field.label,
                    field_type=template_field.field_type,
                    required=template_field.required,
                    options=template_field.options,
                    default_value=template_field.default_value,
                    help_text=template_field.help_text,
                    sort_order=template_field.sort_order,
                    is_active=True,
                    metadata_json={},
                )
            )
            created_custom_field_count += 1
        else:
            skipped_custom_field_count += 1

    settings_payload = metadata_dict(company.settings_json)
    settings_payload["industry_template"] = template.key
    settings_payload["dashboard_label"] = template.metadata.get("dashboard_label")
    settings_payload["default_work_object_type"] = default_type_key or str(settings_payload.get("default_work_object_type") or "task")
    company.settings_json = settings_payload
    if template.industry:
        company.industry = template.industry

    EventService.record_event(
        db,
        company_id=company.id,
        actor_user_id=actor_user_id,
        actor_employee_id=actor_employee_id,
        event_type="industry_template.applied",
        title=f"{template.name} template applied",
        target_entity_type="company",
        target_entity_id=company.id,
        metadata={
            "template_key": template.key,
            "created_type_count": created_type_count,
            "created_custom_field_count": created_custom_field_count,
            "skipped_type_count": skipped_type_count,
            "skipped_custom_field_count": skipped_custom_field_count,
        },
    )

    return {
        "company_id": company.id,
        "template_key": template.key,
        "created_type_count": created_type_count,
        "created_custom_field_count": created_custom_field_count,
        "skipped_type_count": skipped_type_count,
        "skipped_custom_field_count": skipped_custom_field_count,
    }


def type_is_in_use(db: Session, company_id: UUID, type_key: str) -> bool:
    return db.scalar(
        select(WorkObject.id).where(
            WorkObject.company_id == company_id,
            WorkObject.object_type == normalize_key(type_key),
        ).limit(1)
    ) is not None
