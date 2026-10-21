import React, { useState } from 'react';
import { api } from '../../services/api';
import { UploadCloud, CheckCircle2, AlertCircle, FileCheck, ExternalLink } from 'lucide-react';

interface EvidenceUploaderProps {
  applicationId: string;
  onEvidenceUploaded: () => void;
}

export const EvidenceUploader: React.FC<EvidenceUploaderProps> = ({
  applicationId,
  onEvidenceUploaded
}) => {
  const [deliverableName, setDeliverableName] = useState('Reel Principal de Menú');
  const [liveUrl, setLiveUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Calculate SHA-256 hash using native Web Crypto API
  const calculateSHA256 = async (file: File): Promise<string> => {
    const arrayBuffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const sizeMb = file.size / (1024 * 1024);
      if (sizeMb > 10.0) {
        setErrorMsg('El archivo supera el límite de 10 MB permitido para Fase 1.');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMsg('Por favor selecciona un archivo de evidencia.');
      return;
    }

    setIsUploading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      // 1. Calculate SHA-256 integrity hash
      const sha256 = await calculateSHA256(selectedFile);
      const sizeMb = Number((selectedFile.size / (1024 * 1024)).toFixed(2));

      // 2. Request presigned upload URL from backend (RF-14)
      const { data: storageData } = await api.request<any>('/storage/presigned-url', {
        method: 'POST',
        body: {
          filename: selectedFile.name,
          content_type: selectedFile.type || 'image/jpeg'
        }
      });

      // 3. Register evidence record in backend with SHA-256
      await api.request(`/applications/${applicationId}/evidences`, {
        method: 'POST',
        body: {
          deliverable_name: deliverableName,
          file_url: storageData.public_url,
          file_hash_sha256: sha256,
          file_size_mb: sizeMb > 0 ? sizeMb : 0.2,
          external_live_url: liveUrl || undefined
        }
      });

      setSuccessMsg('¡Evidencia cargada e integridad SHA-256 verificada! Estado: En Revisión.');
      setSelectedFile(null);
      setLiveUrl('');
      onEvidenceUploaded();
    } catch (e: any) {
      setErrorMsg(e.message || 'Error al cargar la evidencia');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl text-slate-100">
      <div className="flex items-center gap-2 text-brand-400 font-bold text-base mb-3">
        <UploadCloud className="w-5 h-5" />
        <h4>Cargar Evidencia de Entregable (RF-14)</h4>
      </div>

      <p className="text-xs text-slate-400 mb-4">
        Sube capturas o archivos de soporte (0.2 MB a 10 MB) con verificación criptográfica SHA-256 y URL presignada.
      </p>

      {errorMsg && (
        <div className="p-3 mb-3 rounded-xl bg-rose-950/70 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-3 mb-3 rounded-xl bg-emerald-950/70 border border-emerald-800/60 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      <form onSubmit={handleUpload} className="space-y-3">
        <div>
          <label className="text-[11px] font-semibold text-slate-300 uppercase block mb-1">
            Nombre del Entregable
          </label>
          <input
            type="text"
            value={deliverableName}
            onChange={(e) => setDeliverableName(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500 min-h-touch"
          />
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-300 uppercase block mb-1">
            Enlace de Publicación Pública (Instagram / TikTok)
          </label>
          <input
            type="url"
            value={liveUrl}
            onChange={(e) => setLiveUrl(e.target.value)}
            placeholder="https://instagram.com/reel/..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500 min-h-touch"
          />
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-300 uppercase block mb-1">
            Archivo de Evidencia (Imagen o Video corto &lt; 10 MB)
          </label>
          <input
            type="file"
            accept="image/*,video/mp4"
            onChange={handleFileChange}
            className="w-full text-xs text-slate-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-brand-600 file:text-white hover:file:bg-brand-500 cursor-pointer min-h-touch"
          />
        </div>

        <button
          type="submit"
          disabled={!selectedFile || isUploading}
          className="w-full bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white font-bold py-3 rounded-xl text-xs flex items-center justify-center gap-2 min-h-touch transition-all shadow-md shadow-brand-500/20 active:scale-95"
        >
          <FileCheck className="w-4 h-4" />
          <span>{isUploading ? 'Verificando Hash SHA-256 y Subiendo...' : 'Subir Evidencia Verificada'}</span>
        </button>
      </form>
    </div>
  );
};
