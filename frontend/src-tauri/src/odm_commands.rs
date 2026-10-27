//! Add to the existing Tauri 2 lib.rs (instructions in README).
//! Small process supervisor: one ODM job at a time, streaming log events.
use serde::Serialize;
use std::io::{BufRead, BufReader, Read};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager, State};

struct JobControl { id: String, child: Arc<Mutex<Child>> }
#[derive(Default)]
pub struct ODMJobState(Mutex<Option<JobControl>>);

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SystemInfo {
    os: String, arch: String, docker_installed: bool, docker_running: bool, nvidia_host_visible: bool,
}
#[derive(Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
struct ODMEvent {
    job_id: String,
    kind: String,
    message: String,
    stage: Option<String>,
    success: Option<bool>,
}
fn send(app: &AppHandle, id: &str, kind: &str, message: String, stage: Option<String>, success: Option<bool>) {
    let _ = app.emit("odm-event", ODMEvent { job_id: id.into(), kind: kind.into(), message, stage, success });
}

fn nvidia_visible() -> bool {
    let probe = |path: &std::path::Path| {
        Command::new(path).arg("-L")
            .output().map(|o| o.status.success() && !o.stdout.is_empty()).unwrap_or(false)
    };
    if probe(std::path::Path::new("nvidia-smi")) { return true; }
    if cfg!(windows) {
        for key in ["ProgramW6432", "ProgramFiles"] {
            if let Some(base) = std::env::var_os(key) {
                let path = std::path::PathBuf::from(base)
                    .join("NVIDIA Corporation").join("NVSMI").join("nvidia-smi.exe");
                if probe(&path) { return true; }
            }
        }
    }
    false
}

#[tauri::command]
pub fn odm_system_info() -> SystemInfo {
    let probe = |exe: &str, arg: &str| -> bool {
        Command::new(exe).arg(arg).stdout(Stdio::null()).stderr(Stdio::null()).status().map(|s| s.success()).unwrap_or(false)
    };
    SystemInfo {
        os: std::env::consts::OS.into(), arch: std::env::consts::ARCH.into(),
        docker_installed: probe("docker", "--version"), docker_running: probe("docker", "info"),
        nvidia_host_visible: nvidia_visible(),
    }
}
fn pump<R: Read + Send + 'static>(app: AppHandle, id: String, reader: R, stderr: bool) -> thread::JoinHandle<()> {
    thread::spawn(move || {
        for item in BufReader::new(reader).lines() {
            match item {
                Ok(line) => {
                    if let Some(jsonline) = line.strip_prefix("@@ODM_EVENT@@") {
                        if let Ok(value) = serde_json::from_str::<serde_json::Value>(jsonline) {
                            let kind = value["kind"].as_str().unwrap_or("stage");
                            let stage = value["stage"].as_str().map(str::to_owned);
                            let message = value["message"].as_str().unwrap_or("Processing update");
                            send(&app, &id, kind, message.into(), stage, None);
                            continue;
                        }
                    }
                    let content = if stderr { format!("[stderr] {line}") } else { line };
                    send(&app, &id, "log", content, None, None);
                }
                Err(e) => { send(&app, &id, "log", format!("Could not read process output: {e}"), None, None); break; }
            }
        }
    })
}

#[tauri::command]
pub fn odm_start(app: AppHandle, state: State<'_, ODMJobState>, job_id: String, request_json: String) -> Result<(), String> {
    if !job_id.starts_with("job-") || job_id.len() > 68 || !job_id.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'-') {
        return Err("Invalid job identifier.".into());
    }
    if request_json.len() > 128_000 { return Err("Processing request is too large.".into()); }
    // Validate JSON before starting a subprocess.
    serde_json::from_str::<serde_json::Value>(&request_json).map_err(|e| format!("Bad JSON: {e}"))?;

    let mut current = state.0.lock().map_err(|_| "Job state lock failed")?;
    if current.is_some() { return Err("Another ODM job is already running.".into()); }
    // Developer run: <repository>/frontend/src-tauri; override with ODM_REPO_ROOT if necessary.
    let root = std::env::var_os("ODM_REPO_ROOT").map(std::path::PathBuf::from)
        .unwrap_or_else(|| std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    let python = std::env::var("ODM_PYTHON")
        .unwrap_or_else(|_| if cfg!(windows) { "python".into() } else { "python3".into() });
    let mut command = Command::new(python);
    command.args(["-u", "-m", "ODM.frontend_bridge", &request_json, &job_id])
        .current_dir(root).stdout(Stdio::piped()).stderr(Stdio::piped());
    let mut child = command.spawn().map_err(|e| format!("Could not start Python: {e}"))?;
    let stdout = child.stdout.take().ok_or("No stdout from backend")?;
    let stderr = child.stderr.take().ok_or("No stderr from backend")?;
    let child = Arc::new(Mutex::new(child));
    *current = Some(JobControl { id: job_id.clone(), child: Arc::clone(&child) });
    drop(current);

    let id = job_id.clone();
    thread::spawn(move || {
        let out = pump(app.clone(), id.clone(), stdout, false);
        let err = pump(app.clone(), id.clone(), stderr, true);
        let result = loop {
            let status = child.lock().unwrap().try_wait();
            match status {
                Ok(Some(value)) => break Ok(value.success()),
                Ok(None) => thread::sleep(Duration::from_millis(200)),
                Err(e) => break Err(e.to_string()),
            }
        };
        let _ = out.join();
        let _ = err.join();
        let state_for_worker = app.state::<ODMJobState>();
        if let Ok(mut locked) = state_for_worker.0.lock() {
            if locked.as_ref().is_some_and(|job| job.id == id) { *locked = None; }
        }
        let ok = result.as_ref().is_ok_and(|x| *x);
        let msg = match result { Ok(true) => "ODM workflow completed.".to_string(), Ok(false) => "ODM workflow stopped or failed. Check the logs.".to_string(), Err(e) => format!("ODM process error: {e}") };
        send(&app, &id, "finish", msg, None, Some(ok));
    });
    Ok(())
}

#[tauri::command]
pub fn odm_cancel(state: State<'_, ODMJobState>, job_id: String) -> Result<(), String> {
    let child = {
        let locked = state.0.lock().map_err(|_| "Job state lock failed")?;
        let current = locked.as_ref().ok_or("No active ODM job")?;
        if current.id != job_id { return Err("The requested job is not active.".into()); }
        Arc::clone(&current.child)
    };
    // First stop the named ODM container so killing Python doesn't orphan Docker work.
    let container = format!("uwplatt-{job_id}");
    let _ = Command::new("docker").args(["stop", "--time", "2", &container])
        .stdout(Stdio::null()).stderr(Stdio::null()).status();
    child.lock().map_err(|_| "Child lock failed".to_string())?.kill().map_err(|e| e.to_string())?;
    Ok(())
}
