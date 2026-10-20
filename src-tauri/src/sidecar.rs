use std::collections::HashMap;
use std::io::{BufRead, BufReader, BufWriter, Write};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::mpsc::{sync_channel, Receiver, RecvTimeoutError, SyncSender};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::{Emitter, Manager};

#[cfg(windows)]
use std::os::windows::io::AsRawHandle;
#[cfg(windows)]
use std::os::windows::process::CommandExt;

/// Windows NT Job Object wrapper ensuring automatic cleanup of child
/// and grandchild processes (e.g. FFmpeg) if Tauri exits or crashes.
#[cfg(windows)]
pub struct WindowsJobObject {
    handle: windows_sys::Win32::Foundation::HANDLE,
}

#[cfg(windows)]
unsafe impl Send for WindowsJobObject {}
#[cfg(windows)]
unsafe impl Sync for WindowsJobObject {}

#[cfg(windows)]
impl WindowsJobObject {
    pub fn create_kill_on_close() -> Result<Self, String> {
        use std::mem::size_of;
        use windows_sys::Win32::Foundation::{CloseHandle, HANDLE};
        use windows_sys::Win32::System::JobObjects::{
            CreateJobObjectW, JobObjectExtendedLimitInformation, SetInformationJobObject,
            JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
        };

        unsafe {
            let handle: HANDLE = CreateJobObjectW(core::ptr::null(), core::ptr::null());
            if handle.is_null() {
                return Err("Failed to create Windows Job Object".to_string());
            }

            let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;

            let success = SetInformationJobObject(
                handle,
                JobObjectExtendedLimitInformation,
                &info as *const _ as *const core::ffi::c_void,
                size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            );

            if success == 0 {
                CloseHandle(handle);
                return Err("Failed to set JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE on Job Object".to_string());
            }

            Ok(Self { handle })
        }
    }

    pub fn assign_process(&self, process_handle: windows_sys::Win32::Foundation::HANDLE) -> Result<(), String> {
        use windows_sys::Win32::System::JobObjects::AssignProcessToJobObject;

        unsafe {
            let success = AssignProcessToJobObject(self.handle, process_handle);
            if success == 0 {
                return Err("Failed to assign child process to Windows Job Object".to_string());
            }
            Ok(())
        }
    }
}

#[cfg(windows)]
impl Drop for WindowsJobObject {
    fn drop(&mut self) {
        if !self.handle.is_null() {
            unsafe {
                windows_sys::Win32::Foundation::CloseHandle(self.handle);
            }
        }
    }
}

/// Represents an active Python sidecar process.
struct ActiveChild {
    child: Child,
    stdin: BufWriter<ChildStdin>,
    #[cfg(windows)]
    _job: WindowsJobObject,
}

/// Manages the Python Engine Sidecar process lifecycle, NDJSON IPC,
/// and streaming progress event forwarding to the Tauri frontend.
pub struct SidecarManager {
    app_handle: tauri::AppHandle,
    active_child: Mutex<Option<ActiveChild>>,
    pending_requests: Arc<Mutex<HashMap<u64, SyncSender<serde_json::Value>>>>,
    next_id: AtomicU64,
}

impl SidecarManager {
    /// Creates and initializes a new SidecarManager wrapped in an Arc.
    pub fn new(app_handle: tauri::AppHandle) -> Arc<Self> {
        let manager = Arc::new(Self {
            app_handle,
            active_child: Mutex::new(None),
            pending_requests: Arc::new(Mutex::new(HashMap::new())),
            next_id: AtomicU64::new(1),
        });

        // Attempt initial spawn eagerly in background
        let mgr_clone = manager.clone();
        std::thread::spawn(move || {
            if let Err(e) = mgr_clone.ensure_running() {
                eprintln!("[SidecarManager] Initial spawn warning: {}", e);
            }
        });

        manager
    }

    /// Resolves the Python executable to use for launching the sidecar.
    fn resolve_python_exe() -> String {
        if let Ok(val) = std::env::var("SUBFYNN_PYTHON") {
            if !val.trim().is_empty() {
                return val;
            }
        }
        "python".to_string()
    }

