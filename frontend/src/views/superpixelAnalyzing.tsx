
/**
 * Superpixel Training Workspace
 *
 * Responsibilities:
 * 1. Load prepared RGB and multispectral examples from a JSON manifest.
 * 2. Show one isolated superpixel at a time for human classification.
 * 3. Keep Grass / Clover / Other decisions in React state.
 * 4. Allow navigation and correction without writing training data yet.
 *
 * The manifest is generated from the real superpixel label raster by
 * ODM/prepare_training_samples.py. Model training is NOT performed here.
 */

import { useMemo, useState, type ChangeEvent } from 'react';
import { chooseTiffFile } from '../lib/odmBridge';
import '../styling/superpixelAnalyzing.css';

// ==========================================================
// TYPES
// ==========================================================

type VegetationClass = 'Grass' | 'Clover' | 'Other';

type SuperpixelSample = {
  id: number;
  rgb: string;
  multispectral: string;
  pixels: number;
};

type TrainingManifest = {
  version: 1;
  source: string;
  multispectralDisplay: string;
  samples: SuperpixelSample[];
};

type SampleLabels = Record<number, VegetationClass>;

const CLASS_OPTIONS: VegetationClass[] = ['Grass', 'Clover', 'Other'];

// ==========================================================
// MANIFEST VALIDATION
// ==========================================================

function isTrainingManifest(value: unknown): value is TrainingManifest {
  if (typeof value !== 'object' || value === null) return false;

  const data = value as Partial<TrainingManifest>;

  return (
    data.version === 1 &&
    typeof data.source === 'string' &&
    typeof data.multispectralDisplay === 'string' &&
    Array.isArray(data.samples) &&
    data.samples.every(sample =>
      Number.isInteger(sample.id) &&
      sample.id > 0 &&
      Number.isFinite(sample.pixels) &&
      typeof sample.rgb === 'string' &&
      sample.rgb.startsWith('data:image/') &&
      typeof sample.multispectral === 'string' &&
      sample.multispectral.startsWith('data:image/')
    )
  );
}

// ==========================================================
// TRAINING WORKSPACE
// ==========================================================

