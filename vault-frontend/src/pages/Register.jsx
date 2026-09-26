import React, { useState } from 'react';
import { useNavigate, NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, Lock, Mail, User, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await register(name, email, password);
      navigate('/drive');
    } catch (err) {
      console.error('Registration failed', err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md glass-panel p-8 rounded-3xl border border-slate-800 shadow-2xl space-y-6 z-10"
      >
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-gradient-to-tr from-cyan-600 to-emerald-500 text-slate-950 shadow-xl glow-cyan">
            <Shield className="w-8 h-8 fill-current" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-wider bg-gradient-to-r from-slate-100 via-cyan-200 to-emerald-300 bg-clip-text text-transparent">
            CREATE VAULT ACCOUNT
          </h1>
          <p className="text-xs text-slate-400">Get your personal cloud storage drive</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Full Name</label>
            <div className="relative">
              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                required
                placeholder="Alex Morgan"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 text-sm bg-slate-900/60 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/50"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="email"
                required
                placeholder="alex@example.com"
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
            <span>Create Drive Account</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="text-center text-xs text-slate-500 pt-2 border-t border-slate-800/80">
          Already have an account?{' '}
          <NavLink to="/login" className="text-cyan-400 font-semibold hover:underline">
            Sign in
          </NavLink>
        </div>
      </motion.div>
    </div>
  );
}
