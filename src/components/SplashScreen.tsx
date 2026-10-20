import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import appIcon from '../../assets/app_icon.png';

interface SplashScreenProps {
  isVisible: boolean;
  statusMessage: string;
  progressPercent?: number;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({
  isVisible,
  statusMessage,
  progressPercent = 0,
}) => {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          key="splashscreen"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.05, filter: 'blur(12px)' }}
          transition={{ duration: 0.45, ease: 'easeInOut' }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-canvas select-none"
        >
          {/* Ambient Glow Aura */}
          <div className="absolute w-[360px] h-[360px] rounded-full bg-gradient-to-tr from-brand-indigo/25 via-brand-cyan/20 to-brand-pink/20 blur-3xl pointer-events-none" />

          <motion.div
            initial={{ scale: 0.85, y: 15 }}
            animate={{ scale: 1, y: 0 }}
            transition={{ type: 'spring', damping: 20, stiffness: 220 }}
            className="relative flex flex-col items-center p-8 rounded-3xl bg-surface-card border border-border-glass backdrop-blur-glass shadow-glass-card w-[420px]"
          >
            {/* Pulsing Aura Behind 102x102 Logo */}
            <motion.div
              animate={{
                scale: [1, 1.2, 1],
                opacity: [0.35, 0.8, 0.35],
              }}
              transition={{ repeat: Infinity, duration: 2.8, ease: 'easeInOut' }}
              className="absolute top-10 w-[102px] h-[102px] rounded-2xl bg-brand-indigo/35 blur-xl pointer-events-none"
            />

            {/* 102x102 SubFynn Master Logo */}
            <img
              src={appIcon}
              alt="SubFynn Studio Logo"
              className="w-[102px] h-[102px] rounded-2xl shadow-2xl border border-white/20 object-contain z-10"
            />

            {/* Typography */}
            <h1 className="mt-6 text-2xl font-bold tracking-tight text-content-white font-sans">
              SubFynn Studio
            </h1>
            <p className="mt-1 text-xs text-content-muted font-sans tracking-wide">
              AI Thai Subtitle Studio (Tauri v2 Desktop)
            </p>

            {/* Progress / Status Section */}
            <div className="w-full mt-7">
              <div className="flex items-center justify-between text-xs text-content-dim font-mono mb-2">
                <span className="flex items-center gap-2 text-brand-cyan truncate max-w-[280px]">
                  <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
                  <span className="truncate">{statusMessage}</span>
                </span>
                <span className="shrink-0">{Math.round(progressPercent)}%</span>
              </div>

              {/* Progress Shimmer Bar */}
              <div className="w-full h-1.5 bg-surface-input rounded-full overflow-hidden border border-border-glass">
                <motion.div
                  className="h-full bg-gradient-to-r from-brand-indigo via-brand-cyan to-brand-pink"
                  initial={{ width: '0%' }}
                  animate={{ width: `${Math.max(5, Math.min(100, progressPercent))}%` }}
                  transition={{ duration: 0.35 }}
                />
              </div>
            </div>

            <div className="mt-6 text-[11px] text-content-dim font-mono tracking-wider">
              Whisper Large-v3 • Gemini Live Translate
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
