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
