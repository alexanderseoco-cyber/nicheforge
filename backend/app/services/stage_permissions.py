from enum import Enum

class StagePermission(str, Enum):
    EXECUTE = "EXECUTE"
    REUSE = "REUSE"
    REUSE_IF_COMPATIBLE = "REUSE_IF_COMPATIBLE"
    SKIP = "SKIP"
    FORBIDDEN = "FORBIDDEN"

STAGES = ("POPULATION", "SEARCH_VOLUME", "SERP", "PRIMARY_AUTHORITY", "AHREFS", "BACKLINKS", "KD", "FINALIZATION")

def permissions(run_type: str = "STANDARD", *, authority_only: bool = False) -> dict[str, StagePermission]:
    if run_type == "RECALCULATION":
        result = {stage: StagePermission.REUSE for stage in STAGES}
        result.update({"SERP": StagePermission.REUSE_IF_COMPATIBLE, "PRIMARY_AUTHORITY": StagePermission.EXECUTE, "FINALIZATION": StagePermission.EXECUTE})
        if authority_only:
            result["SERP"] = StagePermission.FORBIDDEN
        return result
    return {stage: StagePermission.EXECUTE for stage in STAGES}

class ForbiddenStageError(RuntimeError):
    pass

def require_stage(permission: StagePermission, stage: str) -> None:
    if permission == StagePermission.FORBIDDEN:
        raise ForbiddenStageError(f"stage {stage} is forbidden for this run")