    /// Resolves the absolute path to `engine_sidecar.py`.
    fn resolve_script_path(&self) -> Result<std::path::PathBuf, String> {
        if let Ok(env_path) = std::env::var("SUBFYNN_SIDECAR_SCRIPT") {
            let p = std::path::PathBuf::from(env_path);
            if p.is_file() {
                return Ok(p);
            }
        }

        let mut candidates = Vec::new();

        // 1. Current working directory
        if let Ok(cwd) = std::env::current_dir() {
            candidates.push(cwd.join("engine_sidecar.py"));
            candidates.push(cwd.join("..").join("engine_sidecar.py"));
        }

        // 2. Tauri resource directory
        if let Ok(res_dir) = self.app_handle.path().resource_dir() {
            candidates.push(res_dir.join("engine_sidecar.py"));
            candidates.push(res_dir.join("resources").join("engine_sidecar.py"));
            candidates.push(res_dir.join("..").join("engine_sidecar.py"));
        }

        // 3. Current executable directory
        if let Ok(exe_path) = std::env::current_exe() {
            if let Some(parent) = exe_path.parent() {
                candidates.push(parent.join("engine_sidecar.py"));
                candidates.push(parent.join("resources").join("engine_sidecar.py"));
                candidates.push(parent.join("..").join("engine_sidecar.py"));
                candidates.push(parent.join("..").join("..").join("engine_sidecar.py"));
            }
        }

        for cand in candidates {
            if cand.is_file() {
                return Ok(cand);
            }
        }

        // Fallback relative path
        let fallback = std::path::PathBuf::from("engine_sidecar.py");
        if fallback.is_file() {
            return Ok(fallback);
        }

        Err("Could not find engine_sidecar.py in workspace or resource paths".to_string())
    }

    /// Resolves the path to the bundled FFmpeg binary if available.
    fn resolve_ffmpeg_path(&self) -> Option<std::path::PathBuf> {
        if let Ok(env_val) = std::env::var("SUBFYNN_FFMPEG_PATH") {
            let p = std::path::PathBuf::from(env_val);
            if p.is_file() {
                return Some(p);
            }
        }

        let mut candidates = Vec::new();

        if let Ok(cwd) = std::env::current_dir() {
            candidates.push(cwd.join("ffmpeg.exe"));
            candidates.push(cwd.join("..").join("ffmpeg.exe"));
        }

        if let Ok(res_dir) = self.app_handle.path().resource_dir() {
            candidates.push(res_dir.join("ffmpeg.exe"));
            candidates.push(res_dir.join("resources").join("ffmpeg.exe"));
        }

        if let Ok(exe) = std::env::current_exe() {
            if let Some(parent) = exe.parent() {
                candidates.push(parent.join("ffmpeg.exe"));
                candidates.push(parent.join("resources").join("ffmpeg.exe"));
            }
        }

        for cand in candidates {
            if cand.is_file() {
                return Some(cand);
            }
        }

        None
    }

    /// Ensures the sidecar process is currently running and ready to accept requests.
    pub fn ensure_running(&self) -> Result<(), String> {
        let mut guard = self.active_child.lock().map_err(|e| e.to_string())?;

        // Check if existing child is still running
        if let Some(ref mut active) = *guard {
            match active.child.try_wait() {
                Ok(None) => return Ok(()), // Still running
                _ => {
                    // Process exited, drop and re-spawn
                    *guard = None;
                }
            }
        }

        let python_exe = Self::resolve_python_exe();
        let script_path = self.resolve_script_path()?;

        let mut cmd = Command::new(&python_exe);
        if let Some(parent) = script_path.parent() {
            cmd.current_dir(parent);
            if let Ok(cur_pythonpath) = std::env::var("PYTHONPATH") {
                cmd.env("PYTHONPATH", format!("{};{}", parent.display(), cur_pythonpath));
            } else {
                cmd.env("PYTHONPATH", parent);
            }
        }
        cmd.arg(&script_path);
        cmd.stdin(Stdio::piped());
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::inherit());

        // On Windows: CREATE_NO_WINDOW (0x08000000)
        #[cfg(windows)]
        cmd.creation_flags(0x08000000);

        // Pass ffmpeg path and directory if discovered
        if let Some(ff) = self.resolve_ffmpeg_path() {
            cmd.env("SUBFYNN_FFMPEG_PATH", &ff);
            if let Some(dir) = ff.parent() {
                if let Ok(cur_path) = std::env::var("PATH") {
                    cmd.env("PATH", format!("{};{}", dir.display(), cur_path));
                }
            }
        }

        let mut child = cmd
            .spawn()
            .map_err(|e| format!("Failed to spawn sidecar process ({} {}): {}", python_exe, script_path.display(), e))?;

