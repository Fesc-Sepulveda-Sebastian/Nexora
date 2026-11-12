import React, { useState, useEffect } from 'react';
import {
  Application,
  Campaign,
  CollaborationAgreement,
  CollaborationAgreementVersion,
  CollaborationFinancialSummary,
  DeliverableEvidence
} from '../types';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { MilestoneBar } from '../components/collaboration/MilestoneBar';
import { RealtimeChat } from '../components/collaboration/RealtimeChat';
import { EvidenceUploader } from '../components/collaboration/EvidenceUploader';
import { ROICalculatorCard } from '../components/collaboration/ROICalculatorCard';
import {
  Users, CheckCircle2, XCircle, Sparkles, MessageSquare,
  Star, DollarSign, Calendar, AlertCircle, Edit3, Briefcase,
  History, FileCheck, ExternalLink
} from 'lucide-react';

interface IU06CollaborationProps {
  campaignId?: string;
}

export const IU06_Collaboration: React.FC<IU06CollaborationProps> = ({ campaignId }) => {
  const { user, isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<'applicants' | 'workspace'>('workspace');

  // Data States
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | undefined>(campaignId);
  const [applicants, setApplicants] = useState<Application[]>([]);
  const [collaborations, setCollaborations] = useState<CollaborationAgreement[]>([]);
  const [collaboration, setCollaboration] = useState<CollaborationAgreement | null>(null);
  const [versions, setVersions] = useState<CollaborationAgreementVersion[]>([]);
  const [showVersions, setShowVersions] = useState(false);
  const [evidences, setEvidences] = useState<DeliverableEvidence[]>([]);
  const [financialSummary, setFinancialSummary] = useState<CollaborationFinancialSummary | null>(null);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedApplicantMediaKit, setSelectedApplicantMediaKit] = useState<any | null>(null);

  // Terms Edit State (RF-13)
  const [editingTerms, setEditingTerms] = useState(false);
  const [editScope, setEditScope] = useState('');
  const [editAmount, setEditAmount] = useState<number>(0);

  // Rating Modal state (RN-05)
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [ratingScore, setRatingScore] = useState(5);
  const [ratingComment, setRatingComment] = useState('');
  const [ratingSuccess, setRatingSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  useEffect(() => {
    setSelectedCampaignId(campaignId);
  }, [campaignId]);

  useEffect(() => {
    if (isAuthenticated) {
      loadCollaborationData();
    } else {
      setLoading(false);
    }
  }, [isAuthenticated, selectedCampaignId, user?.id]);

  const loadCollaborationDetails = async (collabId: string) => {
    try {
      const [verRes, evRes, finRes] = await Promise.all([
        api.request<CollaborationAgreementVersion[]>(`/collaborations/${collabId}/versions`).catch(() => ({ data: [] })),
        api.request<DeliverableEvidence[]>(`/collaborations/${collabId}/evidences`).catch(() => ({ data: [] })),
        api.request<CollaborationFinancialSummary>(`/collaborations/${collabId}/financial-summary`).catch(() => ({ data: null }))
      ]);
      setVersions(verRes.data || []);
      setEvidences(evRes.data || []);
      setFinancialSummary(finRes.data || null);
    } catch (_) {
      setVersions([]);
      setEvidences([]);
      setFinancialSummary(null);
    }
  };

  const loadCollaborationData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const collabQuery = selectedCampaignId
        ? `/collaborations?campaign_id=${encodeURIComponent(selectedCampaignId)}`
        : '/collaborations';
      const { data: collabList } = await api.request<CollaborationAgreement[]>(collabQuery);
      setCollaborations(collabList);

      const activeCollab = collabList[0] || null;
      setCollaboration(activeCollab);
      if (activeCollab) {
        setEditScope(activeCollab.scope_description);
        setEditAmount(activeCollab.compensation_amount);
        await loadCollaborationDetails(activeCollab.id);
      } else {
        setVersions([]);
        setEvidences([]);
        setFinancialSummary(null);
      }

      // If brand or admin, load own campaigns and applicants for selected campaign
      if (user?.role === 'marca' || user?.role === 'administrador') {
        const { data: campPage } = await api.request<any>('/campaigns?limit=20');
        const brandCamps: Campaign[] = (campPage.items || []).filter(
          (c: Campaign) => user.role === 'administrador' || c.brand_id === user.id
        );
        setCampaigns(brandCamps);

        const targetCampId = selectedCampaignId || activeCollab?.campaign_id || brandCamps[0]?.id;
        if (targetCampId) {
          try {
            const { data: apps } = await api.request<Application[]>(`/campaigns/${targetCampId}/applications`);
            setApplicants(apps);
          } catch (_) {
            setApplicants([]);
          }
        } else {
          setApplicants([]);
        }
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Error al cargar el espacio de colaboración');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateApplicationStatus = async (applicationId: string, newStatus: 'Aceptada' | 'Rechazada') => {
    setErrorMsg(null);
    setActionMsg(null);
    try {
      await api.request<Application>(`/applications/${applicationId}/status`, {
        method: 'PATCH',
        body: { status: newStatus }
      });
      setActionMsg(
        newStatus === 'Aceptada'
          ? 'Postulación aceptada. Se ha generado el acuerdo de colaboración.'
          : 'Postulación rechazada.'
      );
      await loadCollaborationData();
      if (newStatus === 'Aceptada') {
        setActiveTab('workspace');
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Error al actualizar estado de postulación');
    }
  };

  const handleSaveTerms = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!collaboration) return;
    setErrorMsg(null);
    try {
      const { data } = await api.request<CollaborationAgreement>(`/collaborations/${collaboration.id}/terms`, {
        method: 'PUT',
        body: {
          expected_version: collaboration.version_id,
          scope_description: editScope,
          compensation_amount: Number(editAmount)
        }
      });
      setCollaboration(data);
      setEditingTerms(false);
      setActionMsg(`Términos actualizados a versión ${data.version_id}. Ambas partes deben aceptar nuevamente.`);
      await loadCollaborationDetails(data.id);
    } catch (e: any) {
      setErrorMsg(e.message || 'Error al actualizar términos del acuerdo');
    }
  };

  const handleAcceptTerms = async () => {
    if (!collaboration) return;
    setErrorMsg(null);
    setActionMsg(null);
    try {
      const { data } = await api.request<CollaborationAgreement>(`/collaborations/${collaboration.id}/accept`, {
        method: 'POST',
        body: { accepted_version_id: collaboration.version_id }
      });
      setCollaboration(data);
      setActionMsg(
        data.status === 'En_Ejecucion'
          ? '¡Ambas partes han aceptado! La colaboración está ahora En Ejecución.'
          : 'Tu aceptación quedó registrada. Esperando a la contraparte.'
      );
    } catch (e: any) {
      setErrorMsg(e.message || 'Error al aceptar términos');
    }
  };

  const handleCloseCollaboration = async () => {
    if (!collaboration) return;
    setErrorMsg(null);
    setActionMsg(null);
    try {
      const { data } = await api.request<CollaborationAgreement>(`/collaborations/${collaboration.id}/close`, {
        method: 'POST'
      });
      setCollaboration(data);
      setCollaborations((prev) => prev.map((c) => (c.id === data.id ? data : c)));
      if (data.status === 'Cerrada') {
        setShowRatingModal(true);
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Error al cerrar la colaboración');
    }
  };

  const handleReviewEvidence = async (evidenceId: string, reviewStatus: 'Aprobado' | 'Rechazado') => {
    if (!collaboration) return;
    setReviewingId(evidenceId);
    setErrorMsg(null);
    setActionMsg(null);
    try {
      await api.request<DeliverableEvidence>(`/evidences/${evidenceId}/review`, {
        method: 'PATCH',
        body: {
          status: reviewStatus,
          review_notes:
            reviewStatus === 'Aprobado'
              ? 'Entregable verificado y aprobado por la marca.'
              : 'Requiere ajustes según el alcance acordado.'
        }
      });
      setActionMsg(`Evidencia marcada como '${reviewStatus}'.`);
      await loadCollaborationDetails(collaboration.id);
    } catch (e: any) {
      setErrorMsg(e.message || 'Error al revisar evidencia');
    } finally {
      setReviewingId(null);
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

  const handleOpenEvidenceFile = async (fileUrl: string) => {
    try {
      const targetUrl = fileUrl.startsWith('http') ? fileUrl : `${api.getApiOrigin()}${fileUrl}`;
      if (fileUrl.startsWith('http')) {
        window.open(targetUrl, '_blank', 'noopener,noreferrer');
        return;
      }
      const token = localStorage.getItem('nexora_token');
      const res = await fetch(targetUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (!res.ok) {
        throw new Error(`No autorizado o archivo no disponible (${res.status})`);
      }
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      window.open(blobUrl, '_blank', 'noopener,noreferrer');
      setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
    } catch (e: any) {
      setErrorMsg(e?.message || 'No fue posible abrir el archivo de evidencia.');
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-3xl mx-auto p-6 text-center text-slate-300">
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8">
          <Briefcase className="w-10 h-10 text-brand-400 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-white mb-2">Inicia sesión para gestionar colaboraciones</h2>
          <p className="text-xs text-slate-400">
            El espacio de acuerdos, mensajería y entrega de evidencias requiere una sesión autenticada.
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto p-6 animate-pulse space-y-4">
        <div className="h-16 bg-slate-900 rounded-2xl" />
        <div className="h-48 bg-slate-900 rounded-3xl" />
      </div>
    );
  }

  const recipientId = collaboration
    ? user?.id === collaboration.brand_id
      ? collaboration.creator_id
      : collaboration.brand_id
    : '';

  const canClose = collaboration?.status === 'En_Ejecucion' || collaboration?.status === 'En_Revision';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-28 lg:pb-12 text-slate-100">
      {/* Workspace Tabs & Collaboration Selector */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
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
            <span>Espacio de Colaboración ({collaborations.length})</span>
          </button>
          {(user?.role === 'marca' || user?.role === 'administrador') && (
            <button
              onClick={() => setActiveTab('applicants')}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold min-h-touch transition-all ${
                activeTab === 'applicants'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Users className="w-4 h-4" />
              <span>Postulantes ({applicants.length})</span>
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {collaborations.length > 1 && (
            <select
              value={collaboration?.id || ''}
              onChange={(e) => {
                const found = collaborations.find((c) => c.id === e.target.value) || null;
                setCollaboration(found);
                if (found) {
                  setEditScope(found.scope_description);
                  setEditAmount(found.compensation_amount);
                  loadCollaborationDetails(found.id);
                }
              }}
              className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white min-h-touch"
            >
              {collaborations.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.scope_description.slice(0, 40)} ({c.status})
                </option>
              ))}
            </select>
          )}

          {canClose && (
            <button
              onClick={handleCloseCollaboration}
              className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs min-h-touch flex items-center gap-1.5 transition-all shadow-md active:scale-95"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Cerrar Colaboración (RN-05)</span>
            </button>
          )}

          {collaboration?.status === 'Cerrada' && (
            <button
              onClick={() => setShowRatingModal(true)}
              className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs min-h-touch flex items-center gap-1.5 transition-all shadow-md"
            >
              <Star className="w-4 h-4" />
              <span>Calificar Contraparte (RN-05)</span>
            </button>
          )}
        </div>
      </div>

      {errorMsg && (
        <div role="alert" className="p-3 mb-4 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {actionMsg && (
        <div className="p-3 mb-4 rounded-xl bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{actionMsg}</span>
        </div>
      )}

      {activeTab === 'applicants' ? (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
              <h2 className="text-lg font-black text-white mb-1">Creadores Postulados a la Campaña</h2>
              <p className="text-xs text-slate-400">
                Evaluación bilateral transparente. El Media Kit se encuentra congelado a la fecha de postulación (RF-10).
              </p>
            </div>
            {campaigns.length > 0 && (
              <select
                value={selectedCampaignId || ''}
                onChange={(e) => setSelectedCampaignId(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white min-h-touch"
              >
                {campaigns.map((camp) => (
                  <option key={camp.id} value={camp.id}>
                    {camp.title} ({camp.status})
                  </option>
                ))}
              </select>
            )}
          </div>

          {applicants.length === 0 ? (
            <div className="text-center py-12 text-xs text-slate-400">
              No hay postulaciones registradas para esta campaña todavía.
            </div>
          ) : (
            <>
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">Creador / Perfil</th>
                      <th className="py-3 px-4">Propuesta Creativa</th>
                      <th className="py-3 px-4">Versión MK</th>
                      <th className="py-3 px-4">Estado</th>
                      <th className="py-3 px-4 text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {applicants.map((app) => {
                      let mk: any = {};
                      try { mk = JSON.parse(app.media_kit_data || '{}'); } catch (_) {}
                      const isPending = app.status === 'Recibida' || app.status === 'En_Revision';
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
                              v{app.media_kit_snapshot_version}
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
                              Media Kit
                            </button>
                            {isPending && (
                              <>
                                <button
                                  onClick={() => handleUpdateApplicationStatus(app.id, 'Aceptada')}
                                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold"
                                >
                                  Aceptar
                                </button>
                                <button
                                  onClick={() => handleUpdateApplicationStatus(app.id, 'Rechazada')}
                                  className="px-3 py-1.5 bg-rose-700 hover:bg-rose-600 text-white rounded-lg text-xs font-semibold"
                                >
                                  Rechazar
                                </button>
                              </>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="md:hidden space-y-4">
                {applicants.map((app) => {
                  let mk: any = {};
                  try { mk = JSON.parse(app.media_kit_data || '{}'); } catch (_) {}
                  const isPending = app.status === 'Recibida' || app.status === 'En_Revision';
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
                      <p className="text-xs text-slate-300 line-clamp-2">{app.creative_proposal}</p>
                      <div className="pt-2 border-t border-slate-800 flex flex-wrap gap-2">
                        <button
                          onClick={() => setSelectedApplicantMediaKit(mk)}
                          className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold min-h-touch"
                        >
                          Media Kit
                        </button>
                        {isPending && (
                          <>
                            <button
                              onClick={() => handleUpdateApplicationStatus(app.id, 'Aceptada')}
                              className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold min-h-touch"
                            >
                              Aceptar
                            </button>
                            <button
                              onClick={() => handleUpdateApplicationStatus(app.id, 'Rechazada')}
                              className="py-2.5 px-3 bg-rose-700 hover:bg-rose-600 text-white rounded-xl text-xs font-semibold min-h-touch"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      ) : !collaboration ? (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 text-center">
          <Briefcase className="w-10 h-10 text-slate-500 mx-auto mb-3" />
          <h3 className="text-base font-bold text-white mb-1">No tienes acuerdos de colaboración activos</h3>
          <p className="text-xs text-slate-400">
            Cuando una marca acepte una postulación, aquí aparecerá el acuerdo versionado, chat contextual y subida de evidencias.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          <MilestoneBar status={collaboration.status} />

          {/* Optimistic Versioned Terms Card (RF-13) */}
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 sm:p-6 shadow-xl space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-brand-400">
                    Acuerdo de Colaboración (RF-13)
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
                {financialSummary && (
                  <div className="mt-3 inline-flex flex-wrap items-center gap-3 px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-300">
                    <span>Comisión NEXORA (10%): <strong className="text-brand-300">${financialSummary.nexora_commission_amount.toLocaleString()}</strong></span>
                    <span>•</span>
                    <span>Costo total campaña: <strong className="text-emerald-400">${financialSummary.total_campaign_cost.toLocaleString()}</strong></span>
                    {financialSummary.volume_discount_applied && (
                      <>
                        <span>•</span>
                        <span className="text-amber-300 font-semibold">Descuento volumen {financialSummary.volume_discount_pct}% (&ge;5 piezas)</span>
                      </>
                    )}
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => setShowVersions(!showVersions)}
                  className="px-4 py-3 bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-200 font-semibold text-xs rounded-xl min-h-touch flex items-center gap-2"
                >
                  <History className="w-4 h-4 text-brand-400" />
                  <span>Historial ({versions.length || collaboration.version_id})</span>
                </button>
                {collaboration.status === 'Acuerdo_Pendiente' && (
                  <>
                    <button
                      onClick={() => setEditingTerms(!editingTerms)}
                      className="px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs rounded-xl min-h-touch flex items-center gap-2"
                    >
                      <Edit3 className="w-4 h-4" />
                      <span>Negociar Términos</span>
                    </button>
                    <button
                      onClick={handleAcceptTerms}
                      className="px-6 py-3 bg-brand-600 hover:bg-brand-500 text-white font-bold text-xs rounded-xl min-h-touch flex items-center justify-center gap-2 shadow-lg shadow-brand-500/25"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Aceptar Versión {collaboration.version_id}</span>
                    </button>
                  </>
                )}
              </div>
            </div>

            {showVersions && (
              <div className="pt-4 border-t border-slate-800 space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Historial Inmutable de Versiones (RF-13)
                </h4>
                {versions.length === 0 ? (
                  <p className="text-xs text-slate-500">Solo versión inicial v{collaboration.version_id} registrada.</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {versions.map((ver) => (
                      <div key={ver.id} className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-bold text-brand-300">Versión v{ver.version_id}</span>
                          <span className="text-[10px] text-slate-500">
                            {new Date(ver.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-slate-300">{ver.scope_description}</p>
                        <p className="text-emerald-400 font-semibold mt-1">
                          ${Number(ver.compensation_amount).toLocaleString()} COP
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {editingTerms && collaboration.status === 'Acuerdo_Pendiente' && (
              <form onSubmit={handleSaveTerms} className="pt-4 border-t border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="md:col-span-2">
                  <label className="text-[11px] text-slate-400 uppercase block mb-1">Alcance del Acuerdo</label>
                  <input
                    type="text"
                    required
                    value={editScope}
                    onChange={(e) => setEditScope(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white min-h-touch"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-400 uppercase block mb-1">Compensación (COP)</label>
                  <input
                    type="number"
                    min="0"
                    required
                    value={editAmount}
                    onChange={(e) => setEditAmount(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white min-h-touch"
                  />
                </div>
                <div className="md:col-span-3 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setEditingTerms(false)}
                    className="px-4 py-2 bg-slate-800 text-slate-300 rounded-xl text-xs font-semibold"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-bold"
                  >
                    Guardar Nueva Versión
                  </button>
                </div>
              </form>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <RealtimeChat
              collaborationId={collaboration.id}
              recipientId={recipientId}
              currentUserId={user?.id || ''}
            />

            <div className="space-y-6">
              {user?.role === 'creador' && (
                <EvidenceUploader
                  applicationId={collaboration.application_id}
                  onEvidenceUploaded={() => {
                    setActionMsg('Evidencia subida y verificada por SHA-256.');
                    loadCollaborationData();
                  }}
                />
              )}

              {/* Evidences Review Panel (RF-14) */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-brand-400 font-bold text-sm">
                    <FileCheck className="w-4 h-4" />
                    <h4>Evidencias de Entregables ({evidences.length})</h4>
                  </div>
                </div>

                {evidences.length === 0 ? (
                  <p className="text-xs text-slate-400">
                    Aún no se han cargado evidencias verificadas para esta colaboración.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {evidences.map((ev) => {
                      const canReview =
                        (user?.role === 'marca' || user?.role === 'administrador') &&
                        ev.status !== 'Aprobado';
                      return (
                        <div key={ev.id} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-bold text-white">{ev.deliverable_name}</span>
                            <span
                              className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${
                                ev.status === 'Aprobado'
                                  ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                                  : ev.status === 'Rechazado'
                                  ? 'bg-rose-950 text-rose-300 border-rose-800'
                                  : 'bg-amber-950 text-amber-300 border-amber-800'
                              }`}
                            >
                              {ev.status}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 font-mono truncate">
                            SHA-256: {ev.file_hash_sha256.slice(0, 16)}... ({ev.file_size_mb} MB)
                          </p>
                          {ev.review_notes && (
                            <p className="text-[11px] text-slate-300 italic">{ev.review_notes}</p>
                          )}
                          <div className="flex flex-wrap items-center gap-2 pt-1">
                            {ev.external_live_url && (
                              <a
                                href={ev.external_live_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-[11px] text-brand-400 hover:text-brand-300 font-semibold"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                                <span>Publicación en vivo</span>
                              </a>
                            )}
                            <button
                              type="button"
                              onClick={() => handleOpenEvidenceFile(ev.file_url)}
                              className="inline-flex items-center gap-1 text-[11px] text-slate-300 hover:text-white underline"
                            >
                              Archivo soporte
                            </button>
                            {canReview && (
                              <div className="ml-auto flex gap-2">
                                <button
                                  type="button"
                                  disabled={reviewingId === ev.id}
                                  onClick={() => handleReviewEvidence(ev.id, 'Aprobado')}
                                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-[11px] font-bold"
                                >
                                  Aprobar
                                </button>
                                <button
                                  type="button"
                                  disabled={reviewingId === ev.id}
                                  onClick={() => handleReviewEvidence(ev.id, 'Rechazado')}
                                  className="px-3 py-1.5 bg-rose-700 hover:bg-rose-600 text-white rounded-lg text-[11px] font-bold"
                                >
                                  Rechazar
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <ROICalculatorCard
                initialCost={collaboration.compensation_amount || 450000}
                initialBenefit={(collaboration.compensation_amount || 450000) * 3}
              />
            </div>
          </div>
        </div>
      )}

      {/* Frozen Media Kit Inspection Modal */}
      {selectedApplicantMediaKit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-lg w-full p-6 shadow-2xl text-slate-100">
            <h3 className="text-base font-bold text-white mb-1">Media Kit Congelado (RF-10)</h3>
            <p className="text-xs text-slate-400 mb-4">
              Instantánea de métricas capturadas al momento exacto de la postulación:
            </p>
            <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 space-y-2 text-xs">
              <p><strong>Creador:</strong> {selectedApplicantMediaKit.display_name}</p>
              <p><strong>Nicho:</strong> {selectedApplicantMediaKit.niche}</p>
              <p><strong>Ubicación:</strong> {selectedApplicantMediaKit.location}</p>
              <p><strong>Versión Media Kit:</strong> v{selectedApplicantMediaKit.media_kit_version || selectedApplicantMediaKit.version || 1}</p>
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
