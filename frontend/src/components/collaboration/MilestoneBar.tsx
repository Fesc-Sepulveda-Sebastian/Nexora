import React from 'react';
import { CheckCircle2, Clock, Eye, Flag } from 'lucide-react';

interface MilestoneBarProps {
  status: 'Acuerdo_Pendiente' | 'En_Ejecucion' | 'En_Revision' | 'Cerrada' | 'Disputa';
}

export const MilestoneBar: React.FC<MilestoneBarProps> = ({ status }) => {
  const steps = [
    { key: 'Acuerdo_Pendiente', label: '1. Acuerdo', icon: Clock },
    { key: 'En_Ejecucion', label: '2. En Ejecución', icon: CheckCircle2 },
    { key: 'En_Revision', label: '3. En Revisión', icon: Eye },
    { key: 'Cerrada', label: '4. Cierre', icon: Flag }
  ];

  const getStepIndex = () => {
    switch (status) {
      case 'Acuerdo_Pendiente': return 0;
      case 'En_Ejecucion': return 1;
      case 'En_Revision': return 2;
      case 'Cerrada': return 3;
      default: return 0;
    }
  };

  const currentIndex = getStepIndex();

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-lg">
      <div className="flex items-center justify-between relative">
        {/* Background track line */}
        <div className="absolute top-4 left-4 right-4 h-0.5 bg-slate-800 -z-0" />

        {steps.map((step, idx) => {
          const Icon = step.icon;
          const isCompleted = idx < currentIndex || status === 'Cerrada';
          const isCurrent = idx === currentIndex && status !== 'Cerrada';

          return (
            <div key={step.key} className="flex flex-col items-center relative z-10">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                  isCompleted
                    ? 'bg-emerald-600 text-white'
                    : isCurrent
                    ? 'bg-brand-600 text-white ring-4 ring-brand-500/20'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                <Icon className="w-4 h-4" />
              </div>
              <span className={`text-[11px] font-semibold mt-2 text-center ${
                isCurrent ? 'text-brand-300 font-bold' : isCompleted ? 'text-emerald-400' : 'text-slate-400'
              }`}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
