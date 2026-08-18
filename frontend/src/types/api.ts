export type ScheduleStatus = "PENDING" | "COMPLETED";
export type WorkSessionStatus = "READY" | "IN_PROGRESS" | "COMPLETED";

export interface VisitTarget {
  visitTargetId: number;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
}

export interface CoolingSpot {
  id: number;
  name: string;
  type: "PUBLIC" | "COMPANY";
  address: string;
  latitude: number;
  longitude: number;
  openTime: string | null;
  closeTime: string | null;
  facilities: Record<string, boolean> | null;
  source: string | null;
}

export interface Schedule {
  scheduleId: number;
  workSessionId: number;
  scheduledTime: string;
  visitOrder: number;
  status: ScheduleStatus;
  plannedVisitMinutes: number | null;
  completedAt: string | null;
  visitTarget: VisitTarget;
}

export interface NextScheduleResult {
  workSessionId: number;
  workCompleted: boolean;
  nextSchedule: Schedule | null;
}

export interface WorkSession {
  workSessionId: number;
  workDate: string;
  status: WorkSessionStatus;
  startedAt: string | null;
  completedAt: string | null;
  completedVisitCount: number;
  totalVisitCount: number;
  totalExposureMinutes: number;
  maxContinuousExposureMinutes: number;
  totalRestMinutes: number;
  restCount: number;
  heatExposureReductionMinutes: number;
  usedCoolingSpotNames: string[];
}

export interface CreateScheduleRequest {
  visitTargetId: number;
  scheduleDate: string;
  scheduledTime: string;
  visitOrder: number;
  plannedVisitMinutes?: number;
}

export interface CurrentWeather {
  latitude: number;
  longitude: number;
  gridX: number;
  gridY: number;
  observedAt: string;
  temperature: number;
  humidity: number;
  apparentTemperature: number;
  source: "KMA";
}

export interface ForecastWeatherValue {
  forecastAt: string;
  temperature: number;
  humidity: number;
  apparentTemperature: number;
}

export interface HourlyWeather {
  latitude: number;
  longitude: number;
  forecastDate: string;
  forecasts: ForecastWeatherValue[];
  source: "KMA";
}

export type HeatwaveLevel = "NONE" | "INTEREST" | "CAUTION" | "WARNING" | "DANGER";

export interface HeatwaveImpact {
  regionId: string;
  regionName: string;
  announcedAt: string;
  effectiveDate: string | null;
  level: HeatwaveLevel;
  label: string;
  hasAnnouncement: boolean;
  forecasts: Array<{
    category: string;
    level: HeatwaveLevel;
    label: string;
    effectiveDate: string;
  }>;
  source: "KMA";
}

export interface LivingIndexValue {
  value: number;
  label: string;
  forecastAt: string;
}

export interface LivingWeatherIndex {
  areaNo: string;
  publishedAt: string;
  ultraviolet: LivingIndexValue;
  airDiffusion: LivingIndexValue;
  source: "KMA";
}

export interface Coordinate {
  latitude: number;
  longitude: number;
  name?: string;
}

export interface RoutePathPoint {
  latitude: number;
  longitude: number;
}

export interface CreateRouteSegmentRequest {
  workSessionId: number;
  scheduleId: number;
  origin: Coordinate;
  destination: Coordinate;
  departureTime: string;
}

export interface RouteSegment {
  routeSegmentId: number;
  routeOptionId: number;
  workSessionId: number;
  scheduleId: number;
  routeType: "NORMAL" | "SAFE";
  origin: Coordinate;
  destination: Coordinate;
  departureTime: string | null;
  distanceMeters: number;
  walkingMinutes: number;
  estimatedArrivalTime: string | null;
  path: RoutePathPoint[];
  weather: {
    latitude: number;
    longitude: number;
    forecastAt: string;
    temperature: number;
    humidity: number;
    apparentTemperature: number;
    source: "KMA";
  } | null;
}

export interface RiskEvaluation {
  route_option_id: number;
  apparentTemperature: number;
  risk_level: "MOVE_POSSIBLE" | "REST_RECOMMENDED" | "REST_REQUIRED";
  rest_required: boolean;
  recommended_rest_count: number;
  reason_codes: string[];
  reason_message: string;
  model_version: string;
}

export interface SafeRoute {
  routeSegmentId: number;
  routeOptionId: number;
  routeType: "SAFE";
  coolingSpot: CoolingSpot;
  distanceMeters: number;
  walkingMinutes: number;
  totalTravelMinutes: number;
  additionalMinutes: number;
  plannedRestMinutes: number;
  estimatedArrivalTime: string;
  path: RoutePathPoint[];
}

export interface RouteRecommendation {
  risk: RiskEvaluation;
  normalRoute: RouteSegment;
  safeRoute: SafeRoute | null;
  shelterRecommendationMessage: string | null;
}

export type RestStatus = "MOVABLE" | "REST_RECOMMENDED" | "REST_BEFORE_NEXT_VISIT";

export interface RestDecisionRequest {
  continuousWalkingMinutes: number;
  totalWalkingMinutes: number;
  minutesSinceLastRest: number;
  recentRestMinutes: number;
  temperature?: number;
  humidity?: number;
  observedAt: string;
  nextTravelMinutes: number;
  coolingSpotNearby: boolean;
  distanceToCoolingSpotMeters: number | null;
}

export interface RestDecisionResponse {
  decision: {
    shouldRest: boolean;
    restTiming: "NOW" | "AFTER_NEXT_VISIT" | "SOON" | "NOT_NEEDED";
    recommendation: string;
    reason: string;
    recommendedRestMinutes: number;
  };
  restStatusPrediction: {
    probabilities: Record<RestStatus, number>;
    decision: RestStatus;
  } | null;
  decisionSource: "AI" | "MODEL" | "FALLBACK";
  weatherSource: "KMA_ASOS" | "REQUEST_FALLBACK";
}
