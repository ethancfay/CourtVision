"use client";

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { MOCK_GAMES, MOCK_PLAYER_STATS } from "@/lib/mockData";
import { getTeamColor } from "@/styles/tokens";
import GameSidebar from "@/components/dashboard/GameSidebar";
import HeroGame from "@/components/dashboard/HeroGame";
import PlayerHighlightCard from "@/components/dashboard/PlayerHighlightCard";
import BoxScoreTable from "@/components/dashboard/BoxScoreTable";
import PlayerModal from "@/components/players/PlayerModal";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorBanner from "@/components/ui/ErrorBanner";

export default function DashboardPage() {
  const [selectedGame, setSelectedGame] = useState<any>(null);
  const [activeTeam, setActiveTeam] = useState<"home" | "away">("home");
  const [activeOverlay, setActiveOverlay] = useState("none");
  const [showFullBoxScore, setShowFullBoxScore] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<any>(null);

  const {
    data: games,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["games"],
    queryFn: async () => {
      try {
        const res = await api.get("/api/games");
        return res.data;
      } catch {
        return MOCK_GAMES;
      }
    },
    refetchInterval: 30000,
  });

  // Sample game with sample box score, so every feature can be tried even when
  // real games have no player data yet (box scores need a paid data plan).
  const DEMO_GAME = { ...MOCK_GAMES[0], status: "final", is_demo: true };
  const realGames = (games || []).filter((g: any) => !g.game_id?.startsWith("game_"));
  const displayGames = [DEMO_GAME, ...realGames];

  // Default to the sample game if nothing selected
  const currentGame = selectedGame ?? (displayGames[0] || null);

  const handleSelectGame = useCallback((game: any) => {
    setSelectedGame(game);
    setActiveTeam("home");
    setShowFullBoxScore(false);
    setSelectedPlayer(null);
  }, []);

  // Real games: live box score from the backend (ESPN public data).
  const isRealGame = !!currentGame && !currentGame.is_demo;
  const { data: box } = useQuery({
    queryKey: ["boxscore", currentGame?.game_id],
    queryFn: async () => {
      try {
        const res = await api.get("/api/boxscore", {
          params: { home: currentGame.home_team_abbr, away: currentGame.away_team_abbr },
        });
        return res.data;
      } catch {
        return null;
      }
    },
    enabled: isRealGame && currentGame?.status !== "upcoming",
    refetchInterval: currentGame?.status === "live" ? 30000 : false,
  });

  // Player data for selected game
  const allPlayers: any[] = !currentGame
    ? []
    : currentGame.is_demo
      ? MOCK_PLAYER_STATS.filter((p) => p.game_id === currentGame.game_id)
      : box?.players ?? [];
  const homePlayers = currentGame?.is_demo
    ? allPlayers.filter((p) => p.team_id === currentGame?.home_team_id)
    : allPlayers.filter((p) => p.side === "home");
  const awayPlayers = currentGame?.is_demo
    ? allPlayers.filter((p) => p.team_id === currentGame?.away_team_id)
    : allPlayers.filter((p) => p.side === "away");

  const activeTeamAbbr =
    activeTeam === "home"
      ? currentGame?.home_team_abbr
      : currentGame?.away_team_abbr;

  const displayedPlayers = activeTeam === "home" ? homePlayers : awayPlayers;

  const topPlayers = [...displayedPlayers]
    .sort((a, b) => b.pts - a.pts)
    .slice(0, 4);

  return (
    // Full-height layout: viewport minus combined header (84px)
    <div className="flex" style={{ height: "calc(100vh - 84px)" }}>
      {/* ── LEFT SIDEBAR ─────────────────────────────────── */}
      {!isLoading && !isError && (
        <GameSidebar
          games={displayGames}
          selectedGame={currentGame}
          onSelectGame={handleSelectGame}
          activeOverlay={activeOverlay}
          onOverlayChange={(v: string) => {
            setActiveOverlay(v);
            if (v !== "none") setShowFullBoxScore(true);
          }}
          hasPlayerData={!!currentGame?.is_demo}
        />
      )}

      {/* ── MAIN CONTENT ────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <LoadingSpinner />
          </div>
        ) : isError ? (
          <div className="p-6">
            <ErrorBanner message="Failed to load games." onRetry={refetch} />
          </div>
        ) : !currentGame ? (
          <div className="flex items-center justify-center h-full text-secondary text-sm">
            No games today. Check back at tip-off.
          </div>
        ) : (
          <div className="p-4 lg:p-6 max-w-4xl">
            {currentGame.is_demo && (
              <div className="mb-3 px-3 py-2 rounded-lg border border-orange/40 bg-orange/10 text-orange text-xs font-semibold">
                Sample data: this is a demo game with sample stats so you can try every feature.
                Real games are listed below it.
              </div>
            )}

            {/* Hero game */}
            <HeroGame
              game={currentGame}
              homePlayers={homePlayers}
              awayPlayers={awayPlayers}
            />

            {/* Team tabs */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex gap-2">
                <TeamTab
                  abbr={currentGame.home_team_abbr}
                  label={`${currentGame.home_team_abbr} (${homePlayers.length})`}
                  isActive={activeTeam === "home"}
                  onClick={() => setActiveTeam("home")}
                />
                <TeamTab
                  abbr={currentGame.away_team_abbr}
                  label={`${currentGame.away_team_abbr} (${awayPlayers.length})`}
                  isActive={activeTeam === "away"}
                  onClick={() => setActiveTeam("away")}
                />
              </div>
              <span className="text-dim text-xs">
                {topPlayers.length > 0
                  ? "Click a card for AI scouting"
                  : "No player data yet"}
              </span>
            </div>

            {/* Player highlight cards */}
            {topPlayers.length > 0 ? (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
                {topPlayers.map((player) => (
                  <PlayerHighlightCard
                    key={player.player_id}
                    player={player}
                    teamAbbr={activeTeamAbbr ?? ""}
                    onClick={() => setSelectedPlayer(player)}
                  />
                ))}
              </div>
            ) : (
              <div className="text-secondary text-sm text-center py-10 mb-5 border border-dashed border-border rounded-xl">
                {currentGame.status === "upcoming"
                  ? "Box score appears once the game tips off."
                  : "Box score data not yet available for this game."}
              </div>
            )}

            {/* Full box score toggle */}
            <button
              onClick={() => setShowFullBoxScore((v) => !v)}
              className="w-full py-2.5 border border-border rounded-xl text-secondary text-sm hover:border-orange/40 hover:text-orange transition-all mb-4 flex items-center justify-center gap-2"
            >
              <span>
                {showFullBoxScore ? "▲ Hide" : "▼ View"} Full Box Score
              </span>
            </button>

            {showFullBoxScore && displayedPlayers.length > 0 && (
              <div className="bg-surface border border-border rounded-xl overflow-hidden mb-4">
                <BoxScoreTable
                  players={displayedPlayers}
                  activeOverlay={activeOverlay as any}
                  game={currentGame}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── PLAYER MODAL ────────────────────────────────── */}
      {selectedPlayer && currentGame && (
        <PlayerModal
          player={selectedPlayer}
          game={currentGame}
          onClose={() => setSelectedPlayer(null)}
        />
      )}
    </div>
  );
}

/* ── Team tab pill ──────────────────────────────────────── */
function TeamTab({
  abbr,
  label,
  isActive,
  onClick,
}: {
  abbr: string;
  label: string;
  isActive: boolean;
  onClick: () => void;
}) {
  const color = getTeamColor(abbr).primary;
  return (
    <button
      onClick={onClick}
      className="px-4 py-1.5 rounded-lg text-sm font-semibold transition-all"
      style={
        isActive
          ? { backgroundColor: color, color: "#fff" }
          : {
              backgroundColor: "#242424",
              color: "#9A9A9A",
            }
      }
    >
      {label}
    </button>
  );
}
