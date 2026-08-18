"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  completeSchedule,
  completeWorkSession,
  createRouteSegment,
  createSchedule,
  deleteSchedule,
  getCurrentWeather,
  getCurrentHeatwave,
  getLivingWeatherIndex,
  getCurrentWorkSession,
  getNextSchedule,
  getTodaySchedules,
  getVisitTargets,
  startWorkSession,
} from "@/lib/api";
import type {
  CurrentWeather,
  HeatwaveImpact,
  LivingWeatherIndex,
  RoutePathPoint,
  RouteSegment,
  Schedule,
  VisitTarget,
  WorkSession,
} from "@/types/api";
import RealMap from "@/components/RealMap";

type Screen = "schedule" | "route" | "guidance" | "complete";
type Modal = "add" | "menu" | "ai" | "warning" | "spot" | "skip" | null;

type VisitCard = {
  scheduleId: number;
  visitOrder: number;
  time: string;
  name: string;
  address: string;
  walk: string;
  distance: string;
  riskStatus: string;
  tone: "safe" | "caution" | "danger";
  rests: number;
  latitude: number;
  longitude: number;
};

const routeMocks = [
  { walk: "12분", distance: "0.8km", riskStatus: "이동 가능", tone: "safe" as const, rests: 0 },
  { walk: "18분", distance: "1.2km", riskStatus: "휴식 권장", tone: "caution" as const, rests: 1 },
  { walk: "21분", distance: "1.5km", riskStatus: "다음 방문 전 휴식 필요", tone: "danger" as const, rests: 2 },
  { walk: "15분", distance: "1.0km", riskStatus: "이동 가능", tone: "safe" as const, rests: 0 },
];

const DEFAULT_LOCATION = { latitude: 37.5739, longitude: 127.0105 };

const fallbackVisits: VisitCard[] = [
  { scheduleId: -1, visitOrder: 1, time: "10:00", name: "김○○", address: "종로구 창신동 ○○길 00", ...routeMocks[0], ...DEFAULT_LOCATION },
  { scheduleId: -2, visitOrder: 2, time: "11:30", name: "이○○", address: "종로구 창신동 ○○길 00", ...routeMocks[1], ...DEFAULT_LOCATION },
  { scheduleId: -3, visitOrder: 3, time: "14:00", name: "박○○", address: "종로구 창신동 ○○길 00", ...routeMocks[2], ...DEFAULT_LOCATION },
  { scheduleId: -4, visitOrder: 4, time: "15:30", name: "최○○", address: "종로구 창신동 ○○길 00", ...routeMocks[3], ...DEFAULT_LOCATION },
];

function getBrowserLocation(): Promise<{ latitude: number; longitude: number }> {
  if (!navigator.geolocation) return Promise.resolve(DEFAULT_LOCATION);
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const location = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        };
        const isInKorea = location.latitude >= 33 && location.latitude <= 39
          && location.longitude >= 124 && location.longitude <= 132;
        resolve(isInKorea ? location : DEFAULT_LOCATION);
      },
      () => resolve(DEFAULT_LOCATION),
      { enableHighAccuracy: false, timeout: 5000, maximumAge: 300000 },
    );
  });
}

function getHeatLevel(apparentTemperature: number | undefined) {
  if (apparentTemperature === undefined) return { label: "확인 중", tone: "safe" };
  if (apparentTemperature >= 35) return { label: "위험", tone: "danger" };
  if (apparentTemperature >= 31) return { label: "주의", tone: "caution" };
  return { label: "보통", tone: "safe" };
}

function getHeatwaveTone(level: HeatwaveImpact["level"] | undefined) {
  if (level === "DANGER" || level === "WARNING") return "danger";
  if (level === "CAUTION" || level === "INTEREST") return "caution";
  return "safe";
}

function getUltravioletTone(label: string | undefined) {
  if (label === "위험" || label === "매우 높음") return "danger";
  if (label === "높음" || label === "보통") return "caution";
  return "safe";
}

