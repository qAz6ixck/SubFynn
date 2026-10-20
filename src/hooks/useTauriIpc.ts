import { useState, useEffect, useCallback, useRef } from 'react';
import { SubtitleSegment, ModelConfig, PipelineProgress, PipelineResult, HardwareStatus } from '../types/subtitle';
import { serializeToSRT, serializeToVTT } from '../utils/timecode';

// Check if running inside Tauri webview
export const isTauriEnvironment = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
};

// Initial sample data for mock testing
const SAMPLE_SEGMENTS: SubtitleSegment[] = [
  {
    id: 1,
    start: 1.25,
    end: 3.42,
    start_str: '00:00:01,250',
    end_str: '00:00:03,420',
    text: 'お疲れ様でした。今日も一日大変でしたね。',
    thai_text: 'เหนื่อยหน่อยนะคะ วันนี้ก็ลำบากทั้งวันเลยนะ',
  },
  {
    id: 2,
    start: 4.1,
    end: 6.85,
    start_str: '00:00:04,100',
    end_str: '00:00:06,850',
    text: 'ゆっくり休んで、お風呂に入ってください。',
    thai_text: 'พักผ่อนให้สบาย แล้วไปอาบน้ำแช่น้ำอุ่นนะคะ',
  },
  {
    id: 3,
    start: 7.2,
    end: 9.6,
    start_str: '00:00:07,200',
    end_str: '00:00:09,600',
    text: '本当にありがとう。すごく助かりました。',
    thai_text: 'ขอบคุณจริงๆ นะ ช่วยได้มากเลย',
  },
  {
    id: 4,
    start: 10.15,
    end: 13.0,
    start_str: '00:00:10,150',
    end_str: '00:00:13,000',
    text: '明日も一緒に頑張りましょうね。',
    thai_text: 'พรุ่งนี้ก็พยายามด้วยกันอีกนะ',
  },
  {
    id: 5,
    start: 13.5,
    end: 16.2,
    start_str: '00:00:13,500',
    end_str: '00:00:16,200',
    text: 'それでは、おやすみなさい。',
    thai_text: 'งั้นก็ ราตรีสวัสดิ์นะคะ',
  },
];

