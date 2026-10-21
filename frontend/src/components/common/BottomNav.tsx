import React from 'react';
import { Home, PlusCircle, MessageSquare, UserCheck } from 'lucide-react';

interface BottomNavProps {
  currentView: string;
  onNavigate: (view: string) => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ currentView, onNavigate }) => {
  return (
    <div className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-slate-950/95 backdrop-blur-lg border-t border-slate-800/80 px-2 py-1 safe-area-pb">
      <div className="flex items-center justify-around">
        {/* Item 1: Marketplace */}
        <button
          onClick={() => onNavigate('marketplace')}
          className={`flex flex-col items-center justify-center flex-1 min-h-[48px] min-w-touch py-1 rounded-xl transition-all ${
            currentView === 'marketplace' ? 'text-brand-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
          aria-label="Ir a Marketplace"
        >
          <Home className={`w-5 h-5 ${currentView === 'marketplace' ? 'stroke-[2.5px]' : ''}`} />
          <span className="text-[11px] mt-1">Inicio</span>
        </button>

        {/* Item 2: Create Campaign */}
        <button
          onClick={() => onNavigate('create_campaign')}
          className={`flex flex-col items-center justify-center flex-1 min-h-[48px] min-w-touch py-1 rounded-xl transition-all ${
            currentView === 'create_campaign' ? 'text-brand-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
          aria-label="Crear o gestionar Campañas"
        >
          <PlusCircle className={`w-5 h-5 ${currentView === 'create_campaign' ? 'stroke-[2.5px]' : ''}`} />
          <span className="text-[11px] mt-1">Campaña</span>
        </button>

        {/* Item 3: Collaboration & Workspace */}
        <button
          onClick={() => onNavigate('collaboration')}
          className={`flex flex-col items-center justify-center flex-1 min-h-[48px] min-w-touch py-1 rounded-xl transition-all ${
            currentView === 'collaboration' ? 'text-brand-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
          aria-label="Espacio de Colaboración"
        >
          <MessageSquare className={`w-5 h-5 ${currentView === 'collaboration' ? 'stroke-[2.5px]' : ''}`} />
          <span className="text-[11px] mt-1">Espacio</span>
        </button>

        {/* Item 4: Media Kit / Profile */}
        <button
          onClick={() => onNavigate('mediakit')}
          className={`flex flex-col items-center justify-center flex-1 min-h-[48px] min-w-touch py-1 rounded-xl transition-all ${
            currentView === 'mediakit' ? 'text-brand-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
          aria-label="Ver Media Kit y Perfil"
        >
          <UserCheck className={`w-5 h-5 ${currentView === 'mediakit' ? 'stroke-[2.5px]' : ''}`} />
          <span className="text-[11px] mt-1">Media Kit</span>
        </button>
      </div>
    </div>
  );
};
