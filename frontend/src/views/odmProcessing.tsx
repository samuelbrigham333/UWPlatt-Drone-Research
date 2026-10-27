/**
 * ODM Processing view.
 * Collects processing values and passes one request object through Tauri.
 * The Python backend owns image validation and the two ODM processing passes.
 */

import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react';
import type { JobState } from '../app/App';
import { chooseFolder, startODM, cancelODM } from '../lib/odmBridge';
import { type AppSettings, type ODMJobRequest, validateJob } from '../types/appSettings';
import '../styling/odmProcessing.css';

type Props = {
    settings: AppSettings;
    setSettings: Dispatch<SetStateAction<AppSettings>>;
    job: JobState;
    setJob: Dispatch<SetStateAction<JobState>>;
};

export default function ODMProcessing({ settings, setSettings, job, setJob }: Props) {
    const [input, setInput] = useState({ imagePath: '', outputPath: '', projectName: '' });
    const [error, setError] = useState('');
    const logRef = useRef<HTMLPreElement>(null);

    useEffect(() => {
        if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
    }, [job.lines]);

    // ==========================================================
    // UPDATE THE FRONTEND SETTINGS
    // ==========================================================
    const updateODM = (change: Partial<AppSettings['odm']>) => {
        setSettings(previous => ({ ...previous, odm: { ...previous.odm, ...change } }));
    };

    const updateDocker = (change: Partial<AppSettings['docker']>) => {
        setSettings(previous => ({ ...previous, docker: { ...previous.docker, ...change } }));
    };

    async function browse(field: 'imagePath' | 'outputPath') {
        try {
            const path = await chooseFolder();
            if (path) setInput(previous => ({ ...previous, [field]: path }));
        } catch (e) {
            setError(String(e));
        }
    }

    // ==========================================================
    // START ODM PROCESSING
    // ==========================================================
    async function startProcessing() {
        // One request object containing all user inputs and processing settings.
        const request: ODMJobRequest = {
            ...input,
            generateSuperpixels: false, // This page only runs the two ODM passes.
            settings
        };

        const issue = validateJob(request);
        if (issue) {
            setError(issue);
            return;
        }

        const jobId = `job-${Date.now().toString(36)}`;
        setError('');
        setJob({ id: jobId, running: true, stage: 'Starting', lines: [], result: '' });

        try {
            await startODM(jobId, request);
        } catch (e) {
            setError(String(e));
            setJob(previous => previous.id === jobId
                ? { ...previous, running: false, stage: 'Failed to start' }
                : previous
            );
        }
    }

    async function stopProcessing() {
        try {
            await cancelODM(job.id);
        } catch (e) {
            setError(String(e));
        }
    }

    // ==========================================================
    // PROCESSING FORM AND LIVE LOGS
    // ==========================================================
    return (
        <div className="config-page odm-page">
            <h1>ODM Processing</h1>
            <p>Select the mixed RGB and multispectral image folder, then configure this ODM job.</p>

            <section className="config-card">
                <h2>Project</h2>
                <div className="config-grid">
                    <label>
                        Source image folder
                        <span className="path-row">
                            <input value={input.imagePath} onChange={e => setInput(p => ({ ...p, imagePath: e.target.value }))} placeholder="Mixed drone image folder" />
                            <button type="button" onClick={() => browse('imagePath')}>Browse</button>
                        </span>
                    </label>
                    <label>
                        Output folder
                        <span className="path-row">
                            <input value={input.outputPath} onChange={e => setInput(p => ({ ...p, outputPath: e.target.value }))} placeholder="ODM output folder" />
                            <button type="button" onClick={() => browse('outputPath')}>Browse</button>
                        </span>
                    </label>
                    <label>
                        Project name
                        <input value={input.projectName} onChange={e => setInput(p => ({ ...p, projectName: e.target.value }))} placeholder="Field_01" />
                    </label>
                </div>
            </section>

            <section className="config-card">
                <h2>Processing options</h2>
                <div className="config-grid">
                    <label>Split size
                        <input type="number" min={1} value={settings.odm.split} onChange={e => updateODM({ split: Number(e.target.value) })} />
                    </label>
                    <label>Split overlap (meters)
                        <input type="number" min={0} value={settings.odm.splitOverlap} onChange={e => updateODM({ splitOverlap: Number(e.target.value) })} />
                    </label>
                    <label>Point cloud quality
                        <select value={settings.odm.pointCloudQuality} onChange={e => updateODM({ pointCloudQuality: e.target.value as AppSettings['odm']['pointCloudQuality'] })}>
                            {['lowest', 'low', 'medium', 'high', 'ultra'].map(v => <option key={v} value={v}>{v}</option>)}
                        </select>
                    </label>
                    <label>Feature quality
                        <select value={settings.odm.featureQuality} onChange={e => updateODM({ featureQuality: e.target.value as AppSettings['odm']['featureQuality'] })}>
                            {['low', 'medium', 'high', 'ultra'].map(v => <option key={v} value={v}>{v}</option>)}
                        </select>
                    </label>
                    <label>Orthophoto resolution (cm/pixel)
                        <input type="number" min={0.1} step={0.1} value={settings.odm.orthophotoResolution} onChange={e => updateODM({ orthophotoResolution: Number(e.target.value) })} />
                    </label>
                    <label>Max concurrency
                        <input type="number" min={1} max={64} value={settings.docker.maxConcurrency} onChange={e => updateDocker({ maxConcurrency: Number(e.target.value) })} />
                    </label>
                    <label>Processing hardware
                        <select value={settings.docker.gpuMode} onChange={e => updateDocker({ gpuMode: e.target.value as AppSettings['docker']['gpuMode'] })}>
                            <option value="auto">Automatic detection</option>
                            <option value="cpu">CPU</option>
                            <option value="nvidia">NVIDIA GPU</option>
                        </select>
                    </label>
                    <label className="config-checkbox">
                        <input type="checkbox" checked={settings.docker.autoStartDocker} onChange={e => updateDocker({ autoStartDocker: e.target.checked })} />
                        Start Docker Desktop if needed
                    </label>
                    <label className="config-checkbox">
                        <input type="checkbox" checked={settings.odm.dsm} onChange={e => updateODM({ dsm: e.target.checked })} />
                        Generate DSM
                    </label>
                    <label className="config-checkbox">
                        <input type="checkbox" checked={settings.odm.dtm} onChange={e => updateODM({ dtm: e.target.checked })} />
                        Generate DTM
                    </label>
                </div>
            </section>

            <section className="config-card">
                <h2>Processing</h2>
                <div className="odm-actions">
                    <button type="button" disabled={job.running} onClick={startProcessing}>Start processing</button>
                    <button type="button" disabled={!job.running} onClick={stopProcessing}>Stop processing</button>
                    <span role="status">{job.stage}</span>
                </div>
                <progress className="odm-progress" max={100} value={job.running ? undefined : job.stage === 'Completed' ? 100 : 0} />
                {error && <p className="error-text" role="alert">{error}</p>}
                {job.result && <p role="status">{job.result}</p>}
            </section>

            <section className="config-card">
                <h2>Processing terminal</h2>
                <pre className="odm-log" ref={logRef} role="log">{job.lines.length ? job.lines.join('\n') : 'No processing output yet.'}</pre>
            </section>
        </div>
    );
}
