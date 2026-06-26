from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_optional_current_user
from app.api.utils import ensure_company, get_or_404, update_model
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.company import Company
from app.models.configuration import CustomFieldDefinition, WorkObjectType
from app.models.employee import Employee
from app.models.user import User
from app.schemas.configuration import (
    ApplyIndustryTemplatePayload,
    ApplyIndustryTemplateResult,
    CompanySettingsRead,
    CompanySettingsUpdate,
    CustomFieldDefinitionCreate,
    CustomFieldDefinitionRead,
    CustomFieldDefinitionUpdate,
    IndustryTemplateRead,
    WorkObjectTypeCreate,
    WorkObjectTypeRead,
    WorkObjectTypeUpdate,
)
from app.services.configuration_service import (
    apply_industry_template,
    ensure_default_work_object_type,
    get_industry_template,
    list_custom_fields,
    list_industry_templates,
    metadata_dict,
    normalize_key,
    type_is_in_use,
    validate_work_object_type_key,
)
from app.services.event_service import EventService

settings_router = APIRouter(prefix="/company-settings", tags=["configuration"])
templates_router = APIRouter(prefix="/industry-templates", tags=["configuration"])
work_object_types_router = APIRouter(prefix="/work-object-types", tags=["configuration"])
custom_fields_router = APIRouter(prefix="/custom-fields", tags=["configuration"])

WORK_WEEK_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
PRIORITIES = {"low", "medium", "high", "critical"}


def get_linked_employee(db: Session, current_user: User | None) -> Employee | None:
    if current_user is None:
        return None
    return db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.user_id == current_user.id,
            Employee.is_active.is_(True),
        )
    )


def actor_employee_id(db: Session, current_user: User | None) -> UUID | None:
    linked_employee = get_linked_employee(db, current_user)
    return linked_employee.id if linked_employee is not None else None


