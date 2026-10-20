import React, { useState, DragEvent } from 'react';
import { FileVideo, UploadCloud, CheckCircle2, FolderOpen, X } from 'lucide-react';

interface VideoDropzoneProps {
  selectedVideo: string | null;
  onSelectVideo: () => void;
  onClearVideo: () => void;
  onDropPath: (path: string) => void;
  disabled?: boolean;
}

export const VideoDropzone: React.FC<VideoDropzoneProps> = ({
  selectedVideo,
  onSelectVideo,
  onClearVideo,
  onDropPath,
  disabled = false,
}) => {
  const [isDragOver, setIsDragOver] = useState<boolean>(false);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      // On web browser file.name, or in Tauri webview window native path might be file.name
      onDropPath(file.name || 'video_input.mp4');
    }
  };

  const getFileName = (path: string) => {
    const parts = path.split(/[/\\]/);
    return parts[parts.length - 1] || path;
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`glass-card glass-card-specular p-5 transition-all duration-300 relative ${
        isDragOver
          ? 'border-brand-indigo ring-2 ring-brand-indigo/40 bg-surface-card-hover'
          : 'hover:border-white/15'
      }`}
    >
      {selectedVideo ? (
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3.5 min-w-0">
            <div className="w-12 h-12 rounded-xl bg-brand-indigo/15 border border-brand-indigo/30 flex items-center justify-center shrink-0">
              <FileVideo className="w-6 h-6 text-brand-indigo" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-brand-cyan flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-brand-emerald" />
                  Target Video Selected
                </span>
              </div>
              <h3 className="text-sm font-medium text-content-white truncate mt-0.5" title={selectedVideo}>
                {getFileName(selectedVideo)}
              </h3>
              <p className="text-xs text-content-dim font-mono truncate mt-0.5" title={selectedVideo}>
                {selectedVideo}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={onSelectVideo}
              disabled={disabled}
              className="px-3 py-1.5 rounded-lg bg-surface-input hover:bg-surface-dropdown border border-border-card text-xs text-content-muted hover:text-white transition-colors flex items-center gap-1.5"
            >
              <FolderOpen className="w-3.5 h-3.5 text-brand-cyan" />
              Change
            </button>
            <button
              type="button"
              onClick={onClearVideo}
              disabled={disabled}
              title="Remove video"
              className="p-1.5 rounded-lg bg-surface-input hover:bg-brand-rose/20 hover:text-brand-rose border border-border-card text-content-dim transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      ) : (
        <div
          onClick={() => !disabled && onSelectVideo()}
          className="cursor-pointer py-6 flex flex-col items-center justify-center text-center group"
        >
          <div className="w-14 h-14 rounded-2xl bg-surface-input border border-border-card flex items-center justify-center mb-3 group-hover:border-brand-indigo/50 group-hover:bg-brand-indigo/10 group-hover:scale-105 transition-all duration-300">
            <UploadCloud className="w-7 h-7 text-content-dim group-hover:text-brand-cyan transition-colors" />
          </div>
          <p className="text-sm font-medium text-content-white group-hover:text-brand-cyan transition-colors">
            Drag & Drop video file here, or click to browse
          </p>
          <p className="text-xs text-content-dim mt-1 font-mono">
            Supports MP4, MKV, AVI, MOV, WEBM (bundled FFmpeg 9.0)
          </p>
        </div>
      )}
    </div>
  );
};
