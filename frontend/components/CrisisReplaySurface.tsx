"use client";

import { useEffect, useMemo, useState } from "react";
import { geoNaturalEarth1, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { FeatureCollection, GeometryObject } from "geojson";
import type { GeometryCollection, Topology } from "topojson-specification";
import worldTopology from "world-atlas/countries-110m.json";

import type { CrisisReplay, ReplayRoute } from "../lib/api";

const MAP_WIDTH = 960;
const MAP_HEIGHT = 430;

const topology = worldTopology as unknown as Topology<{ countries: GeometryCollection }>;
const countries = feature(topology, topology.objects.countries) as FeatureCollection<GeometryObject>;

function percentage(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function compactNumber(value: number): string {
  if (value === 0) return "0 bpd";
  return `${new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 0 }).format(value)} bpd`;
}

function sourceClass(value: string): string {
  return value.toLowerCase().replaceAll(" ", "-");
}

function routeIsSelected(route: ReplayRoute, selectedRoutes: string[]): boolean {
  const origin = route.name.split(" -> ")[0]?.toLowerCase() ?? route.name.toLowerCase();
  return selectedRoutes.some((selected) => selected.toLowerCase().startsWith(origin));
}

type CrisisReplaySurfaceProps = {
  replay: CrisisReplay;
  selectedRoutes: string[];
  onUseReplay: (signal: string) => void;
};

export default function CrisisReplaySurface({ replay, selectedRoutes, onUseReplay }: CrisisReplaySurfaceProps) {
  const [activeSequence, setActiveSequence] = useState(replay.evidence[0]?.sequence ?? 0);
  const projection = useMemo(
    () => geoNaturalEarth1().fitExtent([[14, 16], [MAP_WIDTH - 14, MAP_HEIGHT - 16]], countries),
    [],
  );
  const path = useMemo(() => geoPath(projection), [projection]);
  const activeEvidence = replay.evidence.find((event) => event.sequence === activeSequence) ?? replay.evidence[0] ?? null;

  useEffect(() => {
    setActiveSequence(replay.evidence[0]?.sequence ?? 0);
  }, [replay]);

  return (
    <section className="context-surface crisis-replay" aria-labelledby="crisis-replay-title">
      <div className="section-heading replay-heading">
        <div>
          <p className="label">SOURCE-LABELLED CRISIS REPLAY</p>
          <h3 id="crisis-replay-title">{replay.title}</h3>
          <p>{replay.disclaimer}</p>
        </div>
        <span className="badge">Offline replay · {replay.chokepoint}</span>
      </div>

      <div className="replay-layout">
        <div className="replay-map-panel">
          <div className="replay-map-labels">
            <span>Decision geography</span>
            <small>World basemap · replay routes are not live vessel tracks</small>
          </div>
          <svg className="replay-map" viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`} role="img" aria-labelledby="replay-map-title replay-map-description">
            <title id="replay-map-title">Route replay for the Strait of Hormuz disruption scenario</title>
            <desc id="replay-map-description">A projected world map shows one exposed Persian Gulf route and two simulated alternative routes to Jamnagar.</desc>
            <rect className="replay-ocean" x="0" y="0" width={MAP_WIDTH} height={MAP_HEIGHT} rx="8" />
            <g className="replay-land" aria-hidden="true">
              {countries.features.map((country, index) => {
                const countryPath = path(country);
                return countryPath ? <path d={countryPath} key={country.id ?? index} /> : null;
              })}
            </g>
            <g className="replay-routes" aria-hidden="true">
              {replay.routes.map((route) => {
                const routePath = path({ type: "LineString", coordinates: route.coordinates });
                const selected = routeIsSelected(route, selectedRoutes);
                return routePath ? <path className={`replay-route is-${route.status.toLowerCase()} ${selected ? "is-selected" : ""}`} d={routePath} key={route.route_id} /> : null;
              })}
            </g>
            <g className="replay-locations" aria-hidden="true">
              {replay.locations.map((location) => {
                const point = projection(location.coordinates);
                return point ? <g className={`replay-location is-${location.kind.toLowerCase()}`} key={location.location_id} transform={`translate(${point[0]} ${point[1]})`}><circle r={location.kind === "CHOKEPOINT" ? 6 : 4} /><text x="9" y="4">{location.name}</text></g> : null;
              })}
            </g>
          </svg>
          <div className="replay-map-legend" aria-label="Map legend">
            <span><i className="legend-line is-exposed" /> Exposed replay route</span>
            <span><i className="legend-line is-alternative" /> Simulated alternative</span>
            <span><i className="legend-point" /> Seeded location context</span>
          </div>
        </div>

        <aside className="replay-evidence-panel" aria-label="Replay evidence sequence">
          <p className="label">REPLAY SEQUENCE</p>
          <ol className="replay-timeline">
            {replay.evidence.map((event) => <li key={event.sequence}><button type="button" className={event.sequence === activeSequence ? "is-active" : ""} onClick={() => setActiveSequence(event.sequence)}><span>{String(event.sequence).padStart(2, "0")}</span><strong>{event.label}</strong><small className={`source-chip is-${sourceClass(event.source_status)}`}>{event.source_status}</small></button></li>)}
          </ol>
          {activeEvidence && <article className="replay-evidence-detail" aria-live="polite"><div><span className={`source-chip is-${sourceClass(activeEvidence.source_status)}`}>{activeEvidence.source_status}</span><strong>{percentage(activeEvidence.reliability)} reliability</strong></div><p>{activeEvidence.summary}</p><small>{activeEvidence.impact}</small></article>}
        </aside>
      </div>

      <div className="replay-route-ledger" aria-label="Route comparison for this replay">
        {replay.routes.map((route) => {
          const selected = routeIsSelected(route, selectedRoutes);
          return <article className={`${route.status === "EXPOSED" ? "is-exposed" : "is-alternative"} ${selected ? "is-selected" : ""}`} key={route.route_id}><div><span className="route-state">{route.status === "EXPOSED" ? "Exposed" : selected ? "Selected in current portfolio" : "Alternative"}</span><strong>{route.name}</strong><small>{route.note}</small></div><dl><div><dt>Transit</dt><dd>{route.transit_days} days</dd></div><div><dt>Capacity</dt><dd>{compactNumber(route.available_volume_bpd)}</dd></div><div><dt>Route risk</dt><dd>{percentage(route.route_risk_score)}</dd></div></dl></article>;
        })}
      </div>

      <div className="replay-action-row"><p>{replay.replay_signal}</p><button type="button" className="secondary-button" onClick={() => onUseReplay(replay.replay_signal)}>Use simulated signal in a new case</button></div>
    </section>
  );
}
