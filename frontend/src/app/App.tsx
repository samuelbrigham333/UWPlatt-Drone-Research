/**
 * Main application shell.
 * Coordinates navigation, persistent preferences, and ODM process events.
 * Processing remains in Python; this file only manages frontend state.
 */
import { useEffect, useState } from 'react';
import uwplattLogo from '../assets/UWPlatteville_Horizontal.png';
import Settings from '../views/settings';
import ODMProcessing from '../views/odmProcessing';
import OrthomosaicProcessing from '../views/orthomosaicProcessing';
import SuperpixelAnalyzing from '../views/superpixelAnalyzing';
import { onODMEvent } from '../lib/odmBridge';
import { readSettings, saveSettings, type AppSettings } from '../types/appSettings';
import '../styling/themes.css';
import '../styling/App.css';

export type JobState = {
  id: string;
  running: boolean;
  stage: string;
  lines: string[];
  result: string;
};

const EMPTY_JOB: JobState = {
  id: '',
  running: false,
  stage: 'Idle',
  lines: [],
  result: '',
};

export default function App() {
  // ----------------------------------------------------------
  // APPLICATION STATE
  // ----------------------------------------------------------
  const [view, setView] = useState(0);
  const [settings, setSettings] = useState<AppSettings>(readSettings);
  const [job, setJob] = useState<JobState>(EMPTY_JOB);

  // Persist preferences and apply the selected appearance.
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', settings.appearance.theme);
    saveSettings(settings);
  }, [settings]);

  // ----------------------------------------------------------
  // ODM BACKEND EVENTS
  // ----------------------------------------------------------
  // Keep this listener in the app shell so navigation does not
  // interrupt logging or reset an active processing job.
  useEffect(() => {
    let disposed = false;
    let unlisten: (() => void) | undefined;

    void onODMEvent((event) => {
      setJob((current) => {
        if (current.id !== event.jobId) return current;

        if (event.kind === 'log') {
          return { ...current, lines: [...current.lines, event.message].slice(-3000) };
        }

        if (event.kind === 'stage') {
          return {
            ...current,
            stage: event.stage || event.message,
            lines: [...current.lines, event.message].slice(-3000),
          };
        }

        if (event.kind === 'finish') {
          return {
            ...current,
            running: false,
            stage: event.success ? 'Completed' : 'Failed',
            result: event.message,
          };
        }

        return current;
      });
    })
      .then((cleanup) => {
        if (disposed) cleanup();
        else unlisten = cleanup;
      })
      .catch((error) => console.warn('ODM event listener unavailable:', error));

    return () => {
      disposed = true;
      unlisten?.();
    };
  }, []);

  // ----------------------------------------------------------
  // APPLICATION LAYOUT
  // ----------------------------------------------------------
  return (
    <div className="appContainer">
      {/* University branding / fixed header */}
      <header className="headerContainer">
        <img src={uwplattLogo} alt="UW-Platteville Logo" />
      </header>

      <div className="contentContainer">
        {/* Sidebar navigation */}
        <div className="navigationBarContainer">
          <nav className="navigationBar" aria-label="Main navigation">
            <button className={view === 0 ? 'active' : ''} onClick={() => setView(0)}>
              ODM Processing
            </button>
            <button className={view === 1 ? 'active' : ''} onClick={() => setView(1)}>
              Analyze Existing Orthomosaic
            </button>
            <button className={view === 2 ? 'active' : ''} onClick={() => setView(2)}>
              Train AI Model - Analyze Superpixels
            </button>
          </nav>

          <button className={`settingsButton ${view === 3 ? 'active' : ''}`} onClick={() => setView(3)}>
            Settings
          </button>
        </div>

        {/* Active application view */}
        <main className="mainBody">
          {view === 0 && (
            <ODMProcessing
              settings={settings}
              setSettings={setSettings}
              job={job}
              setJob={setJob}
            />
          )}
          {view === 1 && <OrthomosaicProcessing />}
          {view === 2 && <SuperpixelAnalyzing />}
          {view === 3 && <Settings settings={settings} setSettings={setSettings} />}
        </main>
      </div>
    </div>
  );
}
