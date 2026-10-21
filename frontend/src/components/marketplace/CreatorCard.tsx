import React from 'react';
import { CreatorRecommendation } from '../../types';
import { Star, MapPin, Sparkles, CheckCircle2 } from 'lucide-react';

interface CreatorCardProps {
  creator: CreatorRecommendation;
  onSelect: (creatorId: string) => void;
}

export const CreatorCard: React.FC<CreatorCardProps> = ({ creator, onSelect }) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 sm:p-5 flex flex-col justify-between hover:border-brand-500/50 transition-all duration-300 shadow-lg hover:shadow-brand-500/10 group">
      <div>
        {/* Top Header: Avatar + Info + Score */}
        <div className="flex items-start gap-3 sm:gap-4">
          <img
            src={creator.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80'}
            alt={creator.display_name}
            className="w-14 h-14 rounded-2xl object-cover border-2 border-brand-500/30 group-hover:border-brand-500 transition-colors shrink-0"
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-base font-bold text-white truncate group-hover:text-brand-300 transition-colors">
                {creator.display_name}
              </h3>
              {creator.total_score >= 80 && (
                <span className="shrink-0 flex items-center gap-1 bg-brand-500/20 text-brand-300 border border-brand-500/30 text-[10px] font-bold px-2 py-0.5 rounded-full">
                  <Sparkles className="w-3 h-3 text-amber-300" />
                  {creator.total_score}% Fit
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
              <span className="text-brand-400 font-semibold">{creator.niche}</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3 shrink-0" />
                <span className="truncate">{creator.location_declared}</span>
              </span>
            </div>

            {/* Bilateral Rating */}
            <div className="flex items-center gap-1 mt-1 text-xs text-amber-400">
              <Star className="w-3.5 h-3.5 fill-amber-400" />
              <span className="font-bold">{creator.average_rating.toFixed(1)}</span>
              <span className="text-slate-400 text-[11px]">(Reseñas verificadas)</span>
            </div>
          </div>
        </div>

        {/* Explainable Match Criteria (RF-26, RNF-15) */}
        {creator.matching_criteria && creator.matching_criteria.length > 0 && (
          <div className="mt-3.5 bg-slate-950/80 rounded-xl p-2.5 border border-slate-800/80">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1">
              Criterios de Afinidad Nexora (RF-26):
            </span>
            <div className="space-y-1">
              {creator.matching_criteria.slice(0, 2).map((crit, idx) => (
                <div key={idx} className="flex items-center gap-1.5 text-xs text-slate-300">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span className="truncate">{crit.detail}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Action CTA */}
      <div className="mt-4 pt-3 border-t border-slate-800/80">
        <button
          onClick={() => onSelect(creator.creator_id)}
          className="w-full bg-slate-800 hover:bg-brand-600 text-slate-200 hover:text-white font-semibold text-xs py-3 rounded-xl min-h-touch flex items-center justify-center gap-2 transition-all shadow-md active:scale-95"
        >
          Ver Media Kit Dinámico
        </button>
      </div>
    </div>
  );
};
