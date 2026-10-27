/**
 * Application settings view.
 * Manages persistent appearance and processing defaults, and displays
 * host/Docker diagnostics without changing the underlying processing code.
 */

import { useEffect, useState, type Dispatch, type SetStateAction } from 'react';
import { getSystemInfo, type SystemInfo } from '../lib/odmBridge';
import { type AppSettings, DEFAULT_SETTINGS, applyTheme } from '../types/appSettings';
import '../styling/settings.css';
import '../styling/themes.css';
// Component inputs supplied by the application shell.
type Props = {
    settings: AppSettings;
    setSettings: Dispatch<SetStateAction<AppSettings>>;
};
// Render the view and manage its local interaction state.
export default function Settings({ settings, setSettings }: Props) {
    const [info, setInfo] = useState<SystemInfo | null>(null);
    const [error, setError] = useState('');
    // Detect automatically on Settings load, not only when clicking a button.
    useEffect(() => {
        let mounted = true;
        getSystemInfo().then(value => { if (mounted)
            setInfo(value); })
            .catch(() => { });
        return () => { mounted = false; };
    }, []);
    const editDocker = (value: Partial<AppSettings['docker']>) => setSettings(s => ({ ...s, docker: { ...s.docker, ...value } }));
    return <div className="config-page">
      <h1>Settings</h1>
      <p>Application-wide settings. These values are used as defaults for new processing jobs.</p>
      <section className="config-card">
        <h2>Appearance</h2>
        <div className="config-grid">
          <label>Theme<select value={settings.appearance.theme} onChange={e => { const theme = e.target.value as AppSettings['appearance']['theme']; applyTheme(theme); setSettings(s => ({ ...s, appearance: { theme } })); }}>
              <option value="system">Follow system</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </label>
        </div>
      </section>

      <section className="config-card">
        <h2>Mac / Windows &amp; Docker</h2>
        <div className="config-grid">
          <label>Detected operating system<input readOnly value={info ? `${info.os} (${info.arch})` : 'Checking…'}/>
          </label>
          <label>ODM processing engine<select value={settings.docker.gpuMode} onChange={e => editDocker({ gpuMode: e.target.value as AppSettings['docker']['gpuMode'] })}>
              <option value="auto">Auto-detect (recommended)</option>
              <option value="cpu">CPU (Windows / Mac)</option>
              <option value="nvidia">NVIDIA GPU (Windows only)</option>
            </select>
          </label>
          <label>Maximum concurrent ODM workers<input type="number" min={1} max={64} value={settings.docker.maxConcurrency} onChange={e => editDocker({ maxConcurrency: Number(e.target.value) })}/>
          </label>
          <label className="config-checkbox">
            <input type="checkbox" checked={settings.docker.autoStartDocker} onChange={e => editDocker({ autoStartDocker: e.target.checked })}/> Start Docker Desktop when needed</label>
        </div>
        <p className="config-description">The actual operating system is detected automatically. In Auto mode, Windows with a detected NVIDIA driver selects the ODM GPU image; other machines select CPU. NVIDIA requires working Docker GPU passthrough. Detection alone cannot guarantee acceleration.</p>
        <button type="button" onClick={async () => { try {
          setError('');
          setInfo(await getSystemInfo());
          }
          catch (e) {
          setError(String(e));
          } }}>Check system &amp; Docker</button>
        {info && <pre className="diagnostics">Operating system: {info.os} ({info.arch}){'\n'}Docker installed: {String(info.dockerInstalled)}{'\n'}Docker ready: {String(info.dockerRunning)}{'\n'}NVIDIA on host: {String(info.nvidiaHostVisible)}{'\n'}Automatic selection: {info.os === 'windows' && info.nvidiaHostVisible ? 'NVIDIA candidate' : 'CPU'}{'\n'}Note: this does not verify CUDA works inside Docker.</pre>}
        {error && <p role="alert">{error}</p>}
      </section>

      <section className="config-card">
        <h2>Default ODM options</h2>
        <p>Change per project in the ODM Processing page.</p>
        <div className="config-grid">
          <label>Split (images per submodel)<input type="number" min={1} value={settings.odm.split} onChange={e => setSettings(s => ({ ...s, odm: { ...s.odm, split: Number(e.target.value) } }))}/>
          </label>
          <label>Split overlap (meters)<input type="number" min={0} value={settings.odm.splitOverlap} onChange={e => setSettings(s => ({ ...s, odm: { ...s.odm, splitOverlap: Number(e.target.value) } }))}/>
          </label>
          <label>Point cloud quality<select value={settings.odm.pointCloudQuality} onChange={e => setSettings(s => ({ ...s, odm: { ...s.odm, pointCloudQuality: e.target.value as AppSettings['odm']['pointCloudQuality'] } }))}>{['lowest', 'low', 'medium', 'high', 'ultra'].map(q => <option key={q} value={q}>{q}</option>)}</select>
          </label>
          <label>Feature quality<select value={settings.odm.featureQuality} onChange={e => setSettings(s => ({ ...s, odm: { ...s.odm, featureQuality: e.target.value as AppSettings['odm']['featureQuality'] } }))}>{['low', 'medium', 'high', 'ultra'].map(q => <option key={q} value={q}>{q}</option>)}</select>
          </label>
          <label>Orthophoto resolution (cm/pixel)<input type="number" min={0.1} step={0.1} value={settings.odm.orthophotoResolution} onChange={e => setSettings(s => ({ ...s, odm: { ...s.odm, orthophotoResolution: Number(e.target.value) } }))}/>
          </label>
          <label className="config-checkbox">
            <input type="checkbox" checked={settings.odm.dsm} onChange={e => setSettings(s => ({ ...s, odm: { ...s.odm, dsm: e.target.checked } }))}/> Generate DSM</label>
          <label className="config-checkbox">
            <input type="checkbox" checked={settings.odm.dtm} onChange={e => setSettings(s => ({ ...s, odm: { ...s.odm, dtm: e.target.checked } }))}/> Generate DTM</label>
        </div>
        <p className="config-description">Split 2 is the previous project setting, not OpenDroneMap's upstream default. Increase it for larger image sets after checking available memory.</p>
      </section>

      <section className="config-card">
        <h2>Default superpixel options</h2>
        <p>Used only when optional superpixel analysis is enabled on a job.</p>
        <div className="config-grid">
          <label>Region area (m²)<input type="number" min={0.001} step="any" value={settings.superpixel.regionArea} onChange={e => setSettings(s => ({ ...s, superpixel: { ...s.superpixel, regionArea: Number(e.target.value) } }))}/>
          </label>
          <label>Compactness<input type="number" min={0.01} step="any" value={settings.superpixel.compactness} onChange={e => setSettings(s => ({ ...s, superpixel: { ...s.superpixel, compactness: Number(e.target.value) } }))}/>
          </label>
          <label>Sigma<input type="number" min={0} step="any" value={settings.superpixel.sigma} onChange={e => setSettings(s => ({ ...s, superpixel: { ...s.superpixel, sigma: Number(e.target.value) } }))}/>
          </label>
          <label>Tile size (pixels)<input type="number" min={1} step={1} value={settings.superpixel.tileSize} onChange={e => setSettings(s => ({ ...s, superpixel: { ...s.superpixel, tileSize: Number(e.target.value) } }))}/>
          </label>
        </div>
      </section>
      <button type="button" onClick={() => { applyTheme(DEFAULT_SETTINGS.appearance.theme); setSettings(structuredClone(DEFAULT_SETTINGS)); }}>Restore starter defaults</button>
    </div>;
    }
