import React, { useState, useEffect } from 'react';
import {
  Zap,
  Cpu,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import appIcon from '../assets/app_icon.png';
import { ModelConfig } from './types/subtitle';
import { useTauriIpc } from './hooks/useTauriIpc';
import { useSubtitleEditor } from './hooks/useSubtitleEditor';
import { SplashScreen } from './components/SplashScreen';
import { VideoDropzone } from './components/VideoDropzone';
import { ModelControls } from './components/ModelControls';
import { ActionButtons } from './components/ActionButtons';
import { ProgressBar } from './components/ProgressBar';
import { SubtitleEditor } from './components/SubtitleEditor';
import { CompletionAlert } from './components/CompletionAlert';

export const App: React.FC = () => {
  // Splashscreen lifecycle state
  const [showSplash, setShowSplash] = useState<boolean>(true);
  const [splashStatus, setSplashStatus] = useState<string>('Initializing Python Engine...');
  const [splashPercent, setSplashPercent] = useState<number>(15);

  // Selected Video Path
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);

  // Completion Alert state
  const [completionAlert, setCompletionAlert] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    outputPath?: string;
    segmentCount?: number;
    variant: 'success' | 'info' | 'destructive';
  }>({
    isOpen: false,
    title: '',
    description: '',
    outputPath: undefined,
    segmentCount: undefined,
    variant: 'success',
  });

  // Model Configuration State
  const [modelConfig, setModelConfig] = useState<ModelConfig>({
    whisperModel: 'base',
    geminiModel: 'gemini-3.5-live-translate-preview',
    translationStyle: 'jav_dirty',
    audioLanguage: 'ja',
    geminiApiKey: '',
  });

  // Tauri IPC Hook
  const {
    hardware,
    isProcessing,
    progress,
    closeSplashscreen,
    openVideoDialog,
    startPipeline,
    softMuxSubtitles,
    hardBurnSubtitles,
    openOutputFolder,
  } = useTauriIpc();

  // Subtitle Editor State & Actions
  const {
    segments,
    filteredSegments,
    searchQuery,
    setSearchQuery,
    selectedSegmentId,
    setSelectedSegmentId,
    setSegments,
    updateSegment,
    deleteSegment,
    addSegment,
    applyTimeShift,
    canUndo,
    canRedo,
    undo,
    redo,
    exportSRT,
    downloadSRT,
    downloadVTT,
    copySRTToClipboard,
  } = useSubtitleEditor([]);

  // Simulate or manage startup initialization sequence
  useEffect(() => {
    let t1: NodeJS.Timeout;
    let t2: NodeJS.Timeout;
    let t3: NodeJS.Timeout;

    t1 = setTimeout(() => {
      setSplashStatus('Checking CUDA Hardware Acceleration...');
      setSplashPercent(55);
    }, 400);

    t2 = setTimeout(() => {
      setSplashStatus('SubFynn Ready');
      setSplashPercent(100);
    }, 900);

    t3 = setTimeout(() => {
      setShowSplash(false);
      closeSplashscreen();
    }, 1350);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [closeSplashscreen]);

  // Video picker handler
  const handleSelectVideo = async () => {
    const picked = await openVideoDialog();
    if (picked) {
      setSelectedVideo(picked);
    }
  };

  const handleClearVideo = () => {
    setSelectedVideo(null);
  };

  const handleDropPath = (path: string) => {
    setSelectedVideo(path);
  };

  // Auto-detect fast model if CUDA is not available
  useEffect(() => {
    if (!hardware.cudaAvailable) {
      setModelConfig((prev) => {
        if (prev.whisperModel === 'large-v3') {
          return { ...prev, whisperModel: 'base' };
        }
        return prev;
      });
    }
  }, [hardware.cudaAvailable]);

  // Model configuration update
  const handleConfigChange = (updates: Partial<ModelConfig>) => {
    setModelConfig((prev) => ({ ...prev, ...updates }));
  };

  // Pipeline Execution Triggers
  const handleTranscribeAndTranslate = async () => {
    if (!selectedVideo || isProcessing) return;
    setCompletionAlert((prev) => ({ ...prev, isOpen: false }));
    try {
      const result = await startPipeline(selectedVideo, modelConfig);
      if (result.segments && result.segments.length > 0) {
        setSegments(result.segments);
      }
      const outPath = result.video_output_path || result.srt_path || '';
      setCompletionAlert({
        isOpen: true,
        title: 'ถอดความและแปลภาษาไทยสำเร็จ',
        description: `สร้างคำบรรยายสำเร็จทั้งหมด ${result.segments?.length || 0} ท่อน บันทึกไฟล์พร้อมใช้งาน`,
        outputPath: outPath,
        segmentCount: result.segments?.length || 0,
        variant: 'success',
      });
    } catch (err: any) {
      console.error('Pipeline transcription error:', err);
      const errMsg = typeof err === 'string' ? err : (err?.message || 'เกิดข้อผิดพลาดในการประมวลผลวิดีโอ');
      setCompletionAlert({
        isOpen: true,
        title: 'การประมวลผลไม่สำเร็จ',
        description: errMsg,
        outputPath: undefined,
        segmentCount: undefined,
        variant: 'destructive',
      });
    }
  };

  const handleSoftMux = async () => {
    if (!selectedVideo || segments.length === 0 || isProcessing) return;
    setCompletionAlert((prev) => ({ ...prev, isOpen: false }));
    const srt = exportSRT();
    try {
      const finalPath = await softMuxSubtitles(selectedVideo, srt);
      setCompletionAlert({
        isOpen: true,
        title: 'ฝังซับไตเติล (Softsub) สำเร็จ',
        description: 'ฝังแทร็กซับไตเติลภาษาไทยลงในคอนเทนเนอร์วิดีโอเรียบร้อย โดยไม่สูญเสียความละเอียด',
        outputPath: typeof finalPath === 'string' ? finalPath : '',
        segmentCount: segments.length,
        variant: 'success',
      });
    } catch (err: any) {
      console.error('Softsub error:', err);
      const errMsg = typeof err === 'string' ? err : (err?.message || 'เกิดข้อผิดพลาดในการฝังซับไตเติล');
      setCompletionAlert({
        isOpen: true,
        title: 'การฝังซับไตเติลไม่สำเร็จ',
        description: errMsg,
        outputPath: undefined,
        segmentCount: undefined,
        variant: 'destructive',
      });
    }
  };

  const handleHardBurn = async () => {
    if (!selectedVideo || segments.length === 0 || isProcessing) return;
    setCompletionAlert((prev) => ({ ...prev, isOpen: false }));
    const srt = exportSRT();
    try {
      const finalPath = await hardBurnSubtitles(selectedVideo, srt);
      setCompletionAlert({
        isOpen: true,
        title: 'เบิร์นซับไตเติล (Hardsub) สำเร็จ',
        description: 'เรนเดอร์ตัวอักษรภาษาไทยลงบนวิดีโอเรียบร้อย สามารถเปิดดูได้ทันทีทุกอุปกรณ์',
        outputPath: typeof finalPath === 'string' ? finalPath : '',
        segmentCount: segments.length,
        variant: 'success',
      });
    } catch (err: any) {
      console.error('Hardburn error:', err);
      const errMsg = typeof err === 'string' ? err : (err?.message || 'เกิดข้อผิดพลาดในการเบิร์นซับไตเติล');
      setCompletionAlert({
        isOpen: true,
        title: 'การเบิร์นซับไตเติลไม่สำเร็จ',
        description: errMsg,
        outputPath: undefined,
        segmentCount: undefined,
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="min-h-screen bg-canvas text-content-white relative overflow-x-hidden flex flex-col font-sans">
      {/* Ambient Radial Background Glows */}
      <div className="ambient-background" />

      {/* Animated SplashScreen (Entrance & Exit Transition) */}
      <SplashScreen
        isVisible={showSplash}
        statusMessage={splashStatus}
        progressPercent={splashPercent}
      />

      {/* Application Main Layout */}
      <div className="relative z-10 flex-1 flex flex-col max-w-7xl w-full mx-auto px-4 sm:px-6 py-5 gap-5">
        {/* Top Navigation Bar */}
        <header className="glass-card glass-card-specular px-5 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <img
                src={appIcon}
                alt="SubFynn Logo"
                className="w-9 h-9 rounded-xl border border-white/20 object-contain shadow-md"
              />
              <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-brand-emerald ring-2 ring-canvas" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-content-white font-sans">
                  SubFynn
                </h1>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-brand-indigo/20 border border-brand-indigo/35 text-brand-cyan uppercase tracking-wider">
                  v2.0
                </span>
              </div>
            </div>
          </div>

          {/* Right Status Indicators */}
          <div className="flex items-center gap-3">
            {/* Hardware Acceleration Badge */}
            <div
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono border transition-colors ${
                hardware.cudaAvailable
                  ? 'bg-brand-emerald-bg text-brand-emerald border-brand-emerald/40'
                  : 'bg-amber-950/40 text-amber-400 border-amber-600/40'
              }`}
              title={hardware.deviceString}
            >
              {hardware.cudaAvailable ? (
                <Zap className="w-3.5 h-3.5 text-brand-emerald" />
              ) : (
                <Cpu className="w-3.5 h-3.5 text-amber-400" />
              )}
              <span className="hidden sm:inline">
                {hardware.cudaAvailable ? 'CUDA GPU Active' : 'CPU Mode'}
              </span>
            </div>

            {/* Pipeline Status Indicator */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-surface-card border border-border-card text-content-muted">
              {isProcessing ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 text-brand-cyan animate-spin" />
                  <span className="hidden md:inline">Processing</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-brand-emerald" />
                  <span className="hidden md:inline">Ready</span>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Video Dropzone */}
        <VideoDropzone
          selectedVideo={selectedVideo}
          onSelectVideo={handleSelectVideo}
          onClearVideo={handleClearVideo}
          onDropPath={handleDropPath}
          disabled={isProcessing}
        />

        {/* Model Controls */}
        <ModelControls
          config={modelConfig}
          onChange={handleConfigChange}
          disabled={isProcessing}
          cudaAvailable={hardware.cudaAvailable}
        />

        {/* Primary Action Buttons */}
        <ActionButtons
          onTranscribe={handleTranscribeAndTranslate}
          onSoftMux={handleSoftMux}
          onHardBurn={handleHardBurn}
          onOpenOutput={() => openOutputFolder(completionAlert.outputPath)}
          hasVideo={!!selectedVideo}
          hasSegments={segments.length > 0}
          isProcessing={isProcessing}
        />

        {/* Completion Alert Notification */}
        <CompletionAlert
          isOpen={completionAlert.isOpen}
          title={completionAlert.title}
          description={completionAlert.description}
          outputPath={completionAlert.outputPath}
          segmentCount={completionAlert.segmentCount}
          variant={completionAlert.variant}
          onOpenOutput={(path) => openOutputFolder(path)}
          onClose={() => setCompletionAlert((prev) => ({ ...prev, isOpen: false }))}
        />

        {/* Real-Time Progress Bar */}
        <ProgressBar progress={progress} isProcessing={isProcessing} />

        {/* Interactive Live Subtitle Editor */}
        <SubtitleEditor
          segments={segments}
          filteredSegments={filteredSegments}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          selectedSegmentId={selectedSegmentId}
          onSelectSegment={setSelectedSegmentId}
          onUpdateSegment={updateSegment}
          onDeleteSegment={deleteSegment}
          onAddSegment={addSegment}
          onApplyShift={applyTimeShift}
          canUndo={canUndo}
          canRedo={canRedo}
          onUndo={undo}
          onRedo={redo}
          onDownloadSRT={() => downloadSRT()}
          onDownloadVTT={() => downloadVTT()}
          onCopyClipboard={copySRTToClipboard}
          disabled={isProcessing}
        />

        {/* Footer */}
        <footer className="py-2 flex items-center justify-between text-xs text-content-dim font-mono border-t border-border-glass mt-auto">
          <span>SubFynn • AI Thai Subtitles</span>
          <span>v2.0</span>
        </footer>
      </div>
    </div>
  );
};

export default App;
