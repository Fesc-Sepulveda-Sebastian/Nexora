import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';
import { Flame, Lock, Mail, User, ShieldCheck, AlertCircle } from 'lucide-react';

interface IU01AuthProps {
  onSuccess: () => void;
}

export const IU01_Auth: React.FC<IU01AuthProps> = ({ onSuccess }) => {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [role, setRole] = useState<UserRole>('creador');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [locationDeclared, setLocationDeclared] = useState('Cúcuta, Colombia');
  const [niche, setNiche] = useState('Gastronomía');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (isRegister && !termsAccepted) {
      setErrorMsg('Debe aceptar los Términos y Condiciones para registrarse en Nexora.');
      return;
    }

    setLoading(true);
    try {
      if (isRegister) {
        await register({
          email,
          password,
          display_name: displayName,
          role,
          location_declared: locationDeclared,
          niche,
          terms_accepted: termsAccepted
        });
      } else {
        await login(email, password);
      }
      onSuccess();
    } catch (e: any) {
      setErrorMsg(e.message || 'Error en la autenticación. Verifique sus datos.');
    } finally {
      setLoading(false);
    }
  };

  const setDemoCredentials = (demoRole: 'brand' | 'creator' | 'admin') => {
    setIsRegister(false);
    if (demoRole === 'brand') {
      setEmail('marca@cucutagourmet.com');
      setPassword('BrandPass123!');
    } else if (demoRole === 'creator') {
      setEmail('sofia@cucutafoodie.com');
      setPassword('CreatorPass123!');
    } else {
      setEmail('admin@nexora.co');
      setPassword('AdminPass123!');
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl backdrop-blur-xl relative overflow-hidden">
        {/* Glow accent */}
        <div className="absolute -top-12 -right-12 w-36 h-36 bg-brand-600/20 rounded-full blur-3xl pointer-events-none" />

        {/* Brand header */}
        <div className="text-center mb-6">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-brand-600 to-purple-600 flex items-center justify-center mx-auto mb-3 shadow-lg shadow-brand-500/30">
            <Flame className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            {isRegister ? 'Crear Cuenta en Nexora' : 'Iniciar Sesión en Nexora'}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Marketplace Mobile-First para Marcas y Creadores de Contenido
          </p>
        </div>

        {/* Demo Fast Logins for Testing */}
        <div className="mb-5 p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-xs">
          <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider block mb-2">
            Credenciales Demo Rápidas:
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setDemoCredentials('brand')}
              className="flex-1 py-1.5 px-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px] font-medium"
            >
              Marca Demo
            </button>
            <button
              type="button"
              onClick={() => setDemoCredentials('creator')}
              className="flex-1 py-1.5 px-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px] font-medium"
            >
              Creador Demo
            </button>
            <button
              type="button"
              onClick={() => setDemoCredentials('admin')}
              className="flex-1 py-1.5 px-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px] font-medium"
            >
              Admin
            </button>
          </div>
        </div>

        {errorMsg && (
          <div role="alert" className="p-3 mb-4 rounded-xl bg-rose-950/80 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Role Toggle in Registration */}
          {isRegister && (
            <div>
              <label className="text-[11px] font-semibold text-slate-300 uppercase block mb-1.5">
                Tipo de Cuenta *
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setRole('creador')}
                  className={`py-2.5 rounded-xl text-xs font-bold min-h-touch transition-all ${
                    role === 'creador'
                      ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                      : 'bg-slate-950 text-slate-400 border border-slate-800'
                  }`}
                >
                  Creador / Influencer
                </button>
                <button
                  type="button"
                  onClick={() => setRole('marca')}
                  className={`py-2.5 rounded-xl text-xs font-bold min-h-touch transition-all ${
                    role === 'marca'
                      ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                      : 'bg-slate-950 text-slate-400 border border-slate-800'
                  }`}
                >
                  Marca / Pyme
                </button>
              </div>
            </div>
          )}

          {isRegister && (
            <div>
              <label className="text-[11px] font-semibold text-slate-300 uppercase block mb-1">
                Nombre Completo o Razón Social *
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                <input
                  type="text"
                  required
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Ej. Sofía Castro"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-3.5 py-3 text-xs text-white focus:outline-none focus:border-brand-500 min-h-touch"
                />
              </div>
            </div>
          )}

          <div>
            <label className="text-[11px] font-semibold text-slate-300 uppercase block mb-1">
              Correo Electrónico *
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@correo.com"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-3.5 py-3 text-xs text-white focus:outline-none focus:border-brand-500 min-h-touch"
              />
            </div>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-300 uppercase block mb-1">
              Contraseña *
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Mínimo 8 caracteres"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-3.5 py-3 text-xs text-white focus:outline-none focus:border-brand-500 min-h-touch"
              />
            </div>
          </div>

          {isRegister && (
            <div className="flex items-start gap-2 pt-1">
              <input
                type="checkbox"
                id="terms"
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                className="mt-1 w-4 h-4 rounded text-brand-600 focus:ring-brand-500"
              />
              <label htmlFor="terms" className="text-[11px] text-slate-400 cursor-pointer">
                Acepto los Términos de Servicio y la Política de Privacidad de Nexora (Habeas Data RNF-12).
              </label>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-bold py-3.5 rounded-xl text-xs min-h-touch shadow-lg shadow-brand-500/25 transition-all mt-2 active:scale-95"
          >
            {loading ? 'Procesando...' : isRegister ? 'Registrarme' : 'Entrar a Nexora'}
          </button>
        </form>

        {/* Switch between Login and Register */}
        <div className="mt-6 pt-4 border-t border-slate-800 text-center">
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setErrorMsg(null);
            }}
            className="text-xs text-brand-400 hover:text-brand-300 font-semibold min-h-touch"
          >
            {isRegister
              ? '¿Ya tienes una cuenta? Inicia sesión aquí'
              : '¿No tienes cuenta aún? Regístrate gratis'}
          </button>
        </div>
      </div>
    </div>
  );
};
