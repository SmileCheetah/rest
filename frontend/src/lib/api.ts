import type {
  CreateScheduleRequest,
  CreateRouteSegmentRequest,
  CurrentWeather,
  HourlyWeather,
  CoolingSpot,
  HeatwaveImpact,
  LivingWeatherIndex,
  NextScheduleResult,
  Schedule,
  RouteSegment,
  RouteRecommendation,
  RestDecisionRequest,
  RestDecisionResponse,
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
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 30_000);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: options.signal ?? controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("경로 추천 시간이 초과되었습니다. 다시 시도해주세요.", 408);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }

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

export function getCoolingSpots(latitude?: number, longitude?: number, radius = 2_000): Promise<CoolingSpot[]> {
  const params = new URLSearchParams();
  if (latitude !== undefined && longitude !== undefined) {
    params.set("latitude", String(latitude));
    params.set("longitude", String(longitude));
    params.set("radius", String(radius));
  }
  return apiRequest(`/cooling-spots${params.size ? `?${params}` : ""}`);
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

export function selectRouteOption(routeOptionId: number): Promise<{ routeOptionId: number; selected: boolean }> {
  return apiRequest(`/routes/options/${routeOptionId}/select`, {
    method: "PATCH",
  });
}

export function resetDemoWorkSession(): Promise<WorkSession> {
  return apiRequest("/work-sessions/reset", { method: "POST" });
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

export function getHourlyWeather(
  latitude: number,
  longitude: number,
  date: string,
): Promise<HourlyWeather> {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    date,
  });
  return apiRequest(`/weather/hourly?${params}`);
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

export function recommendRoute(
  routeSegmentId: number,
  currentContinuousExposureMinutes = 0,
): Promise<RouteRecommendation> {
  return apiRequest("/routes/recommendation", {
    method: "POST",
    body: JSON.stringify({
      routeSegmentId,
      currentContinuousExposureMinutes,
      plannedRestMinutes: 10,
      maxAdditionalMinutes: 5,
    }),
  });
}

/** XGBoost 기반 휴식 판단 결과를 반환합니다. */
export function evaluateRestDecision(
  request: RestDecisionRequest,
): Promise<RestDecisionResponse> {
  return apiRequest("/rest/decision", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
