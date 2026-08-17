"use client";

import { useState } from "react";

type Screen = "schedule" | "route" | "guidance" | "complete";
type Modal = "add" | "menu" | "ai" | "warning" | "spot" | "skip" | null;

const visits = [
  { time: "10:00", name: "김○○", walk: "12분", distance: "0.8km", status: "이동 가능", tone: "safe", rests: 0 },
  { time: "11:30", name: "이○○", walk: "18분", distance: "1.2km", status: "휴식 권장", tone: "caution", rests: 1 },
  { time: "14:00", name: "박○○", walk: "21분", distance: "1.5km", status: "다음 방문 전 휴식 필요", tone: "danger", rests: 2 },
  { time: "15:30", name: "최○○", walk: "15분", distance: "1.0km", status: "이동 가능", tone: "safe", rests: 0 },
];

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

function Map({ moving = false, onSpot }: { moving?: boolean; onSpot?: () => void }) {
  return <div className={`map-area ${moving ? "map-moving" : "map-compare"}`}>
    <svg className="map-svg" viewBox={`0 0 375 ${moving ? 470 : 450}`}>
      <rect width="375" height="470" fill="#F7F9FB"/>
      <g className="map-street"><path d="M-10 80 120 50 200 120 390 90M20 180 100 120 250 160 370 140M0 300 90 250 190 320 375 250M60 0 70 470M180 0 160 470M300 0 320 470"/></g>
      {!moving && <path d="M70 355 105 330 110 265 160 250 165 190 235 175 235 120 310 105" className="route-line route-normal"/>}
      <path d={moving ? "M75 385 110 345 145 310 180 275 220 240 255 195 290 145" : "M70 355 125 318 165 285 205 270 235 220 260 185 310 105"} className="route-line route-safe"/>
      <circle cx={moving ? 75 : 70} cy={moving ? 385 : 355} r="10" className="current-dot"/>
      <circle cx={moving ? 290 : 310} cy={moving ? 145 : 105} r="10" className="destination-dot"/>
      <circle onClick={onSpot} className="shelter-dot clickable" cx={moving ? 220 : 235} cy={moving ? 240 : 220} r="10"/>
      <circle className="shelter-dot muted-dot" cx="115" cy="140" r="7"/>
      <circle className="shelter-dot muted-dot" cx="300" cy="250" r="7"/>
    </svg>
    {!moving && <><div className="map-legend"><span><i className="line-normal"/>일반 경로 18분 (1.2km)</span><span><i className="line-safe"/>안전 경로 22분 (1.4km)</span></div><button className="map-tag" onClick={onSpot}>추천 쉼터</button></>}
  </div>;
}