export function useTauriIpc() {
  const [hardware, setHardware] = useState<HardwareStatus>({
    cudaAvailable: false,
    deviceString: 'Checking Hardware...',
  });
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [progress, setProgress] = useState<PipelineProgress>({
    percent: 0,
    stage: 'idle',
    message: 'Ready',
  });

  const progressListenersRef = useRef<((p: PipelineProgress) => void)[]>([]);

  // Register listener for progress
  const onProgress = useCallback((callback: (p: PipelineProgress) => void) => {
    progressListenersRef.current.push(callback);
    return () => {
      progressListenersRef.current = progressListenersRef.current.filter((cb) => cb !== callback);
    };
  }, []);

  const lastProgressRef = useRef<{ percent: number; message: string }>({ percent: -1, message: '' });

  const notifyProgress = useCallback((p: PipelineProgress) => {
    if (
      lastProgressRef.current.percent === p.percent &&
      lastProgressRef.current.message === p.message
    ) {
      return;
    }
    lastProgressRef.current = { percent: p.percent, message: p.message };
    setProgress(p);
    progressListenersRef.current.forEach((cb) => cb(p));
  }, []);

  // Hook up Tauri event listener
  useEffect(() => {
    let unlisten: (() => void) | undefined;

    if (isTauriEnvironment()) {
      import('@tauri-apps/api/event')
        .then(async ({ listen }) => {
          const unlisten1 = await listen<PipelineProgress>('pipeline-progress', (event) => {
            notifyProgress(event.payload);
          });
          const unlisten2 = await listen<PipelineProgress>('engine:progress', (event) => {
            notifyProgress(event.payload);
          });
          unlisten = () => {
            try { unlisten1(); } catch (_) {}
            try { unlisten2(); } catch (_) {}
          };
        })
        .catch((err) => {
          console.warn('Could not attach Tauri progress listeners:', err);
        });

      // Probe hardware status via Tauri invoke
      import('@tauri-apps/api/core')
        .then(({ invoke }) => {
          invoke<{ cuda_available: boolean; device_name?: string }>('get_hardware_status')
            .then((res) => {
              setHardware({
                cudaAvailable: res.cuda_available,
                deviceString: res.cuda_available
                  ? (res.device_name || 'NVIDIA CUDA GPU')
                  : (res.device_name || 'CPU Mode (int8 quantization)'),
              });
            })
            .catch(() => {
              setHardware({
                cudaAvailable: false,
                deviceString: 'CPU Mode (int8 quantization)',
              });
            });
        })
        .catch(() => {
          setHardware({
            cudaAvailable: false,
            deviceString: 'CPU Mode (int8 quantization)',
          });
        });
    } else {
      // In browser preview
      setHardware({
        cudaAvailable: false,
        deviceString: 'Browser Preview (Simulated)',
      });
    }

    return () => {
      if (unlisten) unlisten();
    };
  }, [notifyProgress]);

  // Close splashscreen helper
  const closeSplashscreen = useCallback(async () => {
    if (isTauriEnvironment()) {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('close_splashscreen');
      } catch (err) {
        console.warn('close_splashscreen invoke fallback:', err);
      }
    }
  }, []);

  // Native File Picker Dialog
  const openVideoDialog = useCallback(async (): Promise<string | null> => {
    if (isTauriEnvironment()) {
      try {
        // Attempt native Tauri dialog plugin
        const { open } = await import('@tauri-apps/plugin-dialog');
        const selected = await open({
          multiple: false,
          filters: [
            {
              name: 'Video Files',
              extensions: ['mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'wmv', 'ts'],
            },
          ],
        });
        if (typeof selected === 'string') {
          return selected;
        }
      } catch (err) {
        console.warn('Tauri open dialog failed, attempting invoke fallback:', err);
        try {
          const { invoke } = await import('@tauri-apps/api/core');
          const path = await invoke<string | null>('open_video_dialog');
          if (path) return path;
        } catch (invokeErr) {
          console.warn('invoke open_video_dialog fallback failed:', invokeErr);
        }
      }
    }

    // Browser mock fallback: HTML input element
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'video/*,.mp4,.mkv,.avi,.mov';
      input.onchange = (e) => {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (file) {
          resolve(file.name || 'assets/subfynn_trailer.mp4');
        } else {
          resolve(null);
        }
      };
      input.click();
    });
  }, []);

  // Start processing pipeline
  const startPipeline = useCallback(
    async (videoPath: string, config: ModelConfig): Promise<PipelineResult> => {
      setIsProcessing(true);

      if (isTauriEnvironment()) {
        try {
          const { invoke } = await import('@tauri-apps/api/core');
          const result = await invoke<PipelineResult>('start_pipeline', {
            options: {
              video_path: videoPath,
              model_size: config.whisperModel,
              whisper_model: config.whisperModel,
              gemini_model: config.geminiModel,
              translation_style: config.translationStyle,
              source_lang: config.audioLanguage,
              audio_language: config.audioLanguage,
              gemini_api_key: config.geminiApiKey,
              embed_mode: 'none',
            },
          });
          setIsProcessing(false);
          return result;
        } catch (err) {
          setIsProcessing(false);
          console.error('start_pipeline failed in Tauri:', err);
          throw err;
        }
      }

      // Standalone Browser Simulation Flow (only when outside Tauri)
      const stages = [
        { percent: 10, stage: 'demuxing', message: 'Extracting 16kHz audio stream via FFmpeg...' },
        { percent: 35, stage: 'transcribing', message: `Whisper ${config.whisperModel} transcribing speech (CUDA)...` },
        { percent: 65, stage: 'transcribing', message: 'Speech detected, finalizing timestamps...' },
        { percent: 85, stage: 'translating', message: `Gemini (${config.geminiModel}) translating into Thai [${config.translationStyle}]...` },
        { percent: 98, stage: 'post-processing', message: 'Applying adult Thai slang rules & timing alignment...' },
        { percent: 100, stage: 'complete', message: 'Subtitles successfully generated!' },
      ];

      for (const st of stages) {
        notifyProgress(st);
        await new Promise((r) => setTimeout(r, 650));
      }

      setIsProcessing(false);

      const srt = serializeToSRT(SAMPLE_SEGMENTS);
      const vtt = serializeToVTT(SAMPLE_SEGMENTS);

      return {
        segments: SAMPLE_SEGMENTS,
        srt_content: srt,
        vtt_content: vtt,
        srt_path: videoPath.replace(/\.[^/.]+$/, '') + '.srt',
        vtt_path: videoPath.replace(/\.[^/.]+$/, '') + '.vtt',
      };
    },
    [notifyProgress]
  );

  // Soft-mux subtitles into video
  const softMuxSubtitles = useCallback(
    async (videoPath: string, srtContent: string, outputPath?: string): Promise<string> => {
      setIsProcessing(true);
      notifyProgress({ percent: 15, stage: 'muxing', message: 'Fast-muxing subtitle stream into container...' });

      if (isTauriEnvironment()) {
        try {
          const { invoke } = await import('@tauri-apps/api/core');
          const res = await invoke<{ output_video_path?: string; video_path?: string } | string>('mux_subtitles', {
            videoPath,
            srtContent,
            outputPath: outputPath || '',
          });
          const finalPath = typeof res === 'string' ? res : (res?.output_video_path || res?.video_path || outputPath || '');
          notifyProgress({ percent: 100, stage: 'complete', message: `Muxed video saved: ${finalPath}` });
          setIsProcessing(false);
          return finalPath;
        } catch (err) {
          setIsProcessing(false);
          console.error('mux_subtitles failed in Tauri:', err);
          throw err;
        }
      }

      await new Promise((r) => setTimeout(r, 900));
      const target = outputPath || videoPath.replace(/\.[^/.]+$/, '') + '_subtitled.mkv';
      notifyProgress({ percent: 100, stage: 'complete', message: `Soft-mux completed: ${target}` });
      setIsProcessing(false);
      return target;
    },
    [notifyProgress]
  );

  // Hard burn-in subtitles into video
  const hardBurnSubtitles = useCallback(
    async (videoPath: string, srtContent: string, outputPath?: string): Promise<string> => {
      setIsProcessing(true);
      const stages = [
        { percent: 20, stage: 'burning', message: 'Configuring FFmpeg libx264 hardsub filter (Kanit / Leelawadee UI)...' },
        { percent: 55, stage: 'burning', message: 'Encoding video frames with burned subtitles...' },
        { percent: 85, stage: 'burning', message: 'Finalizing AAC audio muxing...' },
        { percent: 100, stage: 'complete', message: 'Hardsub video burned successfully!' },
      ];

      if (isTauriEnvironment()) {
        try {
          const { invoke } = await import('@tauri-apps/api/core');
          const res = await invoke<{ output_video_path?: string; video_path?: string } | string>('burn_subtitles', {
            videoPath,
            srtContent,
            outputPath: outputPath || '',
          });
          const finalPath = typeof res === 'string' ? res : (res?.output_video_path || res?.video_path || outputPath || '');
          notifyProgress({ percent: 100, stage: 'complete', message: `Burned video saved: ${finalPath}` });
          setIsProcessing(false);
          return finalPath;
        } catch (err) {
          setIsProcessing(false);
          console.error('burn_subtitles failed in Tauri:', err);
          throw err;
        }
      }

      for (const st of stages) {
        notifyProgress(st);
        await new Promise((r) => setTimeout(r, 700));
      }

      const target = outputPath || videoPath.replace(/\.[^/.]+$/, '') + '_burned.mp4';
      setIsProcessing(false);
      return target;
    },
    [notifyProgress]
  );

  // Open directory in Windows Explorer
  const openOutputFolder = useCallback(async (path?: string) => {
    const targetPath = (typeof path === 'string' && path.trim()) ? path.trim() : 'data/output';
    if (isTauriEnvironment()) {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('open_path', { path: targetPath });
        return;
      } catch (err) {
        console.warn('open_path invoke fallback:', err);
      }
    }
    console.info('Opening folder path:', targetPath);
  }, []);

  return {
    hardware,
    isProcessing,
    progress,
    onProgress,
    closeSplashscreen,
    openVideoDialog,
    startPipeline,
    softMuxSubtitles,
    hardBurnSubtitles,
    openOutputFolder,
  };
}
