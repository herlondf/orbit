use std::collections::HashMap;
use std::sync::Mutex;

use tauri::{AppHandle, Emitter, LogicalPosition, LogicalSize, Manager, State, WebviewWindowBuilder};
use tauri::webview::{WebviewBuilder, NewWindowResponse};

type EmbeddedWebview = tauri::webview::Webview<tauri::Wry>;

struct WebviewRegistry(Mutex<HashMap<String, EmbeddedWebview>>);

// A modern Chrome user-agent so sites like Google Chat don't block us
const USER_AGENT: &str =
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";

// ─── init script injected into every chat webview ─────────────────────────────
// Uses the octorelay:// custom scheme instead of window.__TAURI_INTERNALS__.invoke
// so it works from external-origin webviews (WhatsApp, Slack, etc.)

fn make_init_script(label: &str) -> String {
    let lj = serde_json::to_string(label).unwrap_or_default();
    format!(
        r#"(function(){{
  var __l={lj};
  var __pt='';
  function __relay(params){{
    try{{fetch('octorelay://relay?'+params).catch(function(){{}});}}catch(_){{}}
  }}
  setInterval(function(){{
    var t=document.title||'';
    if(t!==__pt){{
      __pt=t;
      __relay('event=title&label='+encodeURIComponent(__l)+'&value='+encodeURIComponent(t));
    }}
  }},1500);
  // Mask WebView2 detection so Google treats us as regular Chrome
  try{{Object.defineProperty(navigator,'webdriver',{{get:function(){{return false;}}}});}}catch(_){{}}
  try{{
    if(!window.chrome){{
      window.chrome={{app:{{isInstalled:false}},runtime:{{}},loadTimes:function(){{}},csi:function(){{}}}};
    }}
  }}catch(_){{}}
  // Intercept ALL new-window requests (window.open, target=_blank) and relay to shell.
  // The shell will ask the user: open in webview or external browser.
  (function(){{
    function __newwin(url){{
      if(!url||typeof url!=='string')return;
      __relay('event=newwin&label='+encodeURIComponent(__l)+'&url='+encodeURIComponent(url));
    }}
    // Lock window.open so sites can't override it back
    var _open=window.open.bind(window);
    var _handler=function(url,target,features){{
      if(url&&typeof url==='string'){{__newwin(url);return null;}}
      return _open(url,target,features);
    }};
    try{{Object.defineProperty(window,'open',{{value:_handler,writable:false,configurable:false}});}}
    catch(_){{window.open=_handler;}}
    // Capture target=_blank anchor clicks (native level, not JS)
    document.addEventListener('click',function(e){{
      var el=e.target;
      while(el&&el!==document&&el.tagName!=='A')el=el.parentElement;
      if(el&&el.tagName==='A'&&el.getAttribute&&el.getAttribute('target')==='_blank'){{
        var href=el.href||el.getAttribute('href');
        if(href&&(href.startsWith('http://')||href.startsWith('https://'))){{
          e.preventDefault();e.stopImmediatePropagation();
          __newwin(href);
        }}
      }}
    }},true);
  }})();
  try{{
    var _N=window.Notification;
    if(_N){{
      function _ON(title,opts){{
        __relay('event=notif&label='+encodeURIComponent(__l)+'&title='+encodeURIComponent(title)+'&body='+encodeURIComponent((opts&&opts.body)?String(opts.body):''));
        return new _N(title,opts);
      }}
      _ON.prototype=_N.prototype;
      Object.defineProperty(_ON,'permission',{{get:function(){{return _N.permission;}}}});
      _ON.requestPermission=_N.requestPermission.bind(_N);
      window.Notification=_ON;
    }}
  }}catch(_){{}}
}})();"#
    )
}

// ─── percent-decode a URL query-param value (from encodeURIComponent) ─────────

fn percent_decode(s: &str) -> String {
    let bytes = s.as_bytes();
    let mut result: Vec<u8> = Vec::with_capacity(s.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' && i + 2 < bytes.len() {
            if let Ok(hex) = std::str::from_utf8(&bytes[i + 1..i + 3]) {
                if let Ok(byte) = u8::from_str_radix(hex, 16) {
                    result.push(byte);
                    i += 3;
                    continue;
                }
            }
        } else if bytes[i] == b'+' {
            result.push(b' ');
        } else {
            result.push(bytes[i]);
        }
        i += 1;
    }
    String::from_utf8_lossy(&result).into_owned()
}

