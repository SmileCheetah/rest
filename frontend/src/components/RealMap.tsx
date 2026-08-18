"use client";

import { useEffect, useRef } from "react";
import type { CoolingSpot, RouteSegment } from "@/types/api";
import "leaflet/dist/leaflet.css";

type Props = {
  route?: RouteSegment | null;
  normalRoute?: RouteSegment | null;
  safeRoute?: RouteSegment | null;
  compareRoutes?: boolean;
  destination: { latitude: number; longitude: number; name: string };
  onSpot?: () => void;
  spots?: CoolingSpot[];
};

const DEFAULT_LOCATION = { latitude: 37.5739, longitude: 127.0105 };

/** 실제 타일 지도와 경로/마커를 그리는 클라이언트 전용 지도입니다. */
export default function RealMap({ route, normalRoute, safeRoute, compareRoutes = false, destination, onSpot, spots = [] }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const onSpotRef = useRef(onSpot);
  const mapRef = useRef<import("leaflet").Map | null>(null);

  useEffect(() => {
    onSpotRef.current = onSpot;
  }, [onSpot]);

  useEffect(() => {
    let map: import("leaflet").Map | undefined;
    let cancelled = false;

    void import("leaflet").then((L) => {
      if (cancelled || !containerRef.current) return;
      const primaryRoute = route ?? normalRoute ?? safeRoute;
      const origin = primaryRoute?.origin ?? DEFAULT_LOCATION;
      const destinationPoint: [number, number] = [destination.latitude, destination.longitude];
      // 빠른 화면 전환 중 이전 지도 애니메이션이 남으면 Leaflet 내부 위치값이
      // 제거된 map pane을 참조할 수 있어, 새 지도를 만들기 전에 확실히 정리한다.
      mapRef.current?.remove();
      mapRef.current = null;
      map = L.map(containerRef.current, {
        zoomControl: false,
        zoomAnimation: false,
        fadeAnimation: false,
        markerZoomAnimation: false,
      }).setView(destinationPoint, 16, { animate: false });
      mapRef.current = map;
      L.control.zoom({ position: "topright" }).addTo(map);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
        maxZoom: 19,
      }).addTo(map);

      const currentIcon = L.divIcon({ className: "leaflet-current-marker", html: "<span></span>", iconSize: [18, 18], iconAnchor: [9, 9] });
      const destinationIcon = L.divIcon({ className: "leaflet-destination-marker", html: "<span>방문지</span>", iconSize: [54, 28], iconAnchor: [10, 28] });
      const spotIcon = (type: CoolingSpot["type"]) => L.divIcon({
        className: `leaflet-spot-marker ${type === "PUBLIC" ? "public" : "company"}`,
        html: `<span>${type === "PUBLIC" ? "공" : "기"}</span>`,
        iconSize: [34, 34],
        iconAnchor: [17, 34],
      });

      L.marker([origin.latitude, origin.longitude], { icon: currentIcon }).addTo(map).bindTooltip("현재 위치");
      L.marker(destinationPoint, { icon: destinationIcon }).addTo(map).bindTooltip(destination.name);

      spots.forEach((spot) => {
        const marker = L.marker([spot.latitude, spot.longitude], { icon: spotIcon(spot.type) }).addTo(map!);
        marker.bindTooltip(spot.name, {
          permanent: true,
          direction: "top",
          offset: [0, -28],
          className: `cooling-spot-label ${spot.type === "PUBLIC" ? "public" : "company"}`,
        });
        marker.on("click", () => onSpotRef.current?.());
      });

      const normalPath = (compareRoutes ? normalRoute?.path : route?.path)?.map((point) => [point.latitude, point.longitude] as [number, number]) ?? [];
      const safePath = (compareRoutes ? safeRoute?.path : route?.routeType === "SAFE" ? route.path : undefined)?.map((point) => [point.latitude, point.longitude] as [number, number]) ?? [];
      const paths = [normalPath, safePath].filter((path) => path.length > 1);
      if (paths.length) {
        if (normalPath.length > 1) L.polyline(normalPath, { color: compareRoutes ? "#697586" : "#1766e8", weight: compareRoutes ? 5 : 6, opacity: 0.9 }).addTo(map);
        if (safePath.length > 1) L.polyline(safePath, { color: "#1766e8", weight: 6, opacity: 0.95 }).addTo(map);
        // 쉼터 전체를 bounds에 포함하면 지도가 지나치게 축소되므로
        // 처음에는 이동 경로와 방문지 주변만 보이도록 한다.
        map.fitBounds(L.latLngBounds(paths.flat()), { padding: [36, 36], maxZoom: 17, animate: false });
      } else {
        L.polyline([[origin.latitude, origin.longitude], destinationPoint], { color: "#727b87", weight: 5, dashArray: "8 8" }).addTo(map);
        map.fitBounds(L.latLngBounds([[origin.latitude, origin.longitude], destinationPoint]), { padding: [36, 36], maxZoom: 17, animate: false });
      }
    });

    return () => {
      cancelled = true;
      map?.remove();
      if (mapRef.current === map) mapRef.current = null;
    };
  }, [destination.latitude, destination.longitude, destination.name, route, normalRoute, safeRoute, compareRoutes, spots]);

  return <div ref={containerRef} className="real-map" aria-label="현재 위치와 방문지 지도" />;
}
