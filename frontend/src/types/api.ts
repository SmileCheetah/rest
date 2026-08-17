export type ScheduleStatus = "PENDING" | "COMPLETED";
export type WorkSessionStatus = "READY" | "IN_PROGRESS" | "COMPLETED";

export interface VisitTarget {
  visitTargetId: number;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
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
