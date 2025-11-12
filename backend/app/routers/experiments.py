"""
Experiment management endpoints for A/B testing.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

from app.database import get_db
from app.models import Experiment, ModelVersion
from app.middleware.auth import require_api_key
from app.services.experiment_service import (
    create_experiment,
    compare_experiment_versions,
    get_active_experiment
)

router = APIRouter()


class ModelVersionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    config: Optional[Dict] = None


class ModelVersionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    config: Optional[Dict]
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    variant_a_version_id: int
    variant_b_version_id: int
    traffic_split: float = 0.5


class ExperimentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    variant_a_version_id: Optional[int]
    variant_b_version_id: Optional[int]
    traffic_split: float
    status: str
    start_date: datetime
    end_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/model-versions", response_model=ModelVersionResponse)
async def create_model_version(
    version: ModelVersionCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Create a new model version."""
    model_version = ModelVersion(
        name=version.name,
        description=version.description,
        config=version.config,
        is_active=0
    )
    
    db.add(model_version)
    db.commit()
    db.refresh(model_version)
    
    return model_version


@router.get("/model-versions", response_model=List[ModelVersionResponse])
async def get_model_versions(
    db: Session = Depends(get_db)
):
    """Get all model versions."""
    versions = db.query(ModelVersion).all()
    return versions


@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment_endpoint(
    experiment: ExperimentCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """Create a new A/B test experiment."""
    exp = create_experiment(
        name=experiment.name,
        variant_a_version_id=experiment.variant_a_version_id,
        variant_b_version_id=experiment.variant_b_version_id,
        traffic_split=experiment.traffic_split,
        description=experiment.description,
        db=db
    )
    
    if not exp:
        raise HTTPException(status_code=500, detail="Failed to create experiment")
    
    return exp


@router.get("/experiments", response_model=List[ExperimentResponse])
async def get_experiments(
    db: Session = Depends(get_db)
):
    """Get all experiments."""
    experiments = db.query(Experiment).all()
    return experiments


@router.get("/experiments/{experiment_id}/comparison")
async def get_experiment_comparison(
    experiment_id: int,
    db: Session = Depends(get_db)
):
    """Get comparison metrics for an experiment."""
    comparison = compare_experiment_versions(experiment_id, db)
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return comparison


@router.get("/experiments/active")
async def get_active_experiment_endpoint(
    db: Session = Depends(get_db)
):
    """Get the currently active experiment."""
    experiment = get_active_experiment(db)
    
    if not experiment:
        return {"active": False}
    
    return {
        "active": True,
        "experiment": ExperimentResponse.from_orm(experiment)
    }

