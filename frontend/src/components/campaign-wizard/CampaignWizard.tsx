import React, { useState } from 'react';
import { Campaign, DeliverableItem, SelectionCriteria } from '../../types';
import { api } from '../../services/api';
import { indexDB } from '../../db/indexdb';
import { useOfflineSync } from '../../context/OfflineSyncContext';
import { CheckCircle2, ChevronRight, ChevronLeft, Save, Send, AlertCircle, Plus, Trash2 } from 'lucide-react';

interface CampaignWizardProps {
  onCampaignCreated: (campaign: Campaign) => void;
}

export const CampaignWizard: React.FC<CampaignWizardProps> = ({ onCampaignCreated }) => {
  const { isOnline } = useOfflineSync();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form State
  const [title, setTitle] = useState('');
  const [objective, setObjective] = useState('');
  const [niche, setNiche] = useState('Gastronomía');
  const [compensationType, setCompensationType] = useState<'pago_fijo' | 'canje' | 'hibrido'>('pago_fijo');
  const [budget, setBudget] = useState<number>(350000);
  const [compensationNotes, setCompensationNotes] = useState('');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(
    new Date(Date.now() + 20 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [deliverables, setDeliverables] = useState<DeliverableItem[]>([
    { format: 'Reel', qty: 1, specs: 'Video dinámico de 30 a 60 segundos destacando experiencia de marca.' }
  ]);
  const [selectionCriteria, setSelectionCriteria] = useState<SelectionCriteria>({
    min_followers: 1500,
    location: 'Cúcuta, Colombia',
    platforms: ['Instagram']
  });

  const handleAddDeliverable = () => {
    setDeliverables([...deliverables, { format: 'Story', qty: 2, specs: 'Stories con mención a la cuenta oficial' }]);
  };

  const handleRemoveDeliverable = (idx: number) => {
    setDeliverables(deliverables.filter((_, i) => i !== idx));
  };

  // Client-side validation of RN-01
  const validateRN01 = (): string[] => {
    const errors: string[] = [];
    if (!title || title.trim().length < 3) errors.push('El título debe tener al menos 3 caracteres.');
    if (!objective || objective.trim().length < 10) errors.push('El objetivo debe tener al menos 10 caracteres.');
    if (!niche) errors.push('Debe seleccionar un nicho de mercado.');
    if (!startDate || !endDate) errors.push('Las fechas de inicio y fin son obligatorias.');
    if (new Date(endDate) <= new Date(startDate)) errors.push('La fecha de fin debe ser posterior a la de inicio.');
    if (!deliverables || deliverables.length === 0) errors.push('Debe agregar al menos un entregable.');
    if (compensationType !== 'canje' && (!budget || budget <= 0)) {
      errors.push('Debe especificar un presupuesto mayor a 0 COP para campañas pagadas.');
    }
    return errors;
  };

  const handleSaveDraft = async () => {
    setErrorMsg(null);
    try {
      const draftData = {
        title: title || 'Borrador sin título',
        objective,
        niche,
        compensation_type: compensationType,
        budget: Number(budget),
        compensation_notes: compensationNotes,
        start_date: startDate ? new Date(startDate).toISOString() : undefined,
        end_date: endDate ? new Date(endDate).toISOString() : undefined,
        deliverables,
        selection_criteria: selectionCriteria
      };

      if (!isOnline) {
        // Save local draft in IndexedDB (max 5)
        await indexDB.saveLocalDraft({
          local_id: 'draft_' + Date.now(),
          ...draftData,
          version_id: 1,
          sync_status: 'Pendiente',
          last_modified: new Date().toISOString()
        });
        alert('Borrador guardado localmente en tu dispositivo (Modo Offline). Se sincronizará al recuperar conexión.');
        return;
      }

      // Online save draft
      const { data } = await api.request<Campaign>('/campaigns', {
        method: 'POST',
        body: draftData
      });
      onCampaignCreated(data);
    } catch (e: any) {
      setErrorMsg(e.message || 'Error al guardar el borrador');
    }
  };

  const handlePublish = async () => {
    setErrorMsg(null);
    const errors = validateRN01();
    if (errors.length > 0) {
      setErrorMsg(`RN-01: ${errors.join(' ')}`);
      return;
    }

    if (!isOnline) {
      setErrorMsg('RN-02: No es posible publicar campañas sin conexión al servidor.');
      return;
    }

    setIsSubmitting(true);
    try {
      // 1. Create draft first
      const { data: createdDraft } = await api.request<Campaign>('/campaigns', {
        method: 'POST',
        body: {
          title,
          objective,
          niche,
          compensation_type: compensationType,
          budget: Number(budget),
          compensation_notes: compensationNotes,
          start_date: new Date(startDate).toISOString(),
          end_date: new Date(endDate).toISOString(),
          deliverables,
          selection_criteria: selectionCriteria
        }
      });

      // 2. Publish draft validating RN-01 on backend
      const { data: publishedCampaign } = await api.request<Campaign>(`/campaigns/${createdDraft.id}/publish`, {
        method: 'POST'
      });

      onCampaignCreated(publishedCampaign);
    } catch (e: any) {
      setErrorMsg(e.message || 'Error al publicar la campaña');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 lg:p-8">
      {/* Wizard Progress Stepper */}
      <div className="flex items-center justify-between mb-8 max-w-lg mx-auto">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <button
              onClick={() => setStep(s as any)}
              className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm min-h-touch min-w-touch transition-all ${
                step === s
                  ? 'bg-brand-600 text-white ring-4 ring-brand-500/20'
                  : step > s
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-800 text-slate-400'
              }`}
            >
              {step > s ? <CheckCircle2 className="w-5 h-5" /> : s}
            </button>
            <span className={`text-xs font-semibold hidden sm:inline ${step === s ? 'text-white' : 'text-slate-400'}`}>
              {s === 1 ? '1. Información' : s === 2 ? '2. Condiciones' : '3. Criterios & Entregables'}
            </span>
          </div>
        ))}
      </div>

      {errorMsg && (
        <div role="alert" className="mb-6 p-4 rounded-xl bg-rose-950/80 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2 animate-shake">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Progressive Step Cards */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl">
        {step === 1 && (
          <div className="space-y-5 animate-fade-in">
            <h2 className="text-xl font-bold text-white mb-2">Paso 1: Información de la Campaña</h2>
            
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase mb-2">
                Título de la Campaña *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ej. Ruta Gastronómica Tradicional Cúcuta 2026"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand-500 min-h-touch"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase mb-2">
                Objetivo Comercial *
              </label>
              <textarea
                rows={3}
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                placeholder="Describe claramente la meta (ej. dar a conocer el nuevo menú regional y atraer 300 comensales)."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase mb-2">
                Nicho / Categoría *
              </label>
              <select
                value={niche}
                onChange={(e) => setNiche(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand-500 min-h-touch"
              >
                <option value="Gastronomía">Gastronomía</option>
                <option value="Fitness & Salud">Fitness & Salud</option>
                <option value="Moda & Belleza">Moda & Belleza</option>
                <option value="Tecnología">Tecnología</option>
                <option value="Turismo">Turismo</option>
              </select>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5 animate-fade-in">
            <h2 className="text-xl font-bold text-white mb-2">Paso 2: Modalidad y Fechas</h2>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase mb-2">
                Modalidad de Compensación *
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setCompensationType('pago_fijo')}
                  className={`p-3 rounded-xl border text-xs font-bold min-h-touch transition-all ${
                    compensationType === 'pago_fijo'
                      ? 'bg-brand-600 border-brand-500 text-white'
                      : 'bg-slate-950 border-slate-800 text-slate-300'
                  }`}
                >
                  Pago Económico Fijo
                </button>
                <button
                  type="button"
                  onClick={() => setCompensationType('canje')}
                  className={`p-3 rounded-xl border text-xs font-bold min-h-touch transition-all ${
                    compensationType === 'canje'
                      ? 'bg-brand-600 border-brand-500 text-white'
                      : 'bg-slate-950 border-slate-800 text-slate-300'
                  }`}
                >
                  Canje / Producto VIP
                </button>
              </div>
            </div>

            {compensationType !== 'canje' ? (
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-2">
                  Presupuesto Total (COP) *
                </label>
                <input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand-500 min-h-touch"
                />
              </div>
            ) : (
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-2">
                  Detalles del Canje / Producto *
                </label>
                <input
                  type="text"
                  value={compensationNotes}
                  onChange={(e) => setCompensationNotes(e.target.value)}
                  placeholder="Ej. Cena completa para 2 personas + cocteles de autor"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand-500 min-h-touch"
                />
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-2">
                  Fecha de Inicio *
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand-500 min-h-touch"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-2">
                  Fecha de Finalización *
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand-500 min-h-touch"
                />
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5 animate-fade-in">
            <h2 className="text-xl font-bold text-white mb-2">Paso 3: Entregables y Criterios</h2>

            {/* Deliverables List */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold text-slate-300 uppercase">
                  Entregables Requeridos *
                </label>
                <button
                  type="button"
                  onClick={handleAddDeliverable}
                  className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 font-semibold min-h-touch"
                >
                  <Plus className="w-4 h-4" />
                  <span>Agregar Entregable</span>
                </button>
              </div>

              <div className="space-y-3">
                {deliverables.map((d, index) => (
                  <div key={index} className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-start gap-3">
                    <div className="w-28 shrink-0">
                      <select
                        value={d.format}
                        onChange={(e) => {
                          const updated = [...deliverables];
                          updated[index].format = e.target.value;
                          setDeliverables(updated);
                        }}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-xs text-white"
                      >
                        <option value="Reel">Reel (IG)</option>
                        <option value="Story">Story (IG)</option>
                        <option value="TikTok">TikTok</option>
                        <option value="Post">Post Estático</option>
                      </select>
                    </div>
                    <div className="flex-1">
                      <input
                        type="text"
                        value={d.specs}
                        onChange={(e) => {
                          const updated = [...deliverables];
                          updated[index].specs = e.target.value;
                          setDeliverables(updated);
                        }}
                        placeholder="Especificaciones del entregable"
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white"
                      />
                    </div>
                    {deliverables.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveDeliverable(index)}
                        className="p-2 text-rose-400 hover:text-rose-300 min-h-touch min-w-touch"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Selection Criteria */}
            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-2xl space-y-3">
              <span className="text-xs font-bold text-brand-300 uppercase block">
                Criterios de Selección (Filtro para Creadores)
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Seguidores Mínimos</label>
                  <input
                    type="number"
                    value={selectionCriteria.min_followers}
                    onChange={(e) => setSelectionCriteria({ ...selectionCriteria, min_followers: Number(e.target.value) })}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Ubicación Requerida</label>
                  <input
                    type="text"
                    value={selectionCriteria.location || ''}
                    onChange={(e) => setSelectionCriteria({ ...selectionCriteria, location: e.target.value })}
                    placeholder="Ej. Cúcuta, Colombia"
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Wizard Controls */}
        <div className="mt-8 pt-6 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            {step > 1 && (
              <button
                type="button"
                onClick={() => setStep((step - 1) as any)}
                className="w-full sm:w-auto px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 min-h-touch"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Atrás</span>
              </button>
            )}
            <button
              type="button"
              onClick={handleSaveDraft}
              className="w-full sm:w-auto px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 min-h-touch"
            >
              <Save className="w-4 h-4 text-brand-400" />
              <span>Guardar Borrador</span>
            </button>
          </div>

          <div className="w-full sm:w-auto">
            {step < 3 ? (
              <button
                type="button"
                onClick={() => setStep((step + 1) as any)}
                className="w-full sm:w-auto px-6 py-3 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 min-h-touch shadow-lg shadow-brand-500/20"
              >
                <span>Siguiente</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                disabled={isSubmitting || !isOnline}
                onClick={handlePublish}
                className="w-full sm:w-auto px-6 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 min-h-touch shadow-lg shadow-emerald-600/25"
              >
                <Send className="w-4 h-4" />
                <span>{isSubmitting ? 'Publicando...' : 'Publicar Campaña (RN-01)'}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
