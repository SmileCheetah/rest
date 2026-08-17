from enum import StrEnum


class WorkSessionStatus(StrEnum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class ScheduleStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class RouteType(StrEnum):
    NORMAL = "NORMAL"
    SAFE = "SAFE"


class RiskLevel(StrEnum):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    REST_REQUIRED = "REST_REQUIRED"


class CoolingSpotType(StrEnum):
    PUBLIC = "PUBLIC"
    COMPANY = "COMPANY"


class ActivityType(StrEnum):
    WORK_STARTED = "WORK_STARTED"
    NORMAL_ROUTE_SELECTED = "NORMAL_ROUTE_SELECTED"
    SAFE_ROUTE_SELECTED = "SAFE_ROUTE_SELECTED"
    REST_COMPLETED = "REST_COMPLETED"
    REST_SKIPPED = "REST_SKIPPED"
    VISIT_COMPLETED = "VISIT_COMPLETED"
    WORK_COMPLETED = "WORK_COMPLETED"
