import React from 'react';
import { Campaign } from '../../types';
import { Calendar, DollarSign, Package, CheckCircle, ArrowRight } from 'lucide-react';

interface CampaignCardProps {
  campaign: Campaign;
  onSelect: (campaignId: string) => void;
}

export const CampaignCard: React.FC<CampaignCardProps> = ({ campaign, onSelect }) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 sm:p-5 flex flex-col justify-between hover:border-brand-500/50 transition-all duration-300 shadow-lg group">
      <div>
        {/* Header: Niche Pill + Status */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-brand-500/15 text-brand-300 border border-brand-500/30">
            {campaign.niche}
          </span>
          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md ${
            campaign.status === 'Publicada' 
              ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40' 
              : 'bg-amber-950/80 text-amber-400 border border-amber-800/40'
          }`}>
            {campaign.status}
          </span>
        </div>

        {/* Title & Objective */}
        <h3 className="text-base sm:text-lg font-bold text-white group-hover:text-brand-300 transition-colors line-clamp-1">
          {campaign.title}
        </h3>
        <p className="text-xs text-slate-400 mt-1 line-clamp-2">
          {campaign.objective}
        </p>

        {/* Highlights: Compensation & Deliverables */}
        <div className="grid grid-cols-2 gap-2 my-3 p-2.5 rounded-xl bg-slate-950/70 border border-slate-800/80 text-xs">
          <div>
            <span className="text-[10px] text-slate-400 block font-medium">Presupuesto / Canje</span>
            <span className="text-white font-extrabold flex items-center gap-0.5">
              <DollarSign className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              {campaign.compensation_type === 'canje' ? (
                'Canje VIP'
              ) : (
                `$${Number(campaign.budget || 0).toLocaleString()} COP`
              )}
            </span>
          </div>

          <div>
            <span className="text-[10px] text-slate-400 block font-medium">Entregables</span>
            <span className="text-white font-extrabold flex items-center gap-1">
              <Package className="w-3.5 h-3.5 text-brand-400 shrink-0" />
              {campaign.deliverables && campaign.deliverables.length > 0 
                ? `${campaign.deliverables.length} formato(s)` 
                : 'A convenir'}
            </span>
          </div>
        </div>
      </div>

      {/* CTA Button */}
      <div className="mt-2 pt-2 border-t border-slate-800/80">
        <button
          onClick={() => onSelect(campaign.id)}
          className="w-full bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs py-3 rounded-xl min-h-touch flex items-center justify-center gap-2 transition-all shadow-md active:scale-95"
        >
          <span>Ver Campaña & Postular</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
