"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";
import { FALLBACK_PLAYER_CARD } from "@/lib/mockData";
import { getTeamColor } from "@/styles/tokens";
import LoadingSkeleton from "../ui/LoadingSkeleton";
import PlayerAnimation from "../dashboard/PlayerAnimation";
import TeamLogo from "../ui/TeamLogo";

interface PlayerStat {
  player_id: string;
  name: string;
  pos: string;
  pts: number;
  reb: number;
  ast: number;
  fgm?: number;
  fga?: number;
  stl?: number;
  blk?: number;
  plus_minus?: number;
  last5_pts: number[];
}

interface PlayerModalProps {
  player: PlayerStat;
  game: any;
  onClose: () => void;
}

export default function PlayerModal({ player, game, onClose }: PlayerModalProps) {
  const [card, setCard] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // FIX: useEffect (not useState) for async side-effects — prevents infinite re-renders
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setCard(null);

    const fetchCard = async () => {
      try {
        const res = await api.post("/api/player-card", {
          player_id: player.player_id,
          player_name: player.name,
          season_avg: { pts: player.pts, reb: player.reb, ast: player.ast },
          last5: player.last5_pts,
          opponent: (player as any).side === "away" ? game.home_team_name : game.away_team_name,
          game_id: game.game_id,
        });
        if (!cancelled) setCard(res.data);
      } catch {
        if (!cancelled) setCard(FALLBACK_PLAYER_CARD);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchCard();
    return () => { cancelled = true; };
  }, [player.player_id]);

  const trendStyles: Record<string, string> = {
    hot: "bg-success/20 text-success border border-success/30",
    cold: "bg-danger/20 text-danger border border-danger/30",
    neutral: "bg-surfaceHigh text-secondary border border-border",
  };
  const trendLabel: Record<string, string> = {
    hot: "🔥 Hot Streak",
    cold: "🥶 Cold Streak",
    neutral: "— Neutral",
  };

  const trend = card?.trend || "neutral";
  const seasonAvg = player.pts;
  const teamColor = getTeamColor(game.home_team_abbr).primary;
  const fgPct =
    player.fgm != null && player.fga && player.fga > 0
      ? `${((player.fgm / player.fga) * 100).toFixed(1)}%`
      : null;

  return (
    <div
      className="fixed inset-0 bg-black/75 backdrop-blur-sm z-[60] flex items-start justify-center pt-16 px-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-label={`${player.name} AI player card`}
    >
      <div
        className="bg-surface rounded-2xl max-w-xl w-full p-6 max-h-[80vh] overflow-y-auto border border-border"
        style={{ animation: "fadeSlideUp 0.22s ease-out" }}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <TeamLogo abbr={game.home_team_abbr} size={40} />
            <div>
              <h2 className="text-xl font-bold text-primary">{player.name}</h2>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span className="bg-surfaceHigh text-secondary text-xs px-2 py-0.5 rounded font-mono">
                  {player.pos}
                </span>
                <span
                  className="text-xs font-semibold"
                  style={{ color: teamColor }}
                >
                  {game.home_team_abbr}
                </span>
                <span className="text-secondary text-xs">
                  {player.pts}/{player.reb}/{player.ast} avg
                </span>
                {fgPct && (
                  <span className="text-dim text-xs">{fgPct} FG</span>
                )}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close player card"
            className="w-8 h-8 rounded-full bg-surfaceHigh hover:bg-border flex items-center justify-center text-secondary hover:text-primary transition-colors flex-shrink-0"
          >
            ✕
          </button>
        </div>

        {/* Player animation banner */}
        <div
          className="rounded-xl overflow-hidden mb-4"
          style={{ height: "120px", background: `${teamColor}14` }}
        >
          <PlayerAnimation teamColor={teamColor} className="h-full w-full" />
        </div>

        {loading ? (
          <div className="space-y-3">
            <LoadingSkeleton lines={3} />
          </div>
        ) : (
          <>
            {/* Tonight's Projection */}
            {card?.projection && (
              <div className="bg-surfaceHigh rounded-xl p-4 mb-4 border border-border">
                <p className="text-dim text-[10px] uppercase tracking-widest mb-2">
                  Tonight's Projection
                </p>
                <div className="flex gap-6">
                  <ProjStat label="PTS" value={card.projection.pts} color={teamColor} />
                  <ProjStat label="REB" value={card.projection.reb} />
                  <ProjStat label="AST" value={card.projection.ast} />
                  {player.plus_minus != null && (
                    <ProjStat
                      label="+/-"
                      value={player.plus_minus > 0 ? `+${player.plus_minus}` : String(player.plus_minus)}
                      color={player.plus_minus > 0 ? "#27AE60" : player.plus_minus < 0 ? "#E74C3C" : undefined}
                    />
                  )}
                </div>
              </div>
            )}

            {/* Trend badge */}
            <span
              className={`inline-block px-3 py-1 rounded-full text-sm font-medium mb-4 ${trendStyles[trend]}`}
            >
              {trendLabel[trend]}
            </span>

            {/* Scouting report */}
            {card?.report && (
              <div className="p-4 bg-surfaceHigh rounded-xl italic text-secondary leading-relaxed text-sm mb-4 border-l-2 border-orange/40">
                {card.report}
              </div>
            )}

            {/* Last 5 games */}
            {player.last5_pts && player.last5_pts.length > 0 && (
              <div className="mb-4">
                <p className="text-dim text-xs uppercase tracking-wider mb-2">
                  Last 5 Games
                </p>
                <div className="flex gap-2">
                  {player.last5_pts.map((pts, i) => {
                    const isHot = pts >= seasonAvg;
                    return (
                      <div
                        key={i}
                        className={`w-9 h-9 rounded-full font-mono text-xs flex items-center justify-center font-bold ${
                          isHot
                            ? "bg-success/20 text-success"
                            : "bg-danger/20 text-danger"
                        }`}
                      >
                        {pts}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Extra stats row */}
            {(player.stl != null || player.blk != null) && (
              <div className="flex gap-3 pt-3 border-t border-border">
                {player.stl != null && (
                  <ExtraStat label="STL" value={player.stl} />
                )}
                {player.blk != null && (
                  <ExtraStat label="BLK" value={player.blk} />
                )}
                {fgPct && <ExtraStat label="FG%" value={fgPct} />}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function ProjStat({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="text-center">
      <div
        className="text-xl font-black font-mono"
        style={{ color: color ?? "#F0F0F0" }}
      >
        {value}
      </div>
      <div className="text-[10px] text-dim uppercase tracking-wider">{label}</div>
    </div>
  );
}

function ExtraStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="text-center bg-surfaceHigh rounded-lg px-3 py-1.5">
      <div className="font-mono text-sm font-bold text-primary">{value}</div>
      <div className="text-[9px] text-dim uppercase tracking-wider">{label}</div>
    </div>
  );
}
