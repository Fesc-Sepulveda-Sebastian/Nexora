import React from 'react';
import { X, SlidersHorizontal, Check } from 'lucide-react';

interface FiltersState {
  niche: string;
  location: string;
  platform: string;
  minFollowers: number;
}

interface BottomSheetFiltersProps {
  isOpen: boolean;
  onClose: () => void;
  filters: FiltersState;
  onChange: (filters: FiltersState) => void;
  onApply: () => void;
  totalResultsCount: number;
}

export const BottomSheetFilters: React.FC<BottomSheetFiltersProps> = ({
  isOpen,
  onClose,
  filters,
  onChange,
  onApply,
  totalResultsCount
}) => {
  if (!isOpen) return null;

  const niches = ['Todos', 'Gastronomía', 'Fitness & Salud', 'Moda & Belleza', 'Tecnología', 'Turismo'];
  const locations = ['Todas', 'Cúcuta, Colombia', 'Bucaramanga, Colombia', 'Bogotá, Colombia'];
  const platforms = ['Todas', 'Instagram', 'TikTok', 'YouTube'];

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 backdrop-blur-sm animate-fade-in lg:hidden">
      <div 
        className="w-full max-h-[85vh] bg-slate-900 border-t border-slate-700/80 rounded-t-3xl p-6 shadow-2xl flex flex-col text-slate-100 overflow-y-auto"
        role="dialog"
        aria-label="Filtros de búsqueda"
      >
        {/* Header handle & close */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2 text-brand-400 font-bold text-base">
            <SlidersHorizontal className="w-5 h-5" />
            <span>Filtros de Búsqueda</span>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-full min-w-touch min-h-touch flex items-center justify-center"
            aria-label="Cerrar panel de filtros"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filter controls */}
        <div className="space-y-5 my-4">
          {/* Niche */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Nicho o Categoría
            </label>
            <div className="flex flex-wrap gap-2">
              {niches.map((n) => (
                <button
                  key={n}
                  onClick={() => onChange({ ...filters, niche: n === 'Todos' ? '' : n })}
                  className={`px-3 py-2 rounded-xl text-xs font-medium min-h-touch transition-all ${
                    (filters.niche === n || (n === 'Todos' && !filters.niche))
                      ? 'bg-brand-600 text-white font-bold shadow-md shadow-brand-500/20'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          {/* Location */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Ubicación Declarada (Local First)
            </label>
            <div className="flex flex-wrap gap-2">
              {locations.map((loc) => (
                <button
                  key={loc}
                  onClick={() => onChange({ ...filters, location: loc === 'Todas' ? '' : loc })}
                  className={`px-3 py-2 rounded-xl text-xs font-medium min-h-touch transition-all ${
                    (filters.location === loc || (loc === 'Todas' && !filters.location))
                      ? 'bg-brand-600 text-white font-bold'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {loc}
                </button>
              ))}
            </div>
          </div>

          {/* Platform */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Plataforma Social
            </label>
            <div className="flex flex-wrap gap-2">
              {platforms.map((p) => (
                <button
                  key={p}
                  onClick={() => onChange({ ...filters, platform: p === 'Todas' ? '' : p })}
                  className={`px-3 py-2 rounded-xl text-xs font-medium min-h-touch transition-all ${
                    (filters.platform === p || (p === 'Todas' && !filters.platform))
                      ? 'bg-brand-600 text-white font-bold'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-4 border-t border-slate-800">
          <button
            onClick={() => {
              onApply();
              onClose();
            }}
            className="w-full bg-brand-600 hover:bg-brand-500 text-white font-bold py-3.5 rounded-xl min-h-touch flex items-center justify-center gap-2 shadow-lg shadow-brand-500/25 transition-transform active:scale-95"
          >
            <Check className="w-5 h-5" />
            <span>Ver {totalResultsCount} Resultados</span>
          </button>
        </div>
      </div>
    </div>
  );
};
