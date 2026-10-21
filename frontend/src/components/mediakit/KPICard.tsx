import React from 'react';
import { ShieldCheck, Info, Clock, Calculator } from 'lucide-react';

interface KPICardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  sourceType: 'API_CONECTADA' | 'DECLARADO' | 'NO_DISPONIBLE';
  captureDateUtc?: string;
  period?: string;
  formulaDetails?: {
    interactions: number;
    reach: number;
    formula: string;
  };
}

export const KPICard: React.FC<KPICardProps> = ({
  label,
  value,
  subtitle,
  sourceType,
  captureDateUtc,
  period,
  formulaDetails
}) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 sm:p-5 flex flex-col justify-between shadow-lg relative overflow-hidden group">
      <div>
        {/* Source Badge (RN-03 Trazabilidad) */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
            {label}
          </span>

          {sourceType === 'API_CONECTADA' ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
              <ShieldCheck className="w-3 h-3 text-emerald-400 shrink-0" />
              API Oficial Verificada
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-950/80 text-amber-400 border border-amber-800/60">
              <Info className="w-3 h-3 text-amber-400 shrink-0" />
              Dato Declarado (RN-03)
            </span>
          )}
        </div>

        {/* Large Value */}
        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            {value}
          </span>
          {subtitle && (
            <span className="text-xs text-slate-400 font-medium">{subtitle}</span>
          )}
        </div>

        {/* Formula breakdown for engagement (RN-03) */}
        {formulaDetails && (
          <div className="mt-2.5 p-2 rounded-xl bg-slate-950/70 border border-slate-800/80 text-[11px] text-slate-300 space-y-1">
            <div className="flex items-center gap-1 text-brand-300 font-semibold">
              <Calculator className="w-3 h-3" />
              <span>Fórmula Transparente (RN-03):</span>
            </div>
            <div className="text-slate-400 font-mono text-[10px]">
              {formulaDetails.formula}
            </div>
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>Interacciones: {formulaDetails.interactions.toLocaleString()}</span>
              <span>Alcance: {formulaDetails.reach.toLocaleString()}</span>
            </div>
          </div>
        )}
      </div>

      {/* Footer capture timestamp & period */}
      <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3 text-slate-400" />
          {period || 'Últimos 30 días'}
        </span>
        {captureDateUtc && (
          <span>Captura: {new Date(captureDateUtc).toLocaleDateString()}</span>
        )}
      </div>
    </div>
  );
};
