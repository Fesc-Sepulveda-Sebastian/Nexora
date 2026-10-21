import React, { useState, useEffect } from 'react';
import { Application, CollaborationAgreement } from '../types';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { MilestoneBar } from '../components/collaboration/MilestoneBar';
import { RealtimeChat } from '../components/collaboration/RealtimeChat';
import { EvidenceUploader } from '../components/collaboration/EvidenceUploader';
import { ROICalculatorCard } from '../components/collaboration/ROICalculatorCard';
import { 
  Users, CheckCircle2, XCircle, Eye, Sparkles, MessageSquare, 
  ShieldAlert, Star, DollarSign, Calendar, AlertCircle
} from 'lucide-react';

interface IU06CollaborationProps {
  campaignId?: string;
}

export const IU06_Collaboration: React.FC<IU06CollaborationProps> = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'applicants' | 'workspace'>('workspace');
  
  // Data States
  const [applicants, setApplicants] = useState<Application[]>([]);
  const [collaboration, setCollaboration] = useState<CollaborationAgreement | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedApplicantMediaKit, setSelectedApplicantMediaKit] = useState<any | null>(null);
  
  // Rating Modal state (RN-05)
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [ratingScore, setRatingScore] = useState(5);
  const [ratingComment, setRatingComment] = useState('');
  const [ratingSuccess, setRatingSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadCollaborationData();
  }, []);

  const loadCollaborationData = async () => {
    setLoading(true);
    try {
      // Fetch latest campaign and its applications
      const campRes = await api.request<any>('/campaigns?limit=1');
      const camp = campRes.data.items?.[0];

      if (camp) {
        // Load applicants
        try {
          const { data: apps } = await api.request<Application[]>(`/campaigns/${camp.id}/applications`);
          setApplicants(apps);
        } catch (_) {}

        // Load active collaboration agreement
        const collabRes = await api.request<any>('/collaborations/roi-calculator', {
          method: 'POST',
          body: { total_cost: 450000, attributable_benefit: 1350000 }
        });
      }

      // Load sample active collaboration for Sofia and Cucuta Gourmet
      setCollaboration({
        id: 'collab_demo_01',
        application_id: 'app_demo_01',
        campaign_id: 'camp_demo_01',
        brand_id: 'brand_01',
        creator_id: 'creator_01',
        version_id: 1,
        scope_description: 'Creación y publicación de 1 Reel y 3 Stories promocionando el menú típico de Cúcuta Gourmet.',
        deliverables_terms: JSON.stringify([
          { format: 'Reel', qty: 1, specs: 'Video 30-60s destacando receta' },
          { format: 'Story', qty: 3, specs: 'Stories con sticker de ubicación en Cúcuta' }
        ]),
        compensation_amount: 450000,
        deadline: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
        brand_accepted: true,
        brand_accepted_at: new Date().toISOString(),
        creator_accepted: true,
        creator_accepted_at: new Date().toISOString(),
        status: 'En_Ejecucion',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });

      // Sample applicant
      setApplicants([
        {
          id: 'app_sofia_01',
          campaign_id: 'camp_01',
          creator_id: 'sofia_id',
          creative_proposal: 'Propondré una historia visual destacando los ingredientes típicos de la región con un Reel cinemático y 3 stories en vivo.',
          media_kit_snapshot_version: 3,
          media_kit_data: JSON.stringify({
            display_name: 'Sofía Castro | Foodie Cúcuta',
            niche: 'Gastronomía',
            location: 'Cúcuta, Colombia',
            followers: 8650,
            engagement: 6.84,
            rating: 5.0
          }),
          status: 'Aceptada',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      ]);
    } catch (e) {
      console.error('Error loading collaboration workspace:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptTerms = async () => {
    if (!collaboration) return;
    try {
      const { data } = await api.request<CollaborationAgreement>(`/collaborations/${collaboration.id}/accept`, {
        method: 'POST',
        body: { accepted_version_id: collaboration.version_id }
      });
      setCollaboration(data);
    } catch (e: any) {
      alert(e.message || 'Error al aceptar términos');
    }
  };

  const handleCloseCollaboration = () => {
    if (collaboration) {
      setCollaboration({ ...collaboration, status: 'Cerrada' });
      setShowRatingModal(true);
    }
  };

  const handleSubmitRating = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    try {
      // RN-05: Bilateral rating only allowed when status is Cerrada
      await api.request('/ratings', {
        method: 'POST',
        body: {
          collaboration_id: collaboration?.id,
          score: ratingScore,
          comment: ratingComment
        }
      });
      setRatingSuccess(true);
      setTimeout(() => setShowRatingModal(false), 1500);
    } catch (e: any) {
      setErrorMsg(e.message || 'RN-05: Error al registrar calificación bilateral');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-28 lg:pb-12 text-slate-100">
      {/* Workspace Tabs: Postulantes vs Espacio Activo */}
      <div className="flex items-center justify-between gap-3 mb-6">
        <div className="flex gap-2 p-1 bg-slate-900 rounded-2xl border border-slate-800">
          <button
            onClick={() => setActiveTab('workspace')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold min-h-touch transition-all ${
              activeTab === 'workspace'
                ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>Espacio de Colaboración Activa</span>
          </button>
          <button
            onClick={() => setActiveTab('applicants')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold min-h-touch transition-all ${
              activeTab === 'applicants'
                ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Dashboard de Postulantes ({applicants.length})</span>
          </button>
        </div>

        {collaboration?.status === 'En_Ejecucion' && (
          <button
            onClick={handleCloseCollaboration}
            className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs min-h-touch flex items-center gap-1.5 transition-all shadow-md active:scale-95"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Cerrar Colaboración (RN-05)</span>
          </button>
        )}
      </div>

      {activeTab === 'applicants' ? (
        /* APPLICANTS DASHBOARD: Desktop Table transforms automatically to Mobile Cards */
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl">
          <h2 className="text-lg font-black text-white mb-1">Creadores Postulados a la Campaña</h2>
          <p className="text-xs text-slate-400 mb-6">
            Evaluación bilateral transparente. El Media Kit se encuentra congelado a la fecha de postulación (RF-10).
          </p>

          {/* Desktop Table View (Hidden on mobile < 768px) */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Creador / Perfil</th>
                  <th className="py-3 px-4">Propuesta Creativa</th>
                  <th className="py-3 px-4">Brand-Fit</th>
                  <th className="py-3 px-4">Estado</th>
                  <th className="py-3 px-4 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {applicants.map((app) => {
                  let mk: any = {};
                  try { mk = JSON.parse(app.media_kit_data || '{}'); } catch (_) {}
                  return (
                    <tr key={app.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 font-bold text-white flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-brand-600/30 flex items-center justify-center font-bold text-brand-300">
                          {mk.display_name?.charAt(0) || 'C'}
                        </div>
                        <div>
                          <span>{mk.display_name || 'Creador Nexora'}</span>
                          <span className="block text-[10px] text-slate-400 font-normal">{mk.location}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 max-w-xs truncate">{app.creative_proposal}</td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-brand-300 bg-brand-500/10 px-2 py-0.5 rounded-full border border-brand-500/20">
                          <Sparkles className="w-3 h-3 text-amber-300" />
                          92% Fit
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/40">
                          {app.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          onClick={() => setSelectedApplicantMediaKit(mk)}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold"
                        >
                          Ver Media Kit Congelado
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile Vertical Cards (Shown on mobile < 768px) */}
          <div className="md:hidden space-y-4">
            {applicants.map((app) => {
              let mk: any = {};
              try { mk = JSON.parse(app.media_kit_data || '{}'); } catch (_) {}
              return (
                <div key={app.id} className="p-4 bg-slate-950 rounded-2xl border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-10 h-10 rounded-xl bg-brand-600/30 flex items-center justify-center font-bold text-brand-300">
                        {mk.display_name?.charAt(0) || 'C'}
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-white">{mk.display_name || 'Creador Nexora'}</h4>
                        <span className="text-[10px] text-slate-400">{mk.location}</span>
                      </div>
                    </div>
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/40">
                      {app.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 line-clamp-2">
                    {app.creative_proposal}
                  </p>

                  <div className="pt-2 border-t border-slate-800 flex gap-2">
                    <button
                      onClick={() => setSelectedApplicantMediaKit(mk)}
                      className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold min-h-touch"
                    >
                      Ver Media Kit
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* ACTIVE COLLABORATION WORKSPACE */
        <div className="space-y-6">
          {/* Milestone Status Bar */}
          {collaboration && <MilestoneBar status={collaboration.status} />}

          {/* Optimistic Versioned Terms Card (RF-13) */}
          {collaboration && (
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 sm:p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-brand-400">
                    Acuerdo de Colaboración (RF-13 Optimistic Concurrency)
                  </span>
                  <span className="text-[10px] font-semibold bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                    Versión {collaboration.version_id}
                  </span>
                </div>
                <h3 className="text-base sm:text-lg font-bold text-white">{collaboration.scope_description}</h3>
                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 mt-2">
                  <span className="flex items-center gap-1 text-emerald-400 font-bold">
                    <DollarSign className="w-3.5 h-3.5" />
                    ${collaboration.compensation_amount.toLocaleString()} COP
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-brand-400" />
                    Límite: {new Date(collaboration.deadline).toLocaleDateString()}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    Marca: {collaboration.brand_accepted ? '✓ Aceptado' : 'Pendiente'} | Creador: {collaboration.creator_accepted ? '✓ Aceptado' : 'Pendiente'}
                  </span>
                </div>
              </div>

              {collaboration.status === 'Acuerdo_Pendiente' && (
                <button
                  onClick={handleAcceptTerms}
                  className="px-6 py-3 bg-brand-600 hover:bg-brand-500 text-white font-bold text-xs rounded-xl min-h-touch flex items-center justify-center gap-2 shadow-lg shadow-brand-500/25 shrink-0"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Aceptar Versión {collaboration.version_id} en Línea</span>
                </button>
              )}
            </div>
          )}

          {/* 2-Column Grid: Left Chat, Right Evidence & ROI */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Realtime Chat */}
            {collaboration && (
              <RealtimeChat
                collaborationId={collaboration.id}
                recipientId={collaboration.creator_id}
                currentUserId={user?.id || 'brand_01'}
              />
            )}

            {/* Right side: Evidence Uploader + ROI Calculator */}
            <div className="space-y-6">
              {collaboration && (
                <EvidenceUploader
                  applicationId={collaboration.application_id}
                  onEvidenceUploaded={() => alert('Evidencia subida correctamente y hash SHA-256 verificado.')}
                />
              )}

              <ROICalculatorCard initialCost={450000} initialBenefit={1350000} />
            </div>
          </div>
        </div>
      )}

      {/* Frozen Media Kit Inspection Modal */}
      {selectedApplicantMediaKit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-lg w-full p-6 shadow-2xl text-slate-100">
            <h3 className="text-base font-bold text-white mb-1">
              Media Kit Congelado (RF-10)
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Instantánea de métricas capturadas al momento exacto de la postulación:
            </p>
            <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 space-y-2 text-xs">
              <p><strong>Creador:</strong> {selectedApplicantMediaKit.display_name}</p>
              <p><strong>Nicho:</strong> {selectedApplicantMediaKit.niche}</p>
              <p><strong>Ubicación:</strong> {selectedApplicantMediaKit.location}</p>
              <p><strong>Seguidores Verificados:</strong> {selectedApplicantMediaKit.followers?.toLocaleString()}</p>
              <p><strong>Engagement Rate:</strong> {selectedApplicantMediaKit.engagement}%</p>
            </div>
            <button
              onClick={() => setSelectedApplicantMediaKit(null)}
              className="mt-4 w-full py-3 bg-brand-600 hover:bg-brand-500 text-white font-bold rounded-xl text-xs min-h-touch"
            >
              Cerrar Vista Previa
            </button>
          </div>
        </div>
      )}

      {/* Bilateral Rating Modal (RN-05) */}
      {showRatingModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-amber-500/50 rounded-3xl max-w-md w-full p-6 shadow-2xl text-slate-100">
            <div className="flex items-center gap-2 text-amber-400 font-bold mb-2">
              <Star className="w-5 h-5 fill-amber-400" />
              <h3 className="text-base font-bold">Calificación Bilateral (RN-05)</h3>
            </div>
            <p className="text-xs text-slate-300 mb-4">
              La colaboración ha finalizado. Emite tu calificación (escala 1 a 5) y comentario moderable:
            </p>

            {errorMsg && (
              <div className="p-3 mb-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {ratingSuccess ? (
              <div className="p-4 rounded-xl bg-emerald-950 border border-emerald-800 text-emerald-300 text-xs font-bold text-center">
                ✓ ¡Calificación bilateral guardada exitosamente!
              </div>
            ) : (
              <form onSubmit={handleSubmitRating} className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-slate-400 block mb-1">
                    Puntuación (1 a 5 estrellas)
                  </label>
                  <div className="flex items-center gap-3">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <button
                        type="button"
                        key={s}
                        onClick={() => setRatingScore(s)}
                        className={`p-2 rounded-xl text-xs font-bold min-h-touch min-w-touch flex items-center justify-center ${
                          ratingScore >= s ? 'text-amber-400 bg-amber-950/50' : 'text-slate-600 bg-slate-950'
                        }`}
                      >
                        <Star className="w-5 h-5 fill-current" />
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-400 block mb-1">
                    Comentario de Experiencia (Moderable)
                  </label>
                  <textarea
                    rows={3}
                    value={ratingComment}
                    onChange={(e) => setRatingComment(e.target.value)}
                    placeholder="Excelente puntualidad en los entregables y gran impacto local..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setShowRatingModal(false)}
                    className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold min-h-touch"
                  >
                    Omitir
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-3 bg-brand-600 hover:bg-brand-500 text-white font-bold rounded-xl text-xs min-h-touch shadow-md shadow-brand-500/20"
                  >
                    Guardar Calificación
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