        // Windows NT Job Object configuration (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
        #[cfg(windows)]
        let job = {
            let job_obj = WindowsJobObject::create_kill_on_close()?;
            let child_raw_handle = child.as_raw_handle();
            job_obj.assign_process(child_raw_handle as windows_sys::Win32::Foundation::HANDLE)?;
            job_obj
        };

        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| "Failed to capture sidecar child stdin".to_string())?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "Failed to capture sidecar child stdout".to_string())?;

        let stdin_writer = BufWriter::new(stdin);

        // Spawn asynchronous stdout reader thread
        let app_handle_clone = self.app_handle.clone();
        let pending_clone = self.pending_requests.clone();

        std::thread::Builder::new()
            .name("subfynn-sidecar-reader".to_string())
            .spawn(move || {
                let reader = BufReader::new(stdout);
                for line_result in reader.lines() {
                    let line = match line_result {
                        Ok(l) => l,
                        Err(e) => {
                            eprintln!("[Sidecar Reader] EOF or pipe read error: {}", e);
                            break;
                        }
                    };

                    let trimmed = line.trim();
                    if trimmed.is_empty() {
                        continue;
                    }

                    // Parse NDJSON line
                    let parsed: serde_json::Value = match serde_json::from_str(trimmed) {
                        Ok(v) => v,
                        Err(e) => {
                            eprintln!("[Sidecar Reader] Skipping non-JSON output: {} (error: {})", trimmed, e);
                            continue;
                        }
                    };

                    // Detect streaming progress events
                    if parsed.get("type").and_then(|t| t.as_str()) == Some("progress") {
                        let payload = parsed.get("data").unwrap_or(&parsed);
                        if let Err(emit_err) = app_handle_clone.emit("pipeline-progress", payload) {
                            eprintln!("[Sidecar Reader] Error emitting pipeline-progress: {}", emit_err);
                        }
                        if let Err(emit_err) = app_handle_clone.emit("engine:progress", payload) {
                            eprintln!("[Sidecar Reader] Error emitting engine:progress: {}", emit_err);
                        }
                    } else if let Some(id_val) = parsed.get("id") {
                        // Route RPC response to awaiting command caller
                        if let Some(req_id) = id_val.as_u64() {
                            let mut waiters = match pending_clone.lock() {
                                Ok(w) => w,
                                Err(p) => p.into_inner(),
                            };
                            if let Some(sender) = waiters.remove(&req_id) {
                                let _ = sender.send(parsed);
                            }
                        }
                    }
                }

                // If reader loop exited, notify any remaining pending requests
                let mut waiters = match pending_clone.lock() {
                    Ok(w) => w,
                    Err(p) => p.into_inner(),
                };
                for (_, sender) in waiters.drain() {
                    let err_resp = serde_json::json!({
                        "id": null,
                        "result": null,
                        "error": { "code": -32000, "message": "Sidecar process terminated unexpectedly" }
                    });
                    let _ = sender.send(err_resp);
                }
            })
            .map_err(|e| format!("Failed to spawn sidecar reader thread: {}", e))?;

        *guard = Some(ActiveChild {
            child,
            stdin: stdin_writer,
            #[cfg(windows)]
            _job: job,
        });

        Ok(())
    }

    /// Sends an NDJSON RPC request to the Python sidecar and waits for the response.
    pub fn call_method(
        &self,
        method: &str,
        params: Option<serde_json::Value>,
        timeout: Option<Duration>,
    ) -> Result<serde_json::Value, String> {
        self.ensure_running()?;

        let req_id = self.next_id.fetch_add(1, Ordering::SeqCst);
        let request_obj = serde_json::json!({
            "id": req_id,
            "method": method,
            "params": params.unwrap_or(serde_json::json!({}))
        });

        let line = serde_json::to_string(&request_obj)
            .map_err(|e| format!("Failed to serialize RPC request: {}", e))?
            + "\n";

        let (tx, rx): (SyncSender<serde_json::Value>, Receiver<serde_json::Value>) = sync_channel(1);

        {
            let mut waiters = self.pending_requests.lock().map_err(|e| e.to_string())?;
            waiters.insert(req_id, tx);
        }

        // Write request NDJSON to stdin with immediate flush
        {
            let mut guard = self.active_child.lock().map_err(|e| e.to_string())?;
            let active = guard
                .as_mut()
                .ok_or_else(|| "Sidecar process is not running".to_string())?;

            active
                .stdin
                .write_all(line.as_bytes())
                .map_err(|e| format!("Failed to write to sidecar stdin: {}", e))?;
            active
                .stdin
                .flush()
                .map_err(|e| format!("Failed to flush sidecar stdin: {}", e))?;
        }

        // Await response
        let resp_val = match timeout {
            Some(dur) => match rx.recv_timeout(dur) {
                Ok(val) => val,
                Err(RecvTimeoutError::Timeout) => {
                    let mut waiters = self.pending_requests.lock().unwrap_or_else(|p| p.into_inner());
                    waiters.remove(&req_id);
                    return Err(format!(
                        "Sidecar request #{} ('{}') timed out after {:?}",
                        req_id, method, dur
                    ));
                }
                Err(RecvTimeoutError::Disconnected) => {
                    let mut waiters = self.pending_requests.lock().unwrap_or_else(|p| p.into_inner());
                    waiters.remove(&req_id);
                    return Err(format!(
                        "Sidecar pipe disconnected while awaiting request #{} ('{}')",
                        req_id, method
                    ));
                }
            },
            None => match rx.recv() {
                Ok(val) => val,
                Err(_) => {
                    let mut waiters = self.pending_requests.lock().unwrap_or_else(|p| p.into_inner());
                    waiters.remove(&req_id);
                    return Err(format!(
                        "Sidecar pipe disconnected while awaiting request #{} ('{}')",
                        req_id, method
                    ));
                }
            },
        };

        // Check for RPC error in response
        if let Some(err_val) = resp_val.get("error") {
            if !err_val.is_null() {
                let msg = err_val
                    .get("message")
                    .and_then(|m| m.as_str())
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| err_val.to_string());
                return Err(format!("Sidecar RPC error: {}", msg));
            }
        }

        let result = resp_val.get("result").cloned().unwrap_or(serde_json::Value::Null);
        Ok(result)
    }

    /// Checks if the sidecar process is currently alive and running.
    pub fn is_alive(&self) -> bool {
        if let Ok(mut guard) = self.active_child.lock() {
            if let Some(ref mut active) = *guard {
                return matches!(active.child.try_wait(), Ok(None));
            }
        }
        false
    }

    /// Gracefully closes stdin and shuts down the child sidecar process.
    pub fn shutdown(&self) {
        // 1. Send graceful shutdown command with a short timeout
        let _ = self.call_method("engine.shutdown", None, Some(Duration::from_millis(600)));

        // 2. Drop stdin and terminate process
        if let Ok(mut guard) = self.active_child.lock() {
            if let Some(mut active) = guard.take() {
                let _ = active.stdin.flush();
                drop(active.stdin); // Triggers Python EOF watchdog

                // Small grace period
                std::thread::sleep(Duration::from_millis(150));

                match active.child.try_wait() {
                    Ok(Some(_)) => {}
                    _ => {
                        let _ = active.child.kill();
                        let _ = active.child.wait();
                    }
                }
            }
        }
    }
}

