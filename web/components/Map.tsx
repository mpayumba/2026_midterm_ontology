"use client";

import Map, { Layer, Marker, Source } from "react-map-gl/maplibre";
import type { MapLayerMouseEvent } from "react-map-gl/maplibre";
import type { HouseFCT, StatesFCT } from "@/lib/schema";

export const KIND_COLORS: Record<string, string> = {
  regular: "#64748b",
  open: "#7c3aed",
  special: "#d97706",
};

const senateFillColor = [
  "match",
  ["get", "senate_kind"],
  "special", KIND_COLORS.special,
  "open", KIND_COLORS.open,
  "regular", KIND_COLORS.regular,
  "#000000",
] as never;

const houseFillColor = [
  "match",
  ["get", "contest_kind"],
  "special", KIND_COLORS.special,
  "open", KIND_COLORS.open,
  KIND_COLORS.regular,
] as never;

interface Props {
  houseFC: HouseFCT;
  statesFC: StatesFCT;
  showHouse: boolean;
  showSenate: boolean;
  marker: { lng: number; lat: number } | null;
  onPick: (lng: number, lat: number) => void;
}

export default function ContestMap({
  houseFC,
  statesFC,
  showHouse,
  showSenate,
  marker,
  onPick,
}: Props) {
  const handleClick = (e: MapLayerMouseEvent) => {
    onPick(e.lngLat.lng, e.lngLat.lat);
  };

  return (
    <Map
      initialViewState={{ longitude: -96.5, latitude: 38.5, zoom: 3.6 }}
      mapStyle="https://demotiles.maplibre.org/style.json"
      onClick={handleClick}
      cursor="crosshair"
      style={{ width: "100%", height: "100%" }}
    >
      {/* Senate layer: states shaded only where a 2026 contest exists */}
      <Source id="states" type="geojson" data={statesFC as never}>
        <Layer
          id="senate-fill"
          type="fill"
          filter={["get", "has_2026_senate_contest"]}
          layout={{ visibility: showSenate ? "visible" : "none" }}
          paint={{ "fill-color": senateFillColor, "fill-opacity": 0.22 }}
        />
        <Layer
          id="senate-outline"
          type="line"
          layout={{ visibility: showSenate ? "visible" : "none" }}
          paint={{ "line-color": "#94a3b8", "line-width": 0.6 }}
        />
      </Source>

      {/* House layer: district choropleth-outline, color = contest kind */}
      <Source id="districts" type="geojson" data={houseFC as never}>
        <Layer
          id="house-fill"
          type="fill"
          layout={{ visibility: showHouse ? "visible" : "none" }}
          paint={{ "fill-color": houseFillColor, "fill-opacity": 0.08 }}
        />
        <Layer
          id="house-outline"
          type="line"
          layout={{ visibility: showHouse ? "visible" : "none" }}
          paint={{
            "line-color": houseFillColor,
            "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.4, 8, 1.4] as never,
            "line-opacity": 0.8,
          }}
        />
      </Source>

      {marker && (
        <Marker longitude={marker.lng} latitude={marker.lat} anchor="bottom">
          <div style={{ fontSize: 22, lineHeight: 1 }}>📍</div>
        </Marker>
      )}
    </Map>
  );
}
