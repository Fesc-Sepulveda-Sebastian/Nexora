import React from 'react';
import { useOfflineSync } from '../../context/OfflineSyncContext';
import { GitCompare, CheckCircle2, Server, Smartphone, X } from 'lucide-react';

export const ConflictResolutionModal: React.FC = () => {
  const { conflict, resolveConflict } = useOfflineSync();

  if (!conflict) return null;

  const { localDraft, serverVersion, serverData } = conflict;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-amber-500/50 rounded-2xl max-w-2xl w-full p-6 shadow-2xl text-slate-100 overflow-hidden flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3 text-amber-400">
            <GitCompare className="w-6 h-6 shrink-0" />
            <h2 className="text-lg md:text-xl font-bold">Conflicto de Versión Detectado (HTTP 409)</h2>
          </div>
          <button 
            onClick={() => resolveConflict('keep_server')}
            className="text-slate-400 hover:text-slate-200 min-w-touch min-h-touch flex items-center justify-center"
            aria-label="Cerrar modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-slate-300 mt-3">
          La versión en el servidor fue modificada mientras editabas sin conexión. Para evitar pérdida de datos según <strong>RNF-14</strong> y <strong>RF-31</strong>, compara las versiones y selecciona cuál deseas conservar:
        </p>

        {/* Side by side comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-6 overflow-y-auto pr-1">
          {/* Server Version */}
          <div className="bg-slate-950/70 border border-brand-500/30 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-brand-400 font-semibold mb-2">
                <Server className="w-4 h-4" />
                <span>Versión del Servidor (v{serverVersion})</span>
              </div>
              <div className="space-y-2 text-xs text-slate-300">
                <p><strong>Título:</strong> {serverData.title || 'Sin título'}</p>
                <p><strong>Presupuesto:</strong> ${serverData.budget ? Number(serverData.budget).toLocaleString() : 0} COP</p>
                <p><strong>Objetivo:</strong> {serverData.objective || 'Sin objetivo'}</p>
              </div>
            </div>
            <button
              onClick={() => resolveConflict('keep_server')}
              className="mt-4 w-full bg-slate-800 hover:bg-slate-700 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 min-h-touch transition-colors text-sm"
            >
              <CheckCircle2 className="w-4 h-4 text-brand-400" />
              Conservar Versión Servidor
            </button>
          </div>

          {/* Local Draft Version */}
          <div className="bg-slate-950/70 border border-amber-500/30 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-amber-400 font-semibold mb-2">
                <Smartphone className="w-4 h-4" />
                <span>Tu Versión Local (Borrador)</span>
              </div>
              <div className="space-y-2 text-xs text-slate-300">
                <p><strong>Título:</strong> {localDraft.title}</p>
                <p><strong>Presupuesto:</strong> ${Number(localDraft.budget || 0).toLocaleString()} COP</p>
                <p><strong>Objetivo:</strong> {localDraft.objective || 'Sin objetivo'}</p>
              </div>
            </div>
            <button
              onClick={() => resolveConflict('keep_local')}
              className="mt-4 w-full bg-brand-600 hover:bg-brand-500 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 min-h-touch transition-colors text-sm shadow-lg shadow-brand-500/20"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-300" />
              Sobrescribir con Local
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
