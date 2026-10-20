import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2Icon, InfoIcon, FolderOpen, X } from 'lucide-react';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';

export interface CompletionAlertProps {
  isOpen: boolean;
  title: string;
  description: string;
  outputPath?: string;
  segmentCount?: number;
  variant?: 'success' | 'info';
  onOpenOutput?: (path?: string) => void;
  onClose: () => void;
}

export const CompletionAlert: React.FC<CompletionAlertProps> = ({
  isOpen,
  title,
  description,
  outputPath,
  segmentCount,
  variant = 'success',
  onOpenOutput,
  onClose,
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.97 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          className="w-full"
        >
          <Alert variant={variant} className="relative shadow-2xl">
            {variant === 'success' ? (
              <CheckCircle2Icon className="text-brand-emerald" />
            ) : (
              <InfoIcon className="text-brand-cyan" />
            )}

            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1">
                <AlertTitle className="text-sm font-semibold flex items-center gap-2">
                  <span>{title}</span>
                  {segmentCount !== undefined && segmentCount > 0 && (
                    <span className="text-[11px] font-mono font-normal px-2 py-0.5 rounded-md bg-brand-emerald-bg/60 text-brand-emerald border border-brand-emerald/30">
                      {segmentCount} ท่อน
                    </span>
                  )}
                </AlertTitle>

                <AlertDescription className="text-xs space-y-1.5">
                  <p>{description}</p>
                  {outputPath && (
                    <p className="font-mono text-[11px] text-content-dim break-all bg-surface-input/60 p-1.5 rounded-lg border border-border-card/60">
                      {outputPath}
                    </p>
                  )}
                </AlertDescription>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {outputPath && onOpenOutput && (
                  <button
                    type="button"
                    onClick={() => onOpenOutput(outputPath)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-brand-indigo/20 hover:bg-brand-indigo/30 border border-brand-indigo/40 text-brand-cyan transition-colors"
                    title="เปิดโฟลเดอร์ไฟล์ผลลัพธ์"
                  >
                    <FolderOpen className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">เปิดโฟลเดอร์</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={onClose}
                  className="p-1 rounded-lg text-content-dim hover:text-content-white hover:bg-white/10 transition-colors"
                  title="ปิดการแจ้งเตือน"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          </Alert>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