fn get_param(query: &str, key: &str) -> String {
    let prefix = format!("{}=", key);
    for pair in query.split('&') {
        if let Some(val) = pair.strip_prefix(&prefix) {
            return percent_decode(val);
        }
    }
    String::new()
}

// ─── commands ─────────────────────────────────────────────────────────────────

/// Creates a child webview embedded in the main window at the given logical bounds.
/// If a webview with this label already exists, the call is a no-op.
#[tauri::command]
async fn create_embedded_webview(
    app: AppHandle,
    registry: State<'_, WebviewRegistry>,
    label: String,
    url: String,
    account_id: String,
    x: f64,
    y: f64,
    width: f64,
    height: f64,
) -> Result<(), String> {
    {
        let reg = registry.0.lock().unwrap();
        if reg.contains_key(&label) {
            return Ok(());
        }
    }

    let main_window = app
        .get_window("main")
        .ok_or_else(|| "main window not found".to_string())?;

    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|e| e.to_string())?
        .join("sessions")
        .join(&account_id);

    let parsed_url = url
        .parse::<tauri::Url>()
        .map_err(|e| format!("invalid url: {e}"))?;

    let init_script = make_init_script(&label);

    // Clone data_dir before it's consumed by WebviewBuilder::data_directory()
    let data_dir_popup = data_dir.clone();

    // Clone for on_new_window handler.
    let app_nwr = app.clone();
    let label_nwr = label.clone();

    let webview = main_window
        .add_child(
            WebviewBuilder::new(&label, tauri::WebviewUrl::External(parsed_url))
                .initialization_script(&init_script)
                .data_directory(data_dir)
                .user_agent(USER_AGENT)
                .on_navigation(|_url| true)
                .on_new_window(move |url, _features| {
                    // Create a native popup WebviewWindow instead of a React dialog.
                    // This avoids z-index issues (WebView2 native always renders above HTML)
                    // and works regardless of which frame (main or iframe) triggered the request.
                    let app2 = app_nwr.clone();
                    let data_dir2 = data_dir_popup.clone();
                    let popup_url = url.clone();
                    let popup_label = format!("popup-{}", label_nwr);

                    // run_on_main_thread schedules for the next event loop tick (safe from any thread)
                    let _ = app_nwr.run_on_main_thread(move || {
                        // Close any previous popup with the same label
                        if let Some(existing) = app2.get_webview_window(&popup_label) {
                            let _ = existing.close();
                        }
                        let _ = WebviewWindowBuilder::new(
                            &app2,
                            &popup_label,
                            tauri::WebviewUrl::External(popup_url),
                        )
                        .title("OctoChat – Login / Popup")
                        .inner_size(960.0, 720.0)
                        .center()
                        .user_agent(USER_AGENT)
                        .data_directory(data_dir2) // share session with the embedded webview
                        .build();
                    });

                    NewWindowResponse::Deny
                }),
            LogicalPosition::new(x, y),
            LogicalSize::new(width, height),
        )
        .map_err(|e| e.to_string())?;

    registry.0.lock().unwrap().insert(label, webview);
    Ok(())
}

#[tauri::command]
fn show_webview(registry: State<'_, WebviewRegistry>, label: String) -> Result<(), String> {
    let wv = registry.0.lock().unwrap().get(&label).cloned()
        .ok_or_else(|| format!("'{label}' not found"))?;
    wv.show().map_err(|e| e.to_string())
}

#[tauri::command]
fn hide_webview(registry: State<'_, WebviewRegistry>, label: String) -> Result<(), String> {
    let wv = registry.0.lock().unwrap().get(&label).cloned()
        .ok_or_else(|| format!("'{label}' not found"))?;
    wv.hide().map_err(|e| e.to_string())
}

