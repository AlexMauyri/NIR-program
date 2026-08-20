from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from mlflow.tracking import MlflowClient

from dependencies import get_mlflow_client, MLFlowConnectionError


router = APIRouter(prefix="/ml-models", tags=["ml-models"])


class ModelInfo(BaseModel):
    name: str
    version: str
    alias: str = "production"
    metrics: dict = {}


@router.get("", response_model=list[ModelInfo])
def list_production_models(client: MlflowClient = Depends(get_mlflow_client)):
    try:
        registered = client.search_registered_models()
    except MLFlowConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MLFlow error: {e}")
    
    result = []
    for rm in registered:
        for v in rm.latest_versions:
            if "production" in v.aliases:
                metrics = {}
                try:
                    run = client.get_run(v.run_id)
                    metrics = dict(run.data.metrics)
                except Exception:
                    pass
                
                result.append(ModelInfo(
                    name=rm.name,
                    version=v.version,
                    metrics=metrics,
                ))
    
    return result
