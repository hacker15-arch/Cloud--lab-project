import React, { useState } from 'react';
import { useNavigate, NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, Lock, Mail, ArrowRight, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const userObj = await login(email, password);
      if (userObj.role === 'admin') {
        navigate('/admin/dashboard');
      } else {
        navigate('/drive');
      }
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md glass-panel p-8 rounded-3xl border border-slate-800 shadow-2xl space-y-6 z-10"
      >
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-gradient-to-tr from-cyan-600 to-emerald-500 text-slate-950 shadow-xl glow-cyan">
            <Shield className="w-8 h-8 fill-current" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-wider bg-gradient-to-r from-slate-100 via-cyan-200 to-emerald-300 bg-clip-text text-transparent">
            VAULT
          </h1>
          <p className="text-xs text-slate-400">Sign in to your Cloud Drive</p>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Credentials Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="email"
                required
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 text-sm bg-slate-900/60 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/50"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 text-sm bg-slate-900/60 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/50"
              />
            </div>
          </div>

          <button
            type="submit"
            className="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-emerald-600 text-slate-950 font-bold text-sm hover:from-cyan-500 hover:to-emerald-500 transition-all glow-cyan flex items-center justify-center gap-2 mt-2"
          >
            <span>Sign In</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-800/80">
          <span>
            Need an account?{' '}
            <NavLink to="/register" className="text-cyan-400 font-semibold hover:underline">
              Register
            </NavLink>
          </span>

          <NavLink to="/admin/login" className="text-slate-500 hover:text-cyan-400 transition-colors">
            Admin Portal →
          </NavLink>
        </div>
      </motion.div>
    </div>
  );
}
