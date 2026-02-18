"""Patient management routes."""

from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from app.api.deps import DbSession, ClinicianOrAdmin, AnyAuthUser
from app.db.models import Patient
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from app.services.audit import AuditService

router = APIRouter()


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a patient",
    description="Create a new patient record. Requires clinician or admin role.",
)
async def create_patient(
    patient_data: PatientCreate,
    db: DbSession,
    current_user: ClinicianOrAdmin,
) -> PatientResponse:
    """Create a new patient.
    
    Args:
        patient_data: Patient creation data.
        db: Database session.
        current_user: Authenticated clinician or admin.
        
    Returns:
        Created patient.
    """
    # Check for duplicate external_id
    if patient_data.external_id:
        result = await db.execute(
            select(Patient).where(Patient.external_id == patient_data.external_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Patient with external_id '{patient_data.external_id}' already exists",
            )

    patient = Patient(
        name=patient_data.name,
        external_id=patient_data.external_id,
        dob=patient_data.dob,
    )
    db.add(patient)
    await db.flush()

    # Audit log
    audit = AuditService(db)
    await audit.log(
        actor_user_id=current_user.id,
        action="create",
        entity_type="patient",
        entity_id=patient.id,
        after_data=patient_data.model_dump_json(),
    )

    return PatientResponse.model_validate(patient)


@router.get(
    "",
    response_model=List[PatientResponse],
    summary="List patients",
    description="Get a list of all patients. Available to all authenticated users.",
)
async def list_patients(
    db: DbSession,
    current_user: AnyAuthUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> List[PatientResponse]:
    """List all patients with optional search.
    
    Args:
        db: Database session.
        current_user: Authenticated user.
        skip: Number of records to skip.
        limit: Maximum records to return.
        search: Optional search term for name.
        
    Returns:
        List of patients.
    """
    query = select(Patient).order_by(Patient.created_at.desc())

    if search:
        query = query.where(Patient.name.ilike(f"%{search}%"))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    patients = result.scalars().all()

    return [PatientResponse.model_validate(p) for p in patients]


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get patient by ID",
    description="Get a specific patient by their ID.",
)
async def get_patient(
    patient_id: int,
    db: DbSession,
    current_user: AnyAuthUser,
) -> PatientResponse:
    """Get a patient by ID.
    
    Args:
        patient_id: Patient ID.
        db: Database session.
        current_user: Authenticated user.
        
    Returns:
        Patient details.
    """
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    return PatientResponse.model_validate(patient)


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update patient",
    description="Update a patient's information. Requires clinician or admin role.",
)
async def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    db: DbSession,
    current_user: ClinicianOrAdmin,
) -> PatientResponse:
    """Update a patient.
    
    Args:
        patient_id: Patient ID.
        patient_data: Update data.
        db: Database session.
        current_user: Authenticated clinician or admin.
        
    Returns:
        Updated patient.
    """
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    # Store before state
    before_data = PatientResponse.model_validate(patient).model_dump_json()

    # Update fields
    if patient_data.name is not None:
        patient.name = patient_data.name
    if patient_data.external_id is not None:
        # Check for duplicate
        result = await db.execute(
            select(Patient).where(
                Patient.external_id == patient_data.external_id,
                Patient.id != patient_id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"External ID '{patient_data.external_id}' already in use",
            )
        patient.external_id = patient_data.external_id
    if patient_data.dob is not None:
        patient.dob = patient_data.dob

    # Audit log
    audit = AuditService(db)
    await audit.log(
        actor_user_id=current_user.id,
        action="update",
        entity_type="patient",
        entity_id=patient.id,
        before_data=before_data,
        after_data=PatientResponse.model_validate(patient).model_dump_json(),
    )

    return PatientResponse.model_validate(patient)


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete patient",
    description="Delete a patient. Requires admin role.",
)
async def delete_patient(
    patient_id: int,
    db: DbSession,
    current_user: ClinicianOrAdmin,
) -> None:
    """Delete a patient.
    
    Args:
        patient_id: Patient ID.
        db: Database session.
        current_user: Authenticated admin.
    """
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    # Audit log before deletion
    audit = AuditService(db)
    await audit.log(
        actor_user_id=current_user.id,
        action="delete",
        entity_type="patient",
        entity_id=patient.id,
        before_data=PatientResponse.model_validate(patient).model_dump_json(),
    )

    await db.delete(patient)