function toVisitCards(schedules: Schedule[]): VisitCard[] {
  return schedules.map((schedule, index) => ({
    scheduleId: schedule.scheduleId,
    visitOrder: schedule.visitOrder,
    time: schedule.scheduledTime.slice(0, 5),
    name: schedule.visitTarget.name,
    address: schedule.visitTarget.address,
    latitude: schedule.visitTarget.latitude,
    longitude: schedule.visitTarget.longitude,
    ...routeMocks[index % routeMocks.length],
  }));
}

function seoulDateString(): string {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Seoul" });
}

const Icon = ({ name }: { name: "bell" | "more" | "back" | "info" | "close" | "search" | "check" | "alert" }) => {
  const paths = {
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></>,
    more: <><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></>,
    back: <path d="m15 18-6-6 6-6"/>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 10v6M12 7h.01"/></>,
    close: <path d="m6 6 12 12M18 6 6 18"/>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>,
    check: <><circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/></>,
    alert: <><circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 17h.01"/></>,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>;
};

function StatusBar() {
  return <div className="statusbar"><span>9:41</span><span className="status-icons">● ◔ ▰</span></div>;
}

function AiSummary({ onClick }: { onClick?: () => void }) {
  return <button className="ai-rec" onClick={onClick}><strong>추천 휴식 1회</strong><span className="ai-label">AI 분석</span></button>;
}

function routePathToSvg(path: RoutePathPoint[], height: number): string | null {
  if (path.length < 2) return null;
  const longitudes = path.map((point) => point.longitude);
  const latitudes = path.map((point) => point.latitude);
  const minLongitude = Math.min(...longitudes);
  const maxLongitude = Math.max(...longitudes);
  const minLatitude = Math.min(...latitudes);
  const maxLatitude = Math.max(...latitudes);
  const longitudeRange = Math.max(maxLongitude - minLongitude, 0.00001);
  const latitudeRange = Math.max(maxLatitude - minLatitude, 0.00001);
  const padding = 54;
  return path.map((point, index) => {
    const x = padding + ((point.longitude - minLongitude) / longitudeRange) * (375 - padding * 2);
    const y = padding + ((maxLatitude - point.latitude) / latitudeRange) * (height - padding * 2);
    return `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
}

function formatDistance(distanceMeters: number): string {
  return distanceMeters >= 1000
    ? `${(distanceMeters / 1000).toFixed(1)}km`
    : `${distanceMeters}m`;
}

// 이전 SVG 지도 구현은 비교용으로 보존합니다.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function SvgMap({ moving = false, onSpot, route }: { moving?: boolean; onSpot?: () => void; route?: RouteSegment | null }) {
  const height = moving ? 470 : 450;
  const actualPath = routePathToSvg(route?.path ?? [], height);
  const normalPath = actualPath ?? "M70 355 105 330 110 265 160 250 165 190 235 175 235 120 310 105";
  return <div className={`map-area ${moving ? "map-moving" : "map-compare"}`}>
    <svg className="map-svg" viewBox={`0 0 375 ${height}`}>
      <rect width="375" height="470" fill="#F7F9FB"/>
      <g className="map-street"><path d="M-10 80 120 50 200 120 390 90M20 180 100 120 250 160 370 140M0 300 90 250 190 320 375 250M60 0 70 470M180 0 160 470M300 0 320 470"/></g>
      {!moving && <path d={normalPath} className="route-line route-normal"/>}
      <path d={moving && actualPath ? actualPath : moving ? "M75 385 110 345 145 310 180 275 220 240 255 195 290 145" : "M70 355 125 318 165 285 205 270 235 220 260 185 310 105"} className="route-line route-safe"/>
      <circle cx={moving ? 75 : 70} cy={moving ? 385 : 355} r="10" className="current-dot"/>
      <circle cx={moving ? 290 : 310} cy={moving ? 145 : 105} r="10" className="destination-dot"/>
      <circle onClick={onSpot} className="shelter-dot clickable" cx={moving ? 220 : 235} cy={moving ? 240 : 220} r="10"/>
      <circle className="shelter-dot muted-dot" cx="115" cy="140" r="7"/>
      <circle className="shelter-dot muted-dot" cx="300" cy="250" r="7"/>
    </svg>
    {!moving && <><div className="map-legend"><span><i className="line-normal"/>일반 경로 {route ? `${route.walkingMinutes}분 (${formatDistance(route.distanceMeters)})` : "계산 전"}</span><span><i className="line-safe"/>안전 경로 22분 (1.4km)</span></div><button className="map-tag" onClick={onSpot}>추천 쉼터</button></>}
  </div>;
}

function Map({ moving = false, onSpot, route }: { moving?: boolean; onSpot?: () => void; route?: RouteSegment | null }) {
  const destination = route?.destination ?? { ...DEFAULT_LOCATION, name: "방문지" };
  return <div className={`map-area ${moving ? "map-moving" : "map-compare"}`}><RealMap route={route} destination={{ latitude: destination.latitude, longitude: destination.longitude, name: destination.name ?? "방문지" }} onSpot={onSpot} /></div>;
}

export default function Home() {
  const [screen, setScreen] = useState<Screen>("schedule");
  const [modal, setModal] = useState<Modal>(null);
  const [selectedRoute, setSelectedRoute] = useState<"safe" | "normal">("safe");
  const [visits, setVisits] = useState<VisitCard[]>(fallbackVisits);
  const [visitTargets, setVisitTargets] = useState<VisitTarget[]>([]);
  const [workSession, setWorkSession] = useState<WorkSession | null>(null);
  const [currentWeather, setCurrentWeather] = useState<CurrentWeather | null>(null);
  const [heatwaveImpact, setHeatwaveImpact] = useState<HeatwaveImpact | null>(null);
  const [livingIndex, setLivingIndex] = useState<LivingWeatherIndex | null>(null);
  const [completed, setCompleted] = useState<number[]>([]);
  const [activeScheduleId, setActiveScheduleId] = useState<number | null>(null);
  const [activeRoute, setActiveRoute] = useState<RouteSegment | null>(null);
  const [selectedScheduleId, setSelectedScheduleId] = useState<number | null>(null);
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);
  const [scheduleTime, setScheduleTime] = useState("14:30");
  const [targetSearch, setTargetSearch] = useState("");
  const [apiMessage, setApiMessage] = useState<string | null>(null);
  const [weatherMessage, setWeatherMessage] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const filteredVisitTargets = visitTargets.filter((target) =>
    target.name.toLowerCase().includes(targetSearch.trim().toLowerCase()),
  );

  const loadDashboard = useCallback(async () => {
    try {
      const [schedules, targets] = await Promise.all([
        getTodaySchedules(),
        getVisitTargets(),
      ]);
      setVisits(toVisitCards(schedules));
      setCompleted(
        schedules
          .filter((schedule) => schedule.status === "COMPLETED")
          .map((schedule) => schedule.scheduleId),
      );
      setVisitTargets(targets);
      setSelectedTargetId((current) => current ?? targets[0]?.visitTargetId ?? null);
      try {
        setWorkSession(await getCurrentWorkSession());
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          setWorkSession(null);
        } else {
          throw error;
        }
      }
      setApiMessage(null);
    } catch {
      setApiMessage("Backend 연결을 확인해주세요. 현재 화면은 mock 데이터입니다.");
    } finally {
      setIsBusy(false);
    }
  }, []);

  const loadWeather = useCallback(async () => {
    const location = await getBrowserLocation();
    const [weatherResult, heatwaveResult, livingResult] = await Promise.allSettled([
      getCurrentWeather(location.latitude, location.longitude),
      getCurrentHeatwave(),
      getLivingWeatherIndex(),
    ]);
    setCurrentWeather(weatherResult.status === "fulfilled" ? weatherResult.value : null);
    setHeatwaveImpact(heatwaveResult.status === "fulfilled" ? heatwaveResult.value : null);
    setLivingIndex(livingResult.status === "fulfilled" ? livingResult.value : null);
    const hasError = [weatherResult, heatwaveResult, livingResult]
      .some((result) => result.status === "rejected");
    setWeatherMessage(hasError ? "일부 기상 정보를 불러오지 못했습니다. 다시 눌러주세요." : null);
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadDashboard();
      void loadWeather();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [loadDashboard, loadWeather]);

  const handleVisitComplete = async (scheduleId: number) => {
    if (scheduleId < 0) {
      setApiMessage("Backend 연결 후 방문 완료를 처리할 수 있습니다.");
      return;
    }
    if (completed.includes(scheduleId)) return;
    setIsBusy(true);
    try {
      await completeSchedule(scheduleId);
      await loadDashboard();
    } catch (error) {
      setApiMessage(error instanceof Error ? error.message : "방문 완료에 실패했습니다.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleStartWork = async () => {
    setIsBusy(true);
    try {
      const session = await startWorkSession(seoulDateString());
      const next = await getNextSchedule();
      setWorkSession(session);
      setActiveScheduleId(next.nextSchedule?.scheduleId ?? null);
      setApiMessage(null);
      setActiveRoute(null);
      if (next.workCompleted || !next.nextSchedule) {
        setScreen("complete");
      } else {
        setScreen("route");
        const location = await getBrowserLocation();
        try {
          const route = await createRouteSegment({
            workSessionId: session.workSessionId,
            scheduleId: next.nextSchedule.scheduleId,
            origin: { ...location, name: "현재 위치" },
            destination: {
              latitude: next.nextSchedule.visitTarget.latitude,
              longitude: next.nextSchedule.visitTarget.longitude,
              name: next.nextSchedule.visitTarget.name,
            },
            departureTime: new Date().toISOString(),
          });
          setActiveRoute(route);
        } catch (routeError) {
          setApiMessage(routeError instanceof Error ? routeError.message : "경로 생성에 실패했습니다.");
        }
      }
    } catch (error) {
      setApiMessage(error instanceof Error ? error.message : "업무 시작에 실패했습니다.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleAddSchedule = async () => {
    if (selectedTargetId === null) return;
    setIsBusy(true);
    try {
      await createSchedule({
        visitTargetId: selectedTargetId,
        scheduleDate: seoulDateString(),
        scheduledTime: `${scheduleTime}:00`,
        visitOrder: Math.max(0, ...visits.map((visit) => visit.visitOrder)) + 1,
        plannedVisitMinutes: 40,
      });
      setModal(null);
      await loadDashboard();
    } catch (error) {
      setApiMessage(error instanceof Error ? error.message : "일정 추가에 실패했습니다.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleDeleteSchedule = async () => {
    if (selectedScheduleId === null || selectedScheduleId < 0) return;
    setIsBusy(true);
    try {
      await deleteSchedule(selectedScheduleId);
      setModal(null);
      setSelectedScheduleId(null);
      await loadDashboard();
    } catch (error) {
      setApiMessage(error instanceof Error ? error.message : "일정 삭제에 실패했습니다.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleGuidanceComplete = async () => {
    if (activeScheduleId === null) return;
    setIsBusy(true);
    try {
      await completeSchedule(activeScheduleId);
      const next = await getNextSchedule();
      if (next.workCompleted) {
        const sessionId = workSession?.workSessionId ?? next.workSessionId;
        setWorkSession(await completeWorkSession(sessionId));
        setScreen("complete");
      } else {
        setActiveScheduleId(next.nextSchedule?.scheduleId ?? null);
        setScreen("schedule");
      }
      await loadDashboard();
    } catch (error) {
      setApiMessage(error instanceof Error ? error.message : "방문 완료에 실패했습니다.");
    } finally {
      setIsBusy(false);
    }
  };

  const activeVisit =
    visits.find((visit) => visit.scheduleId === activeScheduleId) ??
    visits.find((visit) => !completed.includes(visit.scheduleId)) ??
    visits[0] ??
    fallbackVisits[0];
  const heatLevel = getHeatLevel(currentWeather?.apparentTemperature);
  const displayedHeatLevel = heatwaveImpact?.label ?? heatLevel.label;
  const displayedHeatTone = heatwaveImpact
    ? getHeatwaveTone(heatwaveImpact.level)
    : heatLevel.tone;

  const startRoute = () => selectedRoute === "normal" ? setModal("warning") : setScreen("guidance");

  return <main className="app-shell">
    <section className={`phone ${screen === "complete" ? "completion" : ""}`}>
      <StatusBar />
      {screen === "schedule" && <>
        <header className="appbar"><h1>오늘의 방문 일정</h1><button className="icon-btn" aria-label="알림"><Icon name="bell"/></button></header>
        <div className="screen-content">
          <section className="weather-card">
            <div className="weather-metrics"><div className="sun"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42"/></svg></div><div className="metric"><strong>{currentWeather ? `${Math.round(currentWeather.temperature)}°C` : "--"}</strong><span>현재 기온</span></div><div className="metric"><strong>{currentWeather ? `${Math.round(currentWeather.apparentTemperature)}°C` : "--"}</strong><span>체감 온도</span></div><div className="metric"><strong>{currentWeather ? `${Math.round(currentWeather.humidity)}%` : "--"}</strong><span>습도</span></div></div>
            <div className="weather-footer"><span>{heatwaveImpact ? "폭염 영향예보" : "현재 체감온도 수준"}</span><span className={`badge ${displayedHeatTone}`}>{displayedHeatLevel}</span></div>
            <div className="weather-footer living-index"><span>자외선 지수</span><span className={`badge ${getUltravioletTone(livingIndex?.ultraviolet.label)}`}>{livingIndex ? `${livingIndex.ultraviolet.value} · ${livingIndex.ultraviolet.label}` : "확인 중"}</span></div>
          </section>
          {weatherMessage && <button type="button" className="api-message" onClick={() => void loadWeather()}>{weatherMessage}</button>}
          {apiMessage && <button type="button" className="api-message" onClick={() => void loadDashboard()}>{apiMessage}</button>}
          <div className="section-header"><div><h2>오늘의 방문</h2><span>{completed.length} / {visits.length} 완료</span></div><button className="small-button" disabled={isBusy} onClick={() => setModal("add")}>+ 대상자 추가</button></div>
          <div className="visit-list">{visits.map((visit) => <article className={`visit-card ${completed.includes(visit.scheduleId) ? "done" : ""}`} key={visit.scheduleId}>
            <div className="visit-head"><span className="visit-index">{visit.visitOrder}</span><div className="visit-main"><div><strong>{visit.time}</strong><span>{visit.name}</span></div><p>{visit.address}</p></div><button className={`check-btn ${completed.includes(visit.scheduleId) ? "checked" : ""}`} disabled={isBusy} onClick={() => void handleVisitComplete(visit.scheduleId)} aria-label="방문 완료">{completed.includes(visit.scheduleId) && "✓"}</button>{!completed.includes(visit.scheduleId) && <button className="icon-btn sm" onClick={() => {setSelectedScheduleId(visit.scheduleId); setModal("menu");}} aria-label="더보기"><Icon name="more"/></button>}</div>
            <div className="route-meta">도보 {visit.walk}<span>•</span>{visit.distance}</div><div className="visit-foot"><span className={`badge ${visit.tone}`}>{visit.riskStatus}</span><span className="ai-rec"><strong>추천 휴식 {visit.rests}회</strong><span className="ai-label">AI 분석</span></span></div>
          </article>)}</div>
        </div>
        <footer className="sticky-footer"><button className="button primary" disabled={isBusy || visits.length === 0} onClick={() => void handleStartWork()}>{isBusy ? "처리 중..." : "오늘 첫 방문 시작"}</button></footer>
      </>}

      {screen === "route" && <>
        <header className="appbar"><button className="icon-btn" onClick={() => setScreen("schedule")} aria-label="뒤로"><Icon name="back"/></button><div className="appbar-center"><h1>{activeVisit.name}님 댁</h1><span>{activeVisit.visitOrder}번째 이동 구간</span></div><button className="icon-btn" onClick={() => setModal("ai")} aria-label="AI 분석 근거"><Icon name="info"/></button></header>
        <Map route={activeRoute} onSpot={() => setModal("spot")}/>
        <section className="route-panel"><div className="route-summary"><span className="badge caution">휴식 권장</span><AiSummary onClick={() => setModal("ai")}/></div><p>체감온도가 높고 야외 활동이 길어지고 있어 휴식이 필요한 구간이에요.</p><div className="route-options">
          <button className={`route-card ${selectedRoute === "normal" ? "selected" : ""}`} onClick={() => setSelectedRoute("normal")}><span>일반 경로</span><strong>{activeRoute ? `${activeRoute.walkingMinutes}분` : "계산 전"}</strong><small>{activeRoute ? formatDistance(activeRoute.distanceMeters) : "TMAP 연결 확인 필요"}</small><b>휴식 없음</b></button>
          <button className={`route-card ${selectedRoute === "safe" ? "selected" : ""}`} onClick={() => setSelectedRoute("safe")}><span>안전 경로 <em>추천</em></span><strong>22분</strong><small>1.4km</small><b>휴식 1회</b><i>추천 쉼터: 창신동 주민센터</i></button>
        </div>{apiMessage && <p className="route-error">{apiMessage}</p>}<p className="route-delta">일반 경로보다 <strong>4분 더 걸리지만</strong> 이동 중 1회 쉴 수 있어요.</p><button className="button primary" onClick={startRoute}>{selectedRoute === "safe" ? "안전 경로로 안내 시작" : "일반 경로로 안내 시작"}</button></section>
      </>}

      {screen === "guidance" && <>
        <header className="appbar"><button className="icon-btn" onClick={() => setScreen("route")} aria-label="뒤로"><Icon name="back"/></button><div className="appbar-center"><h1>{activeVisit.name}님 댁</h1><span>이동 중</span></div><button className="icon-btn" onClick={() => setModal("ai")} aria-label="AI 분석 근거"><Icon name="info"/></button></header>
        <div className="move-summary"><span className="badge caution">휴식 권장</span><AiSummary onClick={() => setModal("ai")}/></div><Map moving route={activeRoute} onSpot={() => setModal("spot")}/>
        <section className="guidance-sheet"><div className="handle"/><div className="guidance-main"><strong>{activeRoute ? `${activeRoute.walkingMinutes}분` : activeVisit.walk}</strong><span>•</span><span>{activeRoute ? formatDistance(activeRoute.distanceMeters) : activeVisit.distance}</span></div><p>{activeVisit.name}님 댁까지</p><article className="shelter-summary"><div><span>추천 쉼터</span><strong>창신동 주민센터</strong><small>경로상 약 10분 후 도착</small></div><button className="small-button" onClick={() => setModal("spot")}>자세히 보기</button></article><div className="button-row"><button className="button secondary" onClick={() => setModal("skip")}>쉼터 건너뛰기</button><button className="button teal" disabled={isBusy} onClick={() => void handleGuidanceComplete()}>{isBusy ? "처리 중..." : "길 안내 종료"}</button></div></section>
      </>}

      {screen === "complete" && <div className="completion-content"><div className="completion-mark"><Icon name="check"/></div><h1>오늘의 방문을<br/>모두 완료했어요!</h1><div className="completion-count"><strong>{workSession?.completedVisitCount ?? completed.length} / {workSession?.totalVisitCount ?? visits.length}</strong><span>방문 완료</span></div><div className="stats-row"><article><span>총 야외 이동시간</span><strong>{workSession?.totalExposureMinutes ?? 72}분</strong></article><article><span>총 휴식 횟수</span><strong>{workSession?.restCount ?? 2}회</strong></article><article><span>총 휴식 시간</span><strong>{workSession?.totalRestMinutes ?? 15}분</strong></article></div><article className="hero-stat"><span>폭염 노출 감소</span><strong>15분</strong><small>안전하게 이동했어요!</small></article><section className="used-shelters"><h2>이용한 쿨링스팟</h2><p>창신동 주민센터</p><p>동부여성문화센터</p></section><button className="button teal" onClick={() => setScreen("schedule")}>확인</button></div>}

      {modal && <><div className="dim" onClick={() => setModal(null)}/>{modal === "add" && <section className="bottom-sheet tall"><div className="handle"/><div className="sheet-header"><h2>대상자 추가</h2><button className="icon-btn" onClick={() => setModal(null)}><Icon name="close"/></button></div><p>오늘 방문할 대상자를 선택해주세요.</p><label className="search-box"><Icon name="search"/><input placeholder="이름 검색" value={targetSearch} onChange={(event) => setTargetSearch(event.target.value)} /></label><div className="chip-grid">{filteredVisitTargets.map(target => <button key={target.visitTargetId} onClick={() => setSelectedTargetId(target.visitTargetId)} className={selectedTargetId === target.visitTargetId ? "active" : ""}>{target.name}</button>)}</div>{filteredVisitTargets.length === 0 && <p className="empty-state">검색 결과가 없습니다.</p>}<label className="form-label" htmlFor="schedule-time">방문 예정 시간</label><div className="time-input"><input id="schedule-time" type="time" value={scheduleTime} onChange={(event) => setScheduleTime(event.target.value)} required/></div><button className="button primary" disabled={isBusy || selectedTargetId === null || !scheduleTime} onClick={() => void handleAddSchedule()}>일정에 추가</button></section>}
      {modal === "menu" && <div className="context-menu"><button disabled={isBusy} onClick={() => void handleDeleteSchedule()}>일정에서 삭제</button></div>}
      {modal === "ai" && <section className="dialog"><div className="dialog-icon"><Icon name="info"/></div><h2>AI 분석 근거</h2><p>다음 기준으로 휴식이 필요하다고 판단했어요.</p><ul><li>체감온도 36°C로 높음</li><li>연속 야외 이동시간이 길어지고 있음</li><li>다음 구간까지 이동거리 1.4km</li></ul><button className="button primary" onClick={() => setModal(null)}>확인</button></section>}
      {modal === "warning" && <section className="dialog danger-dialog"><div className="dialog-icon danger"><Icon name="alert"/></div><h2>휴식이 필요한 구간이에요</h2><p>일반 경로는 휴식 없이 이동해야 해요. 그래도 일반 경로로 이동하시겠어요?</p><div className="button-row"><button className="button secondary" onClick={() => setModal(null)}>취소</button><button className="button danger-button" onClick={() => {setModal(null); setScreen("guidance");}}>일반 경로로 이동</button></div></section>}
      {modal === "spot" && <section className="bottom-sheet"><div className="handle"/><div className="sheet-header"><div><div className="sheet-title"><h2>창신동 주민센터</h2><span>무더위쉼터</span></div><p><span className="badge safe">운영 중</span> 09:00 ~ 18:00</p></div><button className="icon-btn" onClick={() => setModal(null)}><Icon name="close"/></button></div><p>현재 위치에서 경로상 약 10분 후 도착<br/>경로에 추가 시 약 3분 더 소요</p><div className="text-chips"><span>냉방</span><span>좌석</span><span>화장실</span><span>식수</span></div><button className="button teal" onClick={() => setModal(null)}>이곳을 경유하기</button></section>}
      {modal === "skip" && <section className="bottom-sheet"><div className="handle"/><h2>쉼터를 이용하지 못했나요?</h2><p>다음 방문 구간 계획에 반영하기 위해 이유를 선택해주세요.</p><div className="radio-list">{["시간이 맞지 않아 이용 못함","길이 불편해서 이용 못함","기타"].map((r, i) => <label key={r}><input type="radio" name="reason" defaultChecked={i === 0}/>{r}</label>)}</div><button className="button teal" onClick={() => setModal(null)}>확인</button></section>}</>}
    </section>
  </main>;
}
