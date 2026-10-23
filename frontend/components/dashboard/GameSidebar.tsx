"use client";

import { useState } from "react";
import TeamLogo from "@/components/ui/TeamLogo";
import { getTeamColor } from "@/styles/tokens";

interface Game {
  game_id: string;
  home_team_name: string;
  home_team_abbr: string;
  home_score: number | null;
  away_team_name: string;
  away_team_abbr: string;
  away_score: number | null;
  status: string;
  quarter: number | null;
  clock: string | null;
  tipoff_time: string | null;
  is_demo?: boolean;
}

interface GameSidebarProps {
  games: Game[];
  selectedGame: Game | null;
  onSelectGame: (game: Game) => void;
  activeOverlay: string;
  onOverlayChange: (v: string) => void;
  hasPlayerData?: boolean;
}

type Filter = "all" | "live" | "final";

const overlayOptions = [
  { id: "none", label: "No Overlay" },
  { id: "rank", label: "📊 League Rank" },
  { id: "sparkline", label: "📈 Form" },
  { id: "matchup", label: "🆚 Matchup" },
];

export default function GameSidebar({
  games,
  selectedGame,
  onSelectGame,
  activeOverlay,
  onOverlayChange,
  hasPlayerData = true,
}: GameSidebarProps) {
  const [filter, setFilter] = useState<Filter>("all");

  const filtered = games.filter((g) => {
    if (filter === "live") return g.status === "live";
    if (filter === "final") return g.status === "final";
    return true;
  });

  const today = new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });

  return (
    <aside className="w-52 min-w-[13rem] flex-shrink-0 border-r border-border bg-surface flex flex-col overflow-hidden">
      {/* Date header */}
      <div className="px-3 pt-4 pb-2 border-b border-border">
        <p className="text-[10px] font-bold text-dim uppercase tracking-widest">
          Today · {today}
        </p>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 px-3 pt-3 pb-2">
        {(["all", "live", "final"] as Filter[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`flex-1 py-1 rounded-full text-[10px] font-semibold transition-all capitalize ${
              filter === f
                ? "bg-orange text-white"
                : "bg-surfaceHigh text-secondary hover:text-primary"
            }`}
          >
            {f === "live" ? (
              <span className="flex items-center justify-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-live" />
                Live
              </span>
            ) : (
              f.charAt(0).toUpperCase() + f.slice(1)
            )}
          </button>
        ))}
      </div>

      {/* Game list */}
      <div className="flex-1 overflow-y-auto px-3 space-y-2 py-2">
        {filtered.length === 0 && (
          <p className="text-dim text-xs text-center py-4">No games</p>
        )}
        {filtered.map((game) => (
          <SidebarGameItem
            key={game.game_id}
            game={game}
            isSelected={selectedGame?.game_id === game.game_id}
            onSelect={() => onSelectGame(game)}
          />
        ))}
      </div>

      {/* Stat overlay */}
      <div className="border-t border-border px-3 py-3">
        <p className="text-[9px] font-bold text-dim uppercase tracking-widest mb-2">
          Stat Overlay
        </p>
        <div className="flex flex-col gap-1">
          {overlayOptions.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => onOverlayChange(id)}
              disabled={!hasPlayerData && id !== "none"}
              title={!hasPlayerData && id !== "none" ? "Needs box score data" : undefined}
              className={`text-left px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
                !hasPlayerData && id !== "none"
                  ? "text-dim opacity-40 cursor-not-allowed"
                  : activeOverlay === id
                  ? "bg-orange text-white"
                  : "text-secondary hover:bg-surfaceHigh hover:text-primary"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {!hasPlayerData && (
          <p className="text-dim text-[10px] mt-2 leading-snug">
            Needs box score data. Pick the sample game to try overlays.
          </p>
        )}
      </div>
    </aside>
  );
}

function SidebarGameItem({
  game,
  isSelected,
  onSelect,
}: {
  game: Game;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const hasScore = game.home_score !== null && game.away_score !== null;
  const awayWins = (game.away_score ?? 0) > (game.home_score ?? 0);
  const homeWins = (game.home_score ?? 0) > (game.away_score ?? 0);
  const awayColor = getTeamColor(game.away_team_abbr).primary;
  const homeColor = getTeamColor(game.home_team_abbr).primary;

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-3 rounded-xl border transition-all duration-150 ${
        isSelected
          ? "border-orange bg-orange/5 shadow-[0_0_6px_rgba(232,119,34,0.2)]"
          : "border-border bg-surfaceHigh hover:border-border/60 hover:bg-border/30"
      }`}
    >
      {/* Status row */}
      <div className="flex items-center gap-1.5 mb-2">
        {game.is_demo && (
          <span className="text-orange text-[9px] font-bold tracking-wider uppercase">
            Sample game
          </span>
        )}
        {!game.is_demo && game.status === "live" && (
          <>
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-live" />
            <span className="text-success text-[9px] font-bold tracking-wider uppercase">
              LIVE Q{game.quarter} {game.clock}
            </span>
          </>
        )}
        {!game.is_demo && game.status === "final" && (
          <span className="text-dim text-[9px] font-semibold tracking-wider uppercase">
            Final
          </span>
        )}
        {game.status === "upcoming" && (
          <span className="text-warn text-[9px] font-semibold">
            {game.tipoff_time ?? "TBD"}
          </span>
        )}
      </div>

      {/* Away team */}
      <div className="flex items-center gap-1.5 mb-1">
        <TeamLogo abbr={game.away_team_abbr} size={18} />
        <span
          className="text-xs font-bold flex-1 text-left"
          style={{ color: awayWins ? awayColor : "#9A9A9A" }}
        >
          {game.away_team_abbr}
        </span>
        {hasScore && (
          <span
            className={`font-mono text-sm font-bold tabular-nums ${
              awayWins ? "text-primary" : "text-secondary"
            }`}
          >
            {game.away_score}
          </span>
        )}
      </div>

      {/* Home team */}
      <div className="flex items-center gap-1.5">
        <TeamLogo abbr={game.home_team_abbr} size={18} />
        <span
          className="text-xs font-bold flex-1 text-left"
          style={{ color: homeWins ? homeColor : "#9A9A9A" }}
        >
          {game.home_team_abbr}
        </span>
        {hasScore && (
          <span
            className={`font-mono text-sm font-bold tabular-nums ${
              homeWins ? "text-primary" : "text-secondary"
            }`}
          >
            {game.home_score}
          </span>
        )}
        {!hasScore && game.status === "upcoming" && (
          <span className="font-mono text-xs text-dim">–</span>
        )}
      </div>
    </button>
  );
}