impl Drop for SidecarManager {
    fn drop(&mut self) {
        self.shutdown();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{BufRead, BufReader, Write};
    use std::process::{Command, Stdio};

    #[test]
    #[cfg(windows)]
    fn test_windows_job_object_creation_and_assignment() {
        let job = WindowsJobObject::create_kill_on_close().expect("Failed to create Job Object");

        let mut child = Command::new("python")
            .arg("-c")
            .arg("import time; time.sleep(0.5)")
            .spawn()
            .expect("Failed to spawn test python process");

        let handle = child.as_raw_handle();
        job.assign_process(handle as _).expect("Failed to assign child to Job Object");

        let status = child.wait().expect("Failed to wait on child");
        assert!(status.success());
    }

    #[test]
    #[cfg(windows)]
    fn test_windows_job_object_kills_on_handle_close() {
        let job = WindowsJobObject::create_kill_on_close().expect("Failed to create Job Object");

        let mut child = Command::new("python")
            .arg("-c")
            .arg("import time; time.sleep(10)")
            .spawn()
            .expect("Failed to spawn test python process");

        let handle = child.as_raw_handle();
        job.assign_process(handle as _).expect("Failed to assign child to Job Object");

        // Explicitly drop the job object. Windows NT kernel MUST immediately kill the child process.
        drop(job);

        let start = std::time::Instant::now();
        let _status = child.wait().expect("Failed to wait on child");
        let elapsed = start.elapsed();

        // Must terminate well before the 10-second sleep completes
        assert!(elapsed < Duration::from_secs(3), "Process should have been killed immediately on job close, took {:?}", elapsed);
        // The process was terminated before running its 10-second sleep
    }

    #[test]
    fn test_script_path_resolution() {
        let mut found = false;
        if let Ok(cwd) = std::env::current_dir() {
            if cwd.join("engine_sidecar.py").is_file() || cwd.join("..").join("engine_sidecar.py").is_file() {
                found = true;
            }
        }
        assert!(found, "engine_sidecar.py should exist in project root or parent");
    }

    #[test]
    fn test_ndjson_protocol_parsing() {
        let progress_json = r#"{"type": "progress", "data": {"task_id": 1, "percent": 45.2, "stage": "transcribing", "message": "Transcribing audio..."}}"#;
        let parsed: serde_json::Value = serde_json::from_str(progress_json).unwrap();
        assert_eq!(parsed["type"], "progress");
        assert_eq!(parsed["data"]["percent"], 45.2);
        assert_eq!(parsed["data"]["stage"], "transcribing");

        let rpc_res_json = r#"{"id": 10, "result": {"status": "ready", "version": "1.0.0"}, "error": null}"#;
        let parsed_res: serde_json::Value = serde_json::from_str(rpc_res_json).unwrap();
        assert_eq!(parsed_res["id"], 10);
        assert_eq!(parsed_res["result"]["status"], "ready");
        assert!(parsed_res["error"].is_null());

        let rpc_err_json = r#"{"id": 11, "result": null, "error": {"code": -32601, "message": "Method not found"}}"#;
        let parsed_err: serde_json::Value = serde_json::from_str(rpc_err_json).unwrap();
        assert_eq!(parsed_err["id"], 11);
        assert!(parsed_err["result"].is_null());
        assert_eq!(parsed_err["error"]["code"], -32601);
    }

    #[test]
    fn test_sidecar_subprocess_ndjson_roundtrip() {
        let (script, parent_dir) = if std::path::Path::new("engine_sidecar.py").is_file() {
            (std::path::PathBuf::from("engine_sidecar.py"), std::env::current_dir().unwrap())
        } else if std::path::Path::new("../engine_sidecar.py").is_file() {
            (
                std::env::current_dir().unwrap().join("..").join("engine_sidecar.py"),
                std::env::current_dir().unwrap().join(".."),
            )
        } else {
            panic!("Could not find engine_sidecar.py");
        };

        let mut cmd = Command::new("python");
        cmd.current_dir(&parent_dir);
        cmd.env("PYTHONPATH", &parent_dir);
        cmd.arg(&script);
        cmd.stdin(Stdio::piped());
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::inherit());

        let mut child = cmd.spawn().expect("Failed to spawn engine_sidecar.py");

        #[cfg(windows)]
        let _job = {
            let job = WindowsJobObject::create_kill_on_close().expect("Failed to create Job Object");
            job.assign_process(child.as_raw_handle() as _).expect("Failed to assign child to Job Object");
            job
        };

        let mut stdin = child.stdin.take().expect("Failed to take stdin");
        let stdout = child.stdout.take().expect("Failed to take stdout");
        let mut reader = BufReader::new(stdout);

        // 1. Send engine.ping
        let ping_req = serde_json::json!({"id": 1, "method": "engine.ping", "params": {}});
        writeln!(stdin, "{}", serde_json::to_string(&ping_req).unwrap()).unwrap();
        stdin.flush().unwrap();

        let mut ping_line = String::new();
        reader.read_line(&mut ping_line).unwrap();
        let ping_resp: serde_json::Value = serde_json::from_str(&ping_line).unwrap();
        assert_eq!(ping_resp["id"], 1);
        assert_eq!(ping_resp["result"]["status"], "ready");
        assert_eq!(ping_resp["result"]["version"], "1.0.0");
        assert!(ping_resp["error"].is_null());

        // 2. Send engine.shift_time
        let shift_req = serde_json::json!({
            "id": 2,
            "method": "engine.shift_time",
            "params": {
                "segments": [{"start": 1.0, "end": 3.0, "text": "test"}],
                "offset_seconds": 0.5
            }
        });
        writeln!(stdin, "{}", serde_json::to_string(&shift_req).unwrap()).unwrap();
        stdin.flush().unwrap();

        let mut shift_line = String::new();
        reader.read_line(&mut shift_line).unwrap();
        let shift_resp: serde_json::Value = serde_json::from_str(&shift_line).unwrap();
        assert_eq!(shift_resp["id"], 2);
        assert_eq!(shift_resp["result"]["segments"][0]["start"], 1.5);
        assert_eq!(shift_resp["result"]["segments"][0]["end"], 3.5);

        // 3. Send engine.shutdown
        let shutdown_req = serde_json::json!({"id": 3, "method": "engine.shutdown", "params": {}});
        writeln!(stdin, "{}", serde_json::to_string(&shutdown_req).unwrap()).unwrap();
        stdin.flush().unwrap();

        drop(stdin);

        let status = child.wait().expect("Failed to wait on child process");
        assert!(status.success());
    }
}

