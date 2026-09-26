import React, { useState } from 'react';
import { useNavigate, NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShieldAlert, Lock, Mail, ArrowRight, AlertCircle, Key } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function AdminLogin() {
  const [email, setEmail] = useState('admin@vault.io');
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
        setError('Access denied. Admin portal requires Cluster Administrator credentials.');
      }
    } catch (err) {
      setError(err.message || 'Invalid admin credentials.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md glass-panel p-8 rounded-3xl border border-purple-800/60 shadow-2xl space-y-6 z-10"
      >
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-600 text-slate-100 shadow-xl glow-purple">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-wider text-purple-200">
            VAULT ADMIN CONSOLE
          </h1>
          <p className="text-xs text-slate-400">Enterprise Infrastructure Gateway</p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Admin Username / Email</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="email"
                required
                placeholder="admin@vault.io"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 text-sm bg-slate-900/60 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-purple-500/50 font-mono"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Admin Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="password"
                required
                placeholder="admin"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 text-sm bg-slate-900/60 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-purple-500/50"
              />
            </div>
          </div>

          <button
            type="submit"
            className="w-full py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 text-slate-100 font-bold text-sm hover:from-purple-500 hover:to-indigo-500 transition-all glow-purple flex items-center justify-center gap-2 mt-2"
          >
            <Key className="w-4 h-4" />
            <span>Authenticate Admin Access</span>
          </button>
        </form>

        <div className="text-center text-xs text-slate-500 pt-2 border-t border-slate-800/80">
          <NavLink to="/login" className="text-slate-400 hover:text-cyan-400 transition-colors">
            ← Return to User Drive Login
          </NavLink>
        </div>
      </motion.div>
    </div>
  );
}