def normalize_priority(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in PRIORITIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid priority")
    return normalized


def normalize_work_week(days: list[str] | None) -> list[str] | None:
    if days is None:
        return None
    normalized = []
    for day in days:
        day_value = day.strip().lower()
        if day_value not in WORK_WEEK_DAYS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid work week day")
        if day_value not in normalized:
            normalized.append(day_value)
    return normalized


def safe_settings_list(value: object, fallback: list[str]) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return fallback


def safe_settings_int(value: object, fallback: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return fallback


def settings_read(company: Company) -> CompanySettingsRead:
    settings = metadata_dict(company.settings_json)
    metadata = metadata_dict(settings.get("metadata"))
    default_work_week = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    return CompanySettingsRead(
        company_id=company.id,
        name=company.name,
        industry=company.industry,
        size=company.size,
        timezone=company.timezone,
        description=company.description,
        settings=settings,
        work_week=safe_settings_list(settings.get("work_week"), default_work_week),
        default_work_object_type=str(settings.get("default_work_object_type") or "task"),
        default_priority=str(settings.get("default_priority") or "medium"),
        file_upload_max_mb=safe_settings_int(settings.get("file_upload_max_mb"), 10),
        template_key=settings.get("industry_template") if isinstance(settings.get("industry_template"), str) else None,
        metadata=metadata,
    )


@settings_router.get("", response_model=CompanySettingsRead)
def get_company_settings(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> CompanySettingsRead:
    ensure_company_access(current_user, company_id)
    company = get_or_404(db, Company, company_id, label="Company")
    return settings_read(company)


@settings_router.put("", response_model=CompanySettingsRead)
def update_company_settings(
    company_id: UUID,
    payload: CompanySettingsUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> CompanySettingsRead:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    company = get_or_404(db, Company, company_id, label="Company")
    previous_settings = metadata_dict(company.settings_json)
    next_settings = dict(previous_settings)
    changed_fields: list[str] = []

    company_updates = {}
    for field in ["name", "industry", "size", "timezone", "description"]:
        value = getattr(payload, field)
        if value is not None:
            company_updates[field] = value
    if company_updates:
        changed_fields.extend(company_updates.keys())
        for field, value in company_updates.items():
            setattr(company, field, value)

    if payload.work_week is not None:
        next_settings["work_week"] = normalize_work_week(payload.work_week)
        changed_fields.append("work_week")
    if payload.default_work_object_type is not None:
        next_settings["default_work_object_type"] = validate_work_object_type_key(db, company_id, payload.default_work_object_type)
        changed_fields.append("default_work_object_type")
    if payload.default_priority is not None:
        next_settings["default_priority"] = normalize_priority(payload.default_priority)
        changed_fields.append("default_priority")
    if payload.file_upload_max_mb is not None:
        next_settings["file_upload_max_mb"] = payload.file_upload_max_mb
        changed_fields.append("file_upload_max_mb")
    if payload.dashboard_flags is not None:
        next_settings["dashboard_flags"] = payload.dashboard_flags
        changed_fields.append("dashboard_flags")
    if payload.notification_defaults is not None:
        next_settings["notification_defaults"] = payload.notification_defaults
        changed_fields.append("notification_defaults")
    if payload.metadata is not None:
        next_settings["metadata"] = payload.metadata
        changed_fields.append("metadata")

    company.settings_json = next_settings
    if changed_fields:
        EventService.record_event(
            db,
            company_id=company.id,
            actor_user_id=current_user.id if current_user else None,
            actor_employee_id=actor_employee_id(db, current_user),
            event_type="company_settings.updated",
            title="Company settings updated",
            target_entity_type="company",
            target_entity_id=company.id,
            metadata={"changed_fields": sorted(set(changed_fields))},
        )
    db.commit()
    db.refresh(company)
    return settings_read(company)


@templates_router.get("", response_model=list[IndustryTemplateRead])
def list_templates() -> list[IndustryTemplateRead]:
    return list_industry_templates()


@templates_router.get("/{template_key}", response_model=IndustryTemplateRead)
def get_template(template_key: str) -> IndustryTemplateRead:
    return get_industry_template(template_key)


@settings_router.post("/apply-template", response_model=ApplyIndustryTemplateResult)
def apply_template(
    company_id: UUID,
    payload: ApplyIndustryTemplatePayload,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> dict[str, int | str | UUID]:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    company = get_or_404(db, Company, company_id, label="Company")
    result = apply_industry_template(
        db,
        company=company,
        template_key=payload.template_key,
        actor_user_id=current_user.id if current_user else None,
        actor_employee_id=actor_employee_id(db, current_user),
    )
    db.commit()
    return result


@work_object_types_router.get("", response_model=list[WorkObjectTypeRead])
def list_work_object_types(
    company_id: UUID,
    include_inactive: bool = False,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> list[WorkObjectType]:
    ensure_company_access(current_user, company_id)
    ensure_default_work_object_type(db, company_id)
    statement = select(WorkObjectType).where(WorkObjectType.company_id == company_id)
    if not include_inactive:
        statement = statement.where(WorkObjectType.is_active.is_(True))
    db.commit()
    ordered_statement = statement.order_by(WorkObjectType.sort_order.asc(), WorkObjectType.name.asc())
    return list(db.scalars(ordered_statement).all())


@work_object_types_router.post("", response_model=WorkObjectTypeRead, status_code=status.HTTP_201_CREATED)
def create_work_object_type(
    payload: WorkObjectTypeCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObjectType:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    key = normalize_key(payload.key)
    if db.scalar(select(WorkObjectType.id).where(WorkObjectType.company_id == payload.company_id, WorkObjectType.key == key)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Work object type already exists")
    work_type = WorkObjectType(
        company_id=payload.company_id,
        key=key,
        name=payload.name.strip(),
        description=payload.description,
        icon=payload.icon,
        color=payload.color,
        is_default=payload.is_default,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
        metadata_json=payload.metadata,
    )
    db.add(work_type)
    if work_type.is_default:
        unset_other_default_types(db, payload.company_id, work_type)
    db.flush()
    EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_user_id=current_user.id if current_user else None,
        actor_employee_id=actor_employee_id(db, current_user),
        event_type="work_object_type.created",
        title=f"{work_type.name} type created",
        target_entity_type="work_object_type",
        target_entity_id=work_type.id,
        metadata={"type_key": work_type.key},
    )
    db.commit()
    db.refresh(work_type)
    return work_type


def unset_other_default_types(db: Session, company_id: UUID, selected_type: WorkObjectType) -> None:
    for work_type in db.scalars(
        select(WorkObjectType).where(
            WorkObjectType.company_id == company_id,
            WorkObjectType.id != selected_type.id,
            WorkObjectType.is_default.is_(True),
        )
    ).all():
        work_type.is_default = False


@work_object_types_router.patch("/{type_id}", response_model=WorkObjectTypeRead)
def update_work_object_type(
    type_id: UUID,
    company_id: UUID,
    payload: WorkObjectTypeUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObjectType:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    work_type = get_or_404(db, WorkObjectType, type_id, label="Work object type")
    ensure_company(work_type, company_id, label="Work object type")
    changed = update_model(work_type, payload, alias_fields={"metadata": "metadata_json"})
    if "is_default" in changed and work_type.is_default:
        unset_other_default_types(db, company_id, work_type)
    if changed:
        EventService.record_event(
            db,
            company_id=company_id,
            actor_user_id=current_user.id if current_user else None,
            actor_employee_id=actor_employee_id(db, current_user),
            event_type="work_object_type.updated",
            title=f"{work_type.name} type updated",
            target_entity_type="work_object_type",
            target_entity_id=work_type.id,
            metadata={"type_key": work_type.key, "changed_fields": sorted(changed.keys())},
        )
    db.commit()
    db.refresh(work_type)
    return work_type


@work_object_types_router.post("/{type_id}/archive", response_model=WorkObjectTypeRead)
def archive_work_object_type(
    type_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObjectType:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    work_type = get_or_404(db, WorkObjectType, type_id, label="Work object type")
    ensure_company(work_type, company_id, label="Work object type")
    work_type.is_active = False
    EventService.record_event(
        db,
        company_id=company_id,
        actor_user_id=current_user.id if current_user else None,
        actor_employee_id=actor_employee_id(db, current_user),
        event_type="work_object_type.archived",
        title=f"{work_type.name} type archived",
        target_entity_type="work_object_type",
        target_entity_id=work_type.id,
        metadata={"type_key": work_type.key, "in_use": type_is_in_use(db, company_id, work_type.key)},
    )
    db.commit()
    db.refresh(work_type)
    return work_type


@custom_fields_router.get("", response_model=list[CustomFieldDefinitionRead])
def list_custom_field_definitions(
    company_id: UUID,
    type_key: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> list[CustomFieldDefinition]:
    ensure_company_access(current_user, company_id)
    return list_custom_fields(db, company_id, type_key=type_key, include_inactive=include_inactive)


@custom_fields_router.post("", response_model=CustomFieldDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_custom_field(
    payload: CustomFieldDefinitionCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> CustomFieldDefinition:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    type_key = validate_work_object_type_key(db, payload.company_id, payload.type_key)
    field_key = normalize_key(payload.field_key)
    linked_type_id = payload.work_object_type_id
    if linked_type_id is not None:
        linked_type = get_or_404(db, WorkObjectType, linked_type_id, label="Work object type")
        ensure_company(linked_type, payload.company_id, label="Work object type")
        type_key = linked_type.key
    else:
        linked_type = db.scalar(select(WorkObjectType).where(WorkObjectType.company_id == payload.company_id, WorkObjectType.key == type_key))
        linked_type_id = linked_type.id if linked_type is not None else None
    if db.scalar(select(CustomFieldDefinition.id).where(CustomFieldDefinition.company_id == payload.company_id, CustomFieldDefinition.type_key == type_key, CustomFieldDefinition.field_key == field_key)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Custom field already exists")
    custom_field = CustomFieldDefinition(
        company_id=payload.company_id,
        work_object_type_id=linked_type_id,
        type_key=type_key,
        field_key=field_key,
        label=payload.label.strip(),
        field_type=payload.field_type,
        required=payload.required,
        options=payload.options,
        default_value=payload.default_value,
        help_text=payload.help_text,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        metadata_json=payload.metadata,
    )
    db.add(custom_field)
    db.flush()
    EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_user_id=current_user.id if current_user else None,
        actor_employee_id=actor_employee_id(db, current_user),
        event_type="custom_field.created",
        title=f"{custom_field.label} custom field created",
        target_entity_type="custom_field",
        target_entity_id=custom_field.id,
        metadata={"type_key": custom_field.type_key, "field_key": custom_field.field_key},
    )
    db.commit()
    db.refresh(custom_field)
    return custom_field


@custom_fields_router.patch("/{field_id}", response_model=CustomFieldDefinitionRead)
def update_custom_field(
    field_id: UUID,
    company_id: UUID,
    payload: CustomFieldDefinitionUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> CustomFieldDefinition:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    custom_field = get_or_404(db, CustomFieldDefinition, field_id, label="Custom field")
    ensure_company(custom_field, company_id, label="Custom field")
    changed = update_model(custom_field, payload, alias_fields={"metadata": "metadata_json"})
    if "work_object_type_id" in changed and custom_field.work_object_type_id is not None:
        linked_type = get_or_404(db, WorkObjectType, custom_field.work_object_type_id, label="Work object type")
        ensure_company(linked_type, company_id, label="Work object type")
        custom_field.type_key = linked_type.key
        changed["type_key"] = linked_type.key
        duplicate_id = db.scalar(
            select(CustomFieldDefinition.id).where(
                CustomFieldDefinition.company_id == company_id,
                CustomFieldDefinition.type_key == custom_field.type_key,
                CustomFieldDefinition.field_key == custom_field.field_key,
                CustomFieldDefinition.id != custom_field.id,
            )
        )
        if duplicate_id is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Custom field already exists")
    if changed:
        EventService.record_event(
            db,
            company_id=company_id,
            actor_user_id=current_user.id if current_user else None,
            actor_employee_id=actor_employee_id(db, current_user),
            event_type="custom_field.updated",
            title=f"{custom_field.label} custom field updated",
            target_entity_type="custom_field",
            target_entity_id=custom_field.id,
            metadata={"type_key": custom_field.type_key, "field_key": custom_field.field_key, "changed_fields": sorted(changed.keys())},
        )
    db.commit()
    db.refresh(custom_field)
    return custom_field


@custom_fields_router.post("/{field_id}/archive", response_model=CustomFieldDefinitionRead)
def archive_custom_field(
    field_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> CustomFieldDefinition:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    custom_field = get_or_404(db, CustomFieldDefinition, field_id, label="Custom field")
    ensure_company(custom_field, company_id, label="Custom field")
    custom_field.is_active = False
    EventService.record_event(
        db,
        company_id=company_id,
        actor_user_id=current_user.id if current_user else None,
        actor_employee_id=actor_employee_id(db, current_user),
        event_type="custom_field.archived",
        title=f"{custom_field.label} custom field archived",
        target_entity_type="custom_field",
        target_entity_id=custom_field.id,
        metadata={"type_key": custom_field.type_key, "field_key": custom_field.field_key},
    )
    db.commit()
    db.refresh(custom_field)
    return custom_field
