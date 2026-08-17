import type {
  CreateScheduleRequest,
  CreateRouteSegmentRequest,
  CurrentWeather,
  HeatwaveImpact,
  LivingWeatherIndex,
  NextScheduleResult,
  Schedule,
  RouteSegment,
  VisitTarget,
  WorkSession,
} from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new ApiError(payload?.detail ?? "API 요청에 실패했습니다.", response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function getTodaySchedules(): Promise<Schedule[]> {
  return apiRequest("/schedules/today");
}

export function getNextSchedule(): Promise<NextScheduleResult> {
  return apiRequest("/schedules/next");
}

export function getVisitTargets(): Promise<VisitTarget[]> {
  return apiRequest("/visit-targets");
}

export function getCurrentWorkSession(): Promise<WorkSession> {
  return apiRequest("/work-sessions/current");
}

export function startWorkSession(workDate: string): Promise<WorkSession> {
  return apiRequest("/work-sessions/start", {
    method: "POST",
    body: JSON.stringify({ workDate }),
  });
}

export function completeWorkSession(workSessionId: number): Promise<WorkSession> {
  return apiRequest(`/work-sessions/${workSessionId}/complete`, {
    method: "PATCH",
  });
}

export function createSchedule(request: CreateScheduleRequest): Promise<Schedule> {
  return apiRequest("/schedules", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function deleteSchedule(scheduleId: number): Promise<void> {
  return apiRequest(`/schedules/${scheduleId}`, { method: "DELETE" });
}

export function completeSchedule(scheduleId: number): Promise<Schedule> {
  return apiRequest(`/schedules/${scheduleId}/complete`, { method: "PATCH" });
}

export function getCurrentWeather(
  latitude: number,
  longitude: number,
): Promise<CurrentWeather> {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
  });
  return apiRequest(`/weather/current?${params}`);
}

export function getCurrentHeatwave(): Promise<HeatwaveImpact> {
  return apiRequest("/heatwave/current");
}

export function getLivingWeatherIndex(
  areaNo = "1100000000",
): Promise<LivingWeatherIndex> {
  const params = new URLSearchParams({ areaNo });
  return apiRequest(`/weather/living-index?${params}`);
}

export function createRouteSegment(
  request: CreateRouteSegmentRequest,
): Promise<RouteSegment> {
  return apiRequest("/route-segments", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
