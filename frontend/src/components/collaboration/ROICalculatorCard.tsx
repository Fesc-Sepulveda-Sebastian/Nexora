import React, { useState } from 'react';
import { ROICalculatorResult } from '../../types';
import { api } from '../../services/api';
import { Calculator, TrendingUp, AlertCircle, Info, DollarSign } from 'lucide-react';

interface ROICalculatorCardProps {
  initialCost?: number;
  initialBenefit?: number;
}

export const ROICalculatorCard: React.FC<ROICalculatorCardProps> = ({
  initialCost = 450000,
  initialBenefit = 1350000
}) => {
  const [totalCost, setTotalCost] = useState<number>(initialCost);
  const [attributableBenefit, setAttributableBenefit] = useState<number>(initialBenefit);
  const [result, setResult] = useState<ROICalculatorResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleCalculate = async () => {
    setErrorMsg(null);
    if (!totalCost || totalCost <= 0) {
      setErrorMsg('RN-04: El costo total declarado debe ser estrictamente mayor a cero.');
      return;
    }

    setLoading(true);
    try {
      const { data } = await api.request<ROICalculatorResult>('/collaborations/roi-calculator', {
        method: 'POST',
        body: {
          total_cost: Number(totalCost),
          attributable_benefit: Number(attributableBenefit),
          currency: 'COP',
          cost_source: 'Presupuesto acordado en Nexora',
          benefit_source: 'Ventas atribuidas con código promocional'
        }
      });
      setResult(data);
    } catch (e: any) {
      setErrorMsg(e.message || 'Error al calcular ROI estimado');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl text-slate-100">
      <div className="flex items-center gap-2 text-brand-400 font-bold text-base mb-3">
        <Calculator className="w-5 h-5" />
        <h3>Calculadora de ROI Estimado (RN-04)</h3>
      </div>

      <p className="text-xs text-slate-400 mb-4">
        Según la regla <strong>RN-04</strong>, el retorno se calcula a partir de costos e ingresos declarados por la marca.
      </p>

      {errorMsg && (
        <div className="p-3 mb-4 rounded-xl bg-rose-950/70 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Input controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        <div>
          <label className="text-[11px] font-semibold text-slate-300 uppercase block mb-1">
            Costo Total Declarado (COP) *
          </label>
          <div className="relative">
            <span className="absolute left-3 top-3 text-slate-500 text-xs">$</span>
            <input
              type="number"
              min="1"
              value={totalCost}
              onChange={(e) => setTotalCost(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-7 pr-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500 min-h-touch"
            />
          </div>
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-300 uppercase block mb-1">
            Beneficio Atribuible (COP) *
          </label>
          <div className="relative">
            <span className="absolute left-3 top-3 text-slate-500 text-xs">$</span>
            <input
              type="number"
              value={attributableBenefit}
              onChange={(e) => setAttributableBenefit(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-7 pr-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500 min-h-touch"
            />
          </div>
        </div>
      </div>

      <button
        onClick={handleCalculate}
        disabled={loading}
        className="w-full bg-brand-600 hover:bg-brand-500 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 min-h-touch transition-all shadow-md shadow-brand-500/20 active:scale-95"
      >
        <TrendingUp className="w-4 h-4" />
        <span>{loading ? 'Calculando...' : 'Calcular ROI Estimado'}</span>
      </button>

      {/* Result Display */}
      {result && (
        <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-emerald-900/40 animate-fade-in space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-semibold uppercase">Retorno Estimado (ROI):</span>
            <span className="text-2xl font-black text-emerald-400">
              +{result.roi_percentage}%
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-800">
            <div>
              <span className="text-[10px] text-slate-400 block">Beneficio Neto:</span>
              <span className="text-white font-bold">${result.net_profit.toLocaleString()} COP</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block">Fecha de Estimación:</span>
              <span className="text-white font-bold">{new Date(result.calculated_at_utc).toLocaleDateString()}</span>
            </div>
          </div>

          <div className="pt-2 text-[10px] text-amber-300/80 flex items-start gap-1.5 border-t border-slate-800/60">
            <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span>{result.disclaimer}</span>
          </div>
        </div>
      )}
    </div>
  );
};
