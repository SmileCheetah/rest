"use client";

import { useEffect, useRef } from "react";
import type { CoolingSpot, RouteSegment } from "@/types/api";
import "leaflet/dist/leaflet.css";

type Props = {
  route?: RouteSegment | null;
  destination: { latitude: number; longitude: number; name: string };
  onSpot?: () => void;
  spots?: CoolingSpot[];
};

const DEFAULT_LOCATION = { latitude: 37.5739, longitude: 127.0105 };

/** 실제 타일 지도와 경로/마커를 그리는 클라이언트 전용 지도입니다. */
export default function RealMap({ route, destination, onSpot, spots = [] }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const onSpotRef = useRef(onSpot);

  useEffect(() => {
    onSpotRef.current = onSpot;
  }, [onSpot]);

  useEffect(() => {
    let map: import("leaflet").Map | undefined;
    let cancelled = false;

    void import("leaflet").then((L) => {
      if (cancelled || !containerRef.current) return;
      const origin = route?.origin ?? DEFAULT_LOCATION;
      const destinationPoint: [number, number] = [destination.latitude, destination.longitude];
      map = L.map(containerRef.current, { zoomControl: false }).setView(destinationPoint, 16);
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
        marker.bindTooltip(`${spot.type === "PUBLIC" ? "공공 무더위쉼터" : "기업 쿨링스팟"} · ${spot.name}`);
        marker.on("click", () => onSpotRef.current?.());
      });

      const path = route?.path?.map((point) => [point.latitude, point.longitude] as [number, number]) ?? [];
      if (path.length > 1) {
        L.polyline(path, { color: "#1766e8", weight: 6, opacity: 0.9 }).addTo(map);
        map.fitBounds(L.latLngBounds(path), { padding: [36, 36] });
      } else {
        L.polyline([[origin.latitude, origin.longitude], destinationPoint], { color: "#727b87", weight: 5, dashArray: "8 8" }).addTo(map);
        map.fitBounds(L.latLngBounds([[origin.latitude, origin.longitude], destinationPoint]), { padding: [36, 36] });
      }
    });

    return () => {
      cancelled = true;
      map?.remove();
    };
  }, [destination.latitude, destination.longitude, destination.name, route, spots]);

  return <div ref={containerRef} className="real-map" aria-label="현재 위치와 방문지 지도" />;
}
