pub mod sidecar;

use std::sync::Arc;
use std::time::Duration;
use tauri::{Manager, State};
use tauri_plugin_dialog::DialogExt;

pub use sidecar::SidecarManager;

/// Closes the splashscreen window and shows/focuses the main window.
#[tauri::command]
fn close_splashscreen(app: tauri::AppHandle) {
    if let Some(splash) = app.get_webview_window("splashscreen") {
        let _ = splash.close();
    }
    if let Some(main) = app.get_webview_window("main") {
        let _ = main.show();
        let _ = main.set_focus();
    }
}

/// Pings the Python sidecar and returns health/status information.
#[tauri::command]
async fn ping_sidecar(
    state: State<'_, Arc<SidecarManager>>,
) -> Result<serde_json::Value, String> {
    state.call_method("engine.ping", None, Some(Duration::from_secs(10)))
}

/// Returns the detected hardware status (CUDA availability and device name)
#[tauri::command]
async fn get_hardware_status(
    state: State<'_, Arc<SidecarManager>>,
) -> Result<serde_json::Value, String> {
    match state.call_method("engine.ping", None, Some(Duration::from_secs(5))) {
        Ok(res) => {
            let cuda = res.get("cuda_available").and_then(|v| v.as_bool()).unwrap_or(false);
            let device_name = if cuda {
                "NVIDIA CUDA GPU (Accelerated)".to_string()
            } else {
                "CPU Mode (int8 quantization)".to_string()
            };
            Ok(serde_json::json!({
                "cuda_available": cuda,
                "device_name": device_name,
            }))
        }
        Err(_) => {
            Ok(serde_json::json!({
                "cuda_available": false,
                "device_name": "CPU Mode (int8 quantization)",
            }))
        }
    }
}

/// Invokes the native file picker filtered to video extensions, returning the absolute file path.
#[tauri::command]
async fn open_video_dialog(
    app: tauri::AppHandle,
) -> Result<Option<String>, String> {
    let video_extensions = ["mp4", "mkv", "mov", "avi", "webm", "flv", "ts", "wmv", "m4v"];
    let file = app
        .dialog()
        .file()
        .add_filter("Video Files", &video_extensions)
        .blocking_pick_file();

    Ok(file.map(|f| match f.clone().into_path() {
        Ok(path) => path.to_string_lossy().to_string(),
        Err(_) => f.to_string(),
    }))
}

/// Starts the video transcription and translation pipeline.
/// Supports both an `options` object argument and flattened parameters.
#[tauri::command]
async fn start_pipeline(
    state: State<'_, Arc<SidecarManager>>,
    options: Option<serde_json::Value>,
    video_path: Option<String>,
    output_dir: Option<String>,
    model_size: Option<String>,
    source_lang: Option<String>,
    gemini_api_key: Option<String>,
    gemini_model: Option<String>,
    translation_style: Option<String>,
    embed_mode: Option<String>,
    font_size: Option<u32>,
) -> Result<serde_json::Value, String> {
    let mut params = match options {
        Some(serde_json::Value::Object(map)) => serde_json::Value::Object(map),
        _ => serde_json::json!({}),
    };

    let map = params.as_object_mut().unwrap();

    if let Some(v) = video_path {
        map.insert("video_path".to_string(), serde_json::Value::String(v));
    }
    if let Some(v) = output_dir {
        map.insert("output_dir".to_string(), serde_json::Value::String(v));
    }
    if let Some(v) = model_size {
        map.insert("model_size".to_string(), serde_json::Value::String(v));
    }
    if let Some(v) = source_lang {
        map.insert("source_lang".to_string(), serde_json::Value::String(v));
    }
    if let Some(v) = gemini_api_key {
        map.insert("gemini_api_key".to_string(), serde_json::Value::String(v));
    }
    if let Some(v) = gemini_model {
        map.insert("gemini_model".to_string(), serde_json::Value::String(v));
    }
    if let Some(v) = translation_style {
        map.insert("translation_style".to_string(), serde_json::Value::String(v));
    }
    if let Some(v) = embed_mode {
        map.insert("embed_mode".to_string(), serde_json::Value::String(v));
    }
    if let Some(v) = font_size {
        map.insert("font_size".to_string(), serde_json::json!(v));
    }

    // Video pipeline execution can take substantial time; allow up to 3 hours
    state.call_method(
        "engine.process_video",
        Some(params),
        Some(Duration::from_secs(10800)),
    )
}