export default function Home() {
  const [screen, setScreen] = useState<Screen>("schedule");
  const [modal, setModal] = useState<Modal>(null);
  const [selectedRoute, setSelectedRoute] = useState<"safe" | "normal">("safe");
  const [completed, setCompleted] = useState<number[]>([0, 1]);
  const [selectedPerson, setSelectedPerson] = useState("김○○");

  const toggleComplete = (index: number) => setCompleted((old) => old.includes(index) ? old.filter((i) => i !== index) : [...old, index]);
  const startRoute = () => selectedRoute === "normal" ? setModal("warning") : setScreen("guidance");

  return <main className="app-shell">
    <section className={`phone ${screen === "complete" ? "completion" : ""}`}>
      <StatusBar />
      {screen === "schedule" && <>
        <header className="appbar"><h1>오늘의 방문 일정</h1><button className="icon-btn" aria-label="알림"><Icon name="bell"/></button></header>
        <div className="screen-content">
          <section className="weather-card">
            <div className="weather-metrics"><div className="sun"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42"/></svg></div><div className="metric"><strong>34°C</strong><span>현재 기온</span></div><div className="metric"><strong>36°C</strong><span>체감 온도</span></div><div className="metric"><strong>72%</strong><span>습도</span></div></div>
            <div className="weather-footer"><span>폭염 영향예보</span><span className="badge caution">주의</span></div>
          </section>
          <div className="section-header"><div><h2>오늘의 방문</h2><span>{completed.length} / {visits.length} 완료</span></div><button className="small-button" onClick={() => setModal("add")}>+ 대상자 추가</button></div>
          <div className="visit-list">{visits.map((visit, index) => <article className={`visit-card ${completed.includes(index) ? "done" : ""}`} key={visit.time}>
            <div className="visit-head"><span className="visit-index">{index + 1}</span><div className="visit-main"><div><strong>{visit.time}</strong><span>{visit.name}</span></div><p>종로구 창신동 ○○길 00</p></div><button className={`check-btn ${completed.includes(index) ? "checked" : ""}`} onClick={() => toggleComplete(index)} aria-label="방문 완료">{completed.includes(index) && "✓"}</button><button className="icon-btn sm" onClick={() => setModal("menu")} aria-label="더보기"><Icon name="more"/></button></div>
            <div className="route-meta">도보 {visit.walk}<span>•</span>{visit.distance}</div><div className="visit-foot"><span className={`badge ${visit.tone}`}>{visit.status}</span><span className="ai-rec"><strong>추천 휴식 {visit.rests}회</strong><span className="ai-label">AI 분석</span></span></div>
          </article>)}</div>
        </div>
        <footer className="sticky-footer"><button className="button primary" onClick={() => setScreen("route")}>오늘 첫 방문 시작</button></footer>
      </>}

      {screen === "route" && <>
        <header className="appbar"><button className="icon-btn" onClick={() => setScreen("schedule")} aria-label="뒤로"><Icon name="back"/></button><div className="appbar-center"><h1>김○○님 댁</h1><span>1번째 이동 구간</span></div><button className="icon-btn" onClick={() => setModal("ai")} aria-label="AI 분석 근거"><Icon name="info"/></button></header>
        <Map onSpot={() => setModal("spot")}/>
        <section className="route-panel"><div className="route-summary"><span className="badge caution">휴식 권장</span><AiSummary onClick={() => setModal("ai")}/></div><p>체감온도가 높고 야외 활동이 길어지고 있어 휴식이 필요한 구간이에요.</p><div className="route-options">
          <button className={`route-card ${selectedRoute === "normal" ? "selected" : ""}`} onClick={() => setSelectedRoute("normal")}><span>일반 경로</span><strong>18분</strong><small>1.2km</small><b>휴식 없음</b></button>
          <button className={`route-card ${selectedRoute === "safe" ? "selected" : ""}`} onClick={() => setSelectedRoute("safe")}><span>안전 경로 <em>추천</em></span><strong>22분</strong><small>1.4km</small><b>휴식 1회</b><i>추천 쉼터: 창신동 주민센터</i></button>
        </div><p className="route-delta">일반 경로보다 <strong>4분 더 걸리지만</strong> 이동 중 1회 쉴 수 있어요.</p><button className="button primary" onClick={startRoute}>{selectedRoute === "safe" ? "안전 경로로 안내 시작" : "일반 경로로 안내 시작"}</button></section>
      </>}

      {screen === "guidance" && <>
        <header className="appbar"><button className="icon-btn" onClick={() => setScreen("route")} aria-label="뒤로"><Icon name="back"/></button><div className="appbar-center"><h1>김○○님 댁</h1><span>이동 중</span></div><button className="icon-btn" onClick={() => setModal("ai")} aria-label="AI 분석 근거"><Icon name="info"/></button></header>
        <div className="move-summary"><span className="badge caution">휴식 권장</span><AiSummary onClick={() => setModal("ai")}/></div><Map moving onSpot={() => setModal("spot")}/>
        <section className="guidance-sheet"><div className="handle"/><div className="guidance-main"><strong>18분</strong><span>•</span><span>1.2km</span></div><p>김○○님 댁까지</p><article className="shelter-summary"><div><span>추천 쉼터</span><strong>창신동 주민센터</strong><small>경로상 약 10분 후 도착</small></div><button className="small-button" onClick={() => setModal("spot")}>자세히 보기</button></article><div className="button-row"><button className="button secondary" onClick={() => setModal("skip")}>쉼터 건너뛰기</button><button className="button teal" onClick={() => setScreen("complete")}>길 안내 종료</button></div></section>
      </>}

      {screen === "complete" && <div className="completion-content"><div className="completion-mark"><Icon name="check"/></div><h1>오늘의 방문을<br/>모두 완료했어요!</h1><div className="completion-count"><strong>4 / 4</strong><span>방문 완료</span></div><div className="stats-row"><article><span>총 야외 이동시간</span><strong>72분</strong></article><article><span>총 휴식 횟수</span><strong>2회</strong></article><article><span>총 휴식 시간</span><strong>15분</strong></article></div><article className="hero-stat"><span>폭염 노출 감소</span><strong>15분</strong><small>안전하게 이동했어요!</small></article><section className="used-shelters"><h2>이용한 쿨링스팟</h2><p>창신동 주민센터</p><p>동부여성문화센터</p></section><button className="button teal" onClick={() => setScreen("schedule")}>확인</button></div>}

      {modal && <><div className="dim" onClick={() => setModal(null)}/>{modal === "add" && <section className="bottom-sheet tall"><div className="handle"/><div className="sheet-header"><h2>대상자 추가</h2><button className="icon-btn" onClick={() => setModal(null)}><Icon name="close"/></button></div><p>오늘 방문할 대상자를 선택해주세요.</p><label className="search-box"><Icon name="search"/><input placeholder="이름 검색"/></label><div className="chip-grid">{["김○○","이○○","박○○","최○○","정○○","한○○","조○○","윤○○"].map(name => <button key={name} onClick={() => setSelectedPerson(name)} className={selectedPerson === name ? "active" : ""}>{name}</button>)}</div><label className="form-label">방문 예정 시간</label><div className="time-input"><span>14</span><span>:</span><span>30</span></div><button className="button primary" onClick={() => setModal(null)}>일정에 추가</button></section>}
      {modal === "menu" && <div className="context-menu"><button onClick={() => setModal(null)}>일정에서 삭제</button></div>}
      {modal === "ai" && <section className="dialog"><div className="dialog-icon"><Icon name="info"/></div><h2>AI 분석 근거</h2><p>다음 기준으로 휴식이 필요하다고 판단했어요.</p><ul><li>체감온도 36°C로 높음</li><li>연속 야외 이동시간이 길어지고 있음</li><li>다음 구간까지 이동거리 1.4km</li></ul><button className="button primary" onClick={() => setModal(null)}>확인</button></section>}
      {modal === "warning" && <section className="dialog danger-dialog"><div className="dialog-icon danger"><Icon name="alert"/></div><h2>휴식이 필요한 구간이에요</h2><p>일반 경로는 휴식 없이 이동해야 해요. 그래도 일반 경로로 이동하시겠어요?</p><div className="button-row"><button className="button secondary" onClick={() => setModal(null)}>취소</button><button className="button danger-button" onClick={() => {setModal(null); setScreen("guidance");}}>일반 경로로 이동</button></div></section>}
      {modal === "spot" && <section className="bottom-sheet"><div className="handle"/><div className="sheet-header"><div><div className="sheet-title"><h2>창신동 주민센터</h2><span>무더위쉼터</span></div><p><span className="badge safe">운영 중</span> 09:00 ~ 18:00</p></div><button className="icon-btn" onClick={() => setModal(null)}><Icon name="close"/></button></div><p>현재 위치에서 경로상 약 10분 후 도착<br/>경로에 추가 시 약 3분 더 소요</p><div className="text-chips"><span>냉방</span><span>좌석</span><span>화장실</span><span>식수</span></div><button className="button teal" onClick={() => setModal(null)}>이곳을 경유하기</button></section>}
      {modal === "skip" && <section className="bottom-sheet"><div className="handle"/><h2>쉼터를 이용하지 못했나요?</h2><p>다음 방문 구간 계획에 반영하기 위해 이유를 선택해주세요.</p><div className="radio-list">{["시간이 맞지 않아 이용 못함","길이 불편해서 이용 못함","기타"].map((r, i) => <label key={r}><input type="radio" name="reason" defaultChecked={i === 0}/>{r}</label>)}</div><button className="button teal" onClick={() => setModal(null)}>확인</button></section>}</>}
    </section>
  </main>;
}