#[tauri::command]
fn set_webview_bounds(
    registry: State<'_, WebviewRegistry>,
    label: String,
    x: f64,
    y: f64,
    width: f64,
    height: f64,
) -> Result<(), String> {
    let wv = registry.0.lock().unwrap().get(&label).cloned()
        .ok_or_else(|| format!("'{label}' not found"))?;
    wv.set_bounds(tauri::Rect {
        position: tauri::Position::Logical(LogicalPosition::new(x, y)),
        size: tauri::Size::Logical(LogicalSize::new(width, height)),
    })
    .map_err(|e| e.to_string())
}

#[tauri::command]
async fn navigate_webview(
    registry: State<'_, WebviewRegistry>,
    label: String,
    url: String,
) -> Result<(), String> {
    let wv = registry.0.lock().unwrap().get(&label).cloned()
        .ok_or_else(|| format!("'{label}' not found"))?;
    let parsed_url = url.parse::<tauri::Url>().map_err(|e| e.to_string())?;
    wv.navigate(parsed_url).map_err(|e| e.to_string())
}

#[tauri::command]
fn open_external(url: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("cmd")
            .args(["/c", "start", "", &url])
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open").arg(&url).spawn().map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open").arg(&url).spawn().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn open_webview_devtools(registry: State<'_, WebviewRegistry>, label: String) -> Result<(), String> {
    let reg = registry.0.lock().unwrap();
    if let Some(wv) = reg.get(&label) {
        wv.open_devtools();
    }
    Ok(())
}

#[tauri::command]
fn close_webview(registry: State<'_, WebviewRegistry>, label: String) -> Result<(), String> {
    let wv = registry.0.lock().unwrap().remove(&label);
    if let Some(wv) = wv {
        wv.close().map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Called from init scripts when document.title changes — relays to shell for unread badge update.
#[tauri::command]
async fn relay_webview_title(
    app: AppHandle,
    label: String,
    title: String,
) -> Result<(), String> {
    app.emit("webview:title", serde_json::json!({"label": label, "title": title}))
        .map_err(|e| e.to_string())
}

/// Called from init scripts when window.Notification is invoked — relays to shell for native notification.
#[tauri::command]
async fn relay_notification(
    app: AppHandle,
    label: String,
    title: String,
    body: String,
) -> Result<(), String> {
    app.emit(
        "webview:notification",
        serde_json::json!({"label": label, "title": title, "body": body}),
    )
    .map_err(|e| e.to_string())
}

// ─── entry point ──────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(WebviewRegistry(Mutex::new(HashMap::new())))
        // Custom scheme used by child-webview init scripts to relay title/notification events.
        // This bypasses the need for window.__TAURI_INTERNALS__ in external-origin webviews.
        .register_uri_scheme_protocol("octorelay", |ctx, request| {
            use tauri::http::{Response, StatusCode};

            let app = ctx.app_handle();
            let query = request.uri().query().unwrap_or("").to_owned();
            let event = get_param(&query, "event");
            let label = get_param(&query, "label");

            match event.as_str() {
                "newwin" => {
                    let url = get_param(&query, "url");
                    let _ = app.emit(
                        "webview:newwin",
                        serde_json::json!({"label": label, "url": url}),
                    );
                }
                "title" => {
                    let value = get_param(&query, "value");
                    let _ = app.emit(
                        "webview:title",
                        serde_json::json!({"label": label, "title": value}),
                    );
                }
                "notif" => {
                    let title = get_param(&query, "title");
                    let body = get_param(&query, "body");
                    let _ = app.emit(
                        "webview:notification",
                        serde_json::json!({"label": label, "title": title, "body": body}),
                    );
                }
                _ => {}
            }

            Response::builder()
                .status(StatusCode::OK)
                .header("Access-Control-Allow-Origin", "*")
                .body(Vec::new())
                .unwrap()
        })
        .plugin(tauri_plugin_notification::init())
        .invoke_handler(tauri::generate_handler![
            create_embedded_webview,
            show_webview,
            hide_webview,
            set_webview_bounds,
            close_webview,
            navigate_webview,
            open_external,
            open_webview_devtools,
            relay_webview_title,
            relay_notification,
        ])
        .run(tauri::generate_context!())
        .expect("error while running octochat application");
}