/// Shifts subtitle timestamps by the specified offset in seconds.
#[tauri::command]
async fn shift_subtitles(
    state: State<'_, Arc<SidecarManager>>,
    segments: serde_json::Value,
    offset_seconds: Option<f64>,
) -> Result<serde_json::Value, String> {
    let offset = offset_seconds.unwrap_or(0.0);
    let params = serde_json::json!({
        "segments": segments,
        "offset_seconds": offset
    });

    state.call_method(
        "engine.shift_time",
        Some(params),
        Some(Duration::from_secs(60)),
    )
}

/// Burns subtitles into the video (hardsub) via bundled FFmpeg.
#[tauri::command]
async fn burn_subtitles(
    state: State<'_, Arc<SidecarManager>>,
    video_path: Option<String>,
    srt_content: Option<String>,
    srt_path: Option<String>,
    output_path: Option<String>,
    output_video_path: Option<String>,
    font_size: Option<u32>,
) -> Result<serde_json::Value, String> {
    let v_path = video_path
        .ok_or_else(|| "Missing required parameter 'videoPath' (or 'video_path')".to_string())?;

    let out_path = output_path.or(output_video_path);
    let font = font_size.unwrap_or(18);

    let mut params = serde_json::json!({
        "video_path": v_path,
        "font_size": font,
    });

    if let Some(c) = srt_content {
        params["srt_content"] = serde_json::Value::String(c);
    }
    if let Some(p) = srt_path {
        params["srt_path"] = serde_json::Value::String(p);
    }
    if let Some(o) = out_path {
        params["output_video_path"] = serde_json::Value::String(o);
    }

    state.call_method(
        "engine.burn_subtitles",
        Some(params),
        Some(Duration::from_secs(3600)),
    )
}

/// Muxes subtitles into the video container (softsub) via bundled FFmpeg.
#[tauri::command]
async fn mux_subtitles(
    state: State<'_, Arc<SidecarManager>>,
    video_path: Option<String>,
    srt_content: Option<String>,
    srt_path: Option<String>,
    output_path: Option<String>,
    output_video_path: Option<String>,
) -> Result<serde_json::Value, String> {
    let v_path = video_path
        .ok_or_else(|| "Missing required parameter 'videoPath' (or 'video_path')".to_string())?;

    let out_path = output_path.or(output_video_path);

    let mut params = serde_json::json!({
        "video_path": v_path,
    });

    if let Some(c) = srt_content {
        params["srt_content"] = serde_json::Value::String(c);
    }
    if let Some(p) = srt_path {
        params["srt_path"] = serde_json::Value::String(p);
    }
    if let Some(o) = out_path {
        params["output_video_path"] = serde_json::Value::String(o);
    }

    state.call_method(
        "engine.mux_subtitles",
        Some(params),
        Some(Duration::from_secs(1200)),
    )
}

/// Reveals a file or folder in Windows Explorer.
#[tauri::command]
async fn open_path(path: String) -> Result<(), String> {
    #[cfg(windows)]
    {
        use std::path::Path;
        use std::process::Command;

        let p = Path::new(&path);
        if !p.exists() {
            return Err(format!("Path does not exist: {}", path));
        }

        if p.is_file() {
            Command::new("explorer")
                .args(["/select,", &path])
                .spawn()
                .map_err(|e| format!("Failed to open Windows Explorer: {}", e))?;
        } else {
            Command::new("explorer")
                .arg(&path)
                .spawn()
                .map_err(|e| format!("Failed to open Windows Explorer: {}", e))?;
        }
        Ok(())
    }
    #[cfg(not(windows))]
    {
        let _ = path;
        Ok(())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            close_splashscreen,
            ping_sidecar,
            get_hardware_status,
            open_video_dialog,
            start_pipeline,
            shift_subtitles,
            burn_subtitles,
            mux_subtitles,
            open_path,
        ])
        .setup(|app| {
            // Initialize sidecar manager and register in managed state
            let sidecar = SidecarManager::new(app.handle().clone());
            app.manage(sidecar);
            Ok(())
        })
        .on_window_event(|window, event| {
            // Triple-Lock Lock 2: On main window destruction, shutdown sidecar
            if let tauri::WindowEvent::Destroyed = event {
                if window.label() == "main" {
                    let app = window.app_handle();
                    if let Some(sidecar) = app.try_state::<Arc<SidecarManager>>() {
                        sidecar.shutdown();
                    }
                }
            }
        });

    let app = builder
        .build(tauri::generate_context!())
        .expect("error while building SubFynn application");

    app.run(|app_handle, event| {
        // Triple-Lock Lock 2: On app exit requested, shutdown sidecar
        if let tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit = event {
            if let Some(sidecar) = app_handle.try_state::<Arc<SidecarManager>>() {
                sidecar.shutdown();
            }
        }
    });
}
