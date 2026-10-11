from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from dependencies import get_mlflow_client, MLFlowConnectionError


router = APIRouter(prefix="/ml-models", tags=["ml-models"])


class ModelInfo(BaseModel):
    name: str
    version: str
    alias: str = "production"
    metrics: dict = {}


class ModelVersionMetrics(BaseModel):
    version: int
    aliases: list[str]
    created_at: datetime
    metrics: dict[str, float]
    params: dict[str, str]


class ModelMetrics(BaseModel):
    model_name: str
    versions: list[ModelVersionMetrics]


class AllModelsMetrics(BaseModel):
    models: dict[str, ModelMetrics]


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
        v = None
        # 1. Прямой поиск по alias 'production' через MlflowClient
        try:
            v = client.get_model_version_by_alias(rm.name, "production")
        except Exception:
            v = None

        # 2. Поиск через rm.aliases словаря RegisteredModel
        if not v:
            aliases_dict = getattr(rm, "aliases", None) or {}
            for alias_name, ver in aliases_dict.items():
                if alias_name.lower() == "production":
                    try:
                        v = client.get_model_version(rm.name, str(ver))
                        break
                    except Exception:
                        pass

        # 3. Fallback: поиск по версиям с детальным запросом get_model_version
        # (search_model_versions в MLflow не заполняет поле aliases)
        if not v:
            try:
                versions = client.search_model_versions(f"name='{rm.name}'")
                for cand in versions:
                    try:
                        detailed = client.get_model_version(rm.name, str(cand.version))
                        cand_aliases = [a.lower() for a in (getattr(detailed, "aliases", None) or [])]
                        if "production" in cand_aliases:
                            v = detailed
                            break
                    except Exception:
                        pass
            except Exception:
                pass

        # 4. Если alias production не установлен ни на одной версии,
        # берём последнюю версию модели, чтобы селектор на фронтенде не блокировался
        if not v:
            try:
                versions = client.search_model_versions(f"name='{rm.name}'")
                if versions:
                    v = max(versions, key=lambda item: int(item.version))
            except Exception:
                pass

        if v:
            metrics = {}
            if v.run_id:
                try:
                    run = client.get_run(v.run_id)
                    metrics = dict(run.data.metrics)
                except Exception:
                    pass

            result.append(ModelInfo(
                name=rm.name,
                version=str(v.version),
                alias="production" if "production" in [a.lower() for a in (getattr(v, "aliases", None) or [])] else (v.aliases[0] if getattr(v, "aliases", None) else ""),
                metrics=metrics,
            ))
    
    return result


def _version_metrics(client: MlflowClient, v) -> ModelVersionMetrics:
    metrics: dict[str, float] = {}
    params: dict[str, str] = {}
    if v.run_id:
        try:
            run = client.get_run(v.run_id)
            metrics = {k: float(val) for k, val in run.data.metrics.items()}
            params = dict(run.data.params)
        except Exception:
            pass

    aliases = list(getattr(v, "aliases", None) or [])
    if not aliases and hasattr(v, "name"):
        try:
            detailed = client.get_model_version(v.name, str(v.version))
            aliases = list(getattr(detailed, "aliases", None) or [])
        except Exception:
            pass

    return ModelVersionMetrics(
        version=int(v.version),
        aliases=aliases,
        created_at=datetime.fromtimestamp(v.creation_timestamp / 1000),
        metrics=metrics,
        params=params,
    )


def _model_metrics(client: MlflowClient, model_name: str) -> ModelMetrics:
    versions = client.search_model_versions(f"name='{model_name}'")
    collected = [_version_metrics(client, v) for v in versions]
    collected.sort(key=lambda m: m.version, reverse=True)
    return ModelMetrics(model_name=model_name, versions=collected)


@router.get("/metrics", response_model=AllModelsMetrics)
def list_all_metrics(client: MlflowClient = Depends(get_mlflow_client)):
    try:
        model_names = [rm.name for rm in client.search_registered_models()]
    except MLFlowConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MLFlow error: {e}")

    models: dict[str, ModelMetrics] = {}
    for name in model_names:
        try:
            models[name] = _model_metrics(client, name)
        except Exception:
            models[name] = ModelMetrics(model_name=name, versions=[])

    return AllModelsMetrics(models=models)


@router.get("/{model_name}/metrics", response_model=ModelMetrics)
def get_model_metrics(model_name: str, client: MlflowClient = Depends(get_mlflow_client)):
    try:
        versions = client.search_model_versions(f"name='{model_name}'")
        if not versions:
            client.get_registered_model(model_name)
        collected = [_version_metrics(client, v) for v in versions]
        collected.sort(key=lambda m: m.version, reverse=True)
        return ModelMetrics(model_name=model_name, versions=collected)
    except MlflowException as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found in Registry")
        raise HTTPException(status_code=503, detail=f"MLFlow unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MLFlow error: {e}")