export default function SuperpixelAnalyzing() {
  const [manifest, setManifest] = useState<TrainingManifest | null>(null);
  const [index, setIndex] = useState(0);
  const [labels, setLabels] = useState<SampleLabels>({});
  const [error, setError] = useState('');
  const [onlyUnlabeled, setOnlyUnlabeled] = useState(false);

  const [orthomosaicPaths, setOrthomosaicPaths] = useState({
    multispectral: '',
    rgb: '',
    labels: ''
});



  const samples = manifest?.samples ?? [];
  const activeSample = samples[index];
  const selectedClass = activeSample ? labels[activeSample.id] : undefined;

  const classCounts = useMemo(() => {
    const counts = { Grass: 0, Clover: 0, Other: 0 };
    samples.forEach(sample => {
      const classification = labels[sample.id];
      if (classification) counts[classification]++;
    });
    return counts;
  }, [samples, labels]);

  const labeledCount = classCounts.Grass + classCounts.Clover + classCounts.Other;
  const remainingCount = samples.length - labeledCount;

  // ==========================================================
  // LOAD REAL SUPERPIXEL DATA
  // ==========================================================

  async function loadManifest(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const parsed: unknown = JSON.parse(await file.text());
      if (!isTrainingManifest(parsed)) {
        throw new Error('This JSON file is not a valid superpixel training manifest.');
      }

      const uniqueIds = new Set(parsed.samples.map(sample => sample.id));
      if (uniqueIds.size !== parsed.samples.length) {
        throw new Error('Duplicate superpixel IDs were found.');
      }

      setManifest(parsed);
      setLabels({});
      setIndex(0);
      setError('');
      setOnlyUnlabeled(false);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : String(problem));
    } finally {
      event.target.value = '';
    }
  }

  async function browseOrthomosaic(
    field: 'multispectral' | 'rgb' | 'labels'
  ) {
    try {
        const title = field === 'rgb'
            ? 'Select RGB Orthomosaic'
            : field === 'labels'
                ? 'Select Labels Orthomosaic'
                : 'Select Multispectral Orthomosaic';

        const path = await chooseTiffFile(title);

        if (path) {
            setOrthomosaicPaths(previous => ({
                ...previous,
                [field]: path
            }));

            setError('');
        }
    } catch (problem) {
        setError(
            problem instanceof Error
                ? problem.message
                : String(problem)
        );
    }
}

  // ==========================================================
  // CLASSIFICATION AND NAVIGATION
  // ==========================================================

  function navigate(direction: -1 | 1, unlabeledOnly = onlyUnlabeled) {
    if (!samples.length) return;

    let next = index + direction;
    while (next >= 0 && next < samples.length) {
      if (!unlabeledOnly || labels[samples[next].id] === undefined) {
        setIndex(next);
        return;
      }
      next += direction;
    }
  }

  function classify(value: VegetationClass) {
    if (!activeSample) return;

    setLabels(current => ({ ...current, [activeSample.id]: value }));

    // Advance to the next unclassified region after each decision.
    const next = samples.findIndex((sample, sampleIndex) =>
      sampleIndex > index && labels[sample.id] === undefined
    );
    if (next >= 0) setIndex(next);
    else if (index < samples.length - 1) setIndex(index + 1);
  }

  function clearClassification() {
    if (!activeSample) return;
    setLabels(current => {
      const next = { ...current };
      delete next[activeSample.id];
      return next;
    });
  }

  // ==========================================================
  // RENDER JSX
  // ==========================================================

  return (
    <div className="training-page">

      <header className="training-heading">
        <div>
          <h1>Train AI Model</h1>
          <p>Review individual superpixels and assign the dominant vegetation class.</p>
        </div>
        <label className="training-file-button">
          Load training samples
          <input type="file" accept=".json,application/json" onChange={loadManifest} />
        </label>
      </header>


      <section className="training-file-section">
    <h2>Orthomosaic Selection</h2>
    <p>
        Select the multispectral and RGB orthomosaics that will be
        used for superpixel visualization and classification.
    </p>

    <div className="training-file-grid">
        <label>
            Multispectral Orthomosaic
            <span className="training-path-row">
                <input
                    type="text"
                    value={orthomosaicPaths.multispectral}
                    onChange={e =>
                        setOrthomosaicPaths(previous => ({
                            ...previous,
                            multispectral: e.target.value
                        }))
                    }
                    placeholder="Path to multispectral .tif"
                />
                <button
                    type="button"
                    onClick={() => browseOrthomosaic('multispectral')}
                >
                    Browse
                </button>
            </span>
        </label>

        <label>
            RGB Orthomosaic
            <span className="training-path-row">
                <input
                    type="text"
                    value={orthomosaicPaths.rgb}
                    onChange={e =>
                        setOrthomosaicPaths(previous => ({
                            ...previous,
                            rgb: e.target.value
                        }))
                    }
                    placeholder="Path to RGB .tif"
                />
                <button
                    type="button"
                    onClick={() => browseOrthomosaic('rgb')}
                >
                    Browse
                </button>
            </span>
        </label>
    </div>
</section>

      {error && <p role="alert" className="training-error">{error}</p>}

      {!manifest ? (
        <section className="training-empty">
          <h2>No training samples loaded</h2>
          <p>
            Generate a training manifest from <code>superpixel_labels.tif</code>,
            <code>rgb_orthomosaic_aligned.tif</code>, and the original multispectral
            orthomosaic. Then use <strong>Load training samples</strong> above.
          </p>
          <p>The interface uses real superpixel images; it does not generate example vegetation.</p>
        </section>
      ) : (
        <>
          <section className="training-summary" aria-label="Training progress">
            <div><span>Samples</span><strong>{samples.length}</strong></div>
            <div><span>Labeled</span><strong>{labeledCount}</strong></div>
            <div><span>Remaining</span><strong>{remainingCount}</strong></div>
            <div><span>Grass</span><strong>{classCounts.Grass}</strong></div>
            <div><span>Clover</span><strong>{classCounts.Clover}</strong></div>
            <div><span>Other</span><strong>{classCounts.Other}</strong></div>
          </section>

          <div className="training-workspace">

            <section className="training-classifier" aria-label="Current superpixel">
              <div className="training-section-heading">
                <div>
                  <h2>Superpixel {activeSample?.id ?? '—'}</h2>
                  <span>{samples.length ? `${index + 1} of ${samples.length}` : 'No valid samples'}</span>
                </div>
                {selectedClass && <span className="training-current">Labeled: {selectedClass}</span>}
              </div>

              {activeSample ? (
                <>
                  <div className="training-main-preview">
                    <img src={activeSample.rgb} alt={`Isolated RGB image of superpixel ${activeSample.id}`} />
                  </div>
                  <p className="training-help">What is this superpixel mostly made of?</p>
                  <div className="training-class-buttons">
                    {CLASS_OPTIONS.map(option => (
                      <button
                        key={option}
                        type="button"
                        className={selectedClass === option ? 'selected' : ''}
                        aria-pressed={selectedClass === option}
                        onClick={() => classify(option)}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                  <div className="training-controls">
                    <button type="button" disabled={index === 0} onClick={() => navigate(-1)}>Previous</button>
                    <button type="button" disabled={index === samples.length - 1} onClick={() => navigate(1)}>Next / Skip</button>
                    <button type="button" disabled={!selectedClass} onClick={clearClassification}>Clear label</button>
                    <label>
                      <input type="checkbox" checked={onlyUnlabeled} onChange={e => setOnlyUnlabeled(e.target.checked)} />
                      Navigate unlabeled only
                    </label>
                  </div>
                  <p className="training-footnote">Area: {activeSample.pixels.toLocaleString()} raster pixels. Superpixel ID: {activeSample.id}.</p>
                </>
              ) : <p>No valid superpixel samples were found in this manifest.</p>}
            </section>

            <aside className="training-examples" aria-label="Matching image previews">
              <div className="training-section-heading"><h2>Reference views</h2></div>
              <div className="training-example">
                <h3>RGB</h3>
                <p>Natural-color view of the selected superpixel</p>
                {activeSample && <img src={activeSample.rgb} alt={`RGB preview ${activeSample.id}`} />}
              </div>
              <div className="training-example">
                <h3>Multispectral</h3>
                <p>{manifest.multispectralDisplay}</p>
                {activeSample && <img src={activeSample.multispectral} alt={`Multispectral false-color preview ${activeSample.id}`} />}
              </div>
              <p className="training-footnote">Both previews show the same label mask and geographic region. Multispectral is a visualization, not raw spectral values.</p>
            </aside>
          </div>
          <footer className="training-footer">
            <div className="training-progress-bar" role="progressbar" aria-label="Labeling progress" aria-valuenow={labeledCount} aria-valuemin={0} aria-valuemax={samples.length || 1}>
              <div style={{ width: `${samples.length ? (100 * labeledCount) / samples.length : 0}%` }} />
            </div>
            <p>Labels are currently held only in memory. CSV saving and model training will be added later.</p>
          </footer>
        </>
      )}
    </div>
  );
}




