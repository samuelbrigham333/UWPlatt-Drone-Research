/**
 * Shared frontend data contracts and defaults.
 * Keeps saved preferences and request validation independent of UI styling.
 */

// Shared, typed inputs. Keep appearance separate from processing.
export type Theme = 'system' | 'light' | 'dark';
export type PlatformPreference = 'auto' | 'windows' | 'macos';
export type GpuMode = 'auto' | 'cpu' | 'nvidia';
export type PointCloudQuality = 'lowest' | 'low' | 'medium' | 'high' | 'ultra';
export type FeatureQuality = 'low' | 'medium' | 'high' | 'ultra';
export interface AppSettings {
    appearance: {
        theme: Theme;
    };
    docker: {
        platformPreference: PlatformPreference;
        gpuMode: GpuMode;
        autoStartDocker: boolean;
        maxConcurrency: number;
    };
    odm: {
        split: number;
        splitOverlap: number;
        pointCloudQuality: PointCloudQuality;
        featureQuality: FeatureQuality;
        orthophotoResolution: number;
        dsm: boolean;
        dtm: boolean;
    };
    superpixel: {
        regionArea: number;
        compactness: number;
        sigma: number;
        tileSize: number;
    };
}
export interface ODMJobRequest {
    imagePath: string;
    rgbImagePath?: string; // Legacy compatibility only; not used by mixed-folder UI.
    outputPath: string;
    projectName: string;
    generateSuperpixels: boolean;
    settings: AppSettings;
}
// The original UI.py options are all represented: folder, output, project,
// split, overlap, pc quality, superpixel area/compactness/sigma/tile size.
// Split 2 is the project's prior value, NOT ODM's own upstream default.
export const DEFAULT_SETTINGS: AppSettings = {
    appearance: { theme: 'system' },
    docker: { platformPreference: 'auto', gpuMode: 'auto', autoStartDocker: true, maxConcurrency: 1 },
    odm: {
        split: 2,
        splitOverlap: 150,
        pointCloudQuality: 'high',
        featureQuality: 'high',
        orthophotoResolution: 5,
        dsm: false,
        dtm: false,
    },
    superpixel: { regionArea: 0.5, compactness: 10, sigma: 1, tileSize: 2048 },
};
const KEY = 'uwplatt-drone-ui-v2';
// Applied to the document root, so CSS (not processing code) controls the colors.
export function applyTheme(theme: Theme): void {
    if (typeof document !== 'undefined')
        document.documentElement.dataset.theme = theme;
}
export function readSettings(): AppSettings {
    try {
        const data = JSON.parse(localStorage.getItem(KEY) || '{}') as Partial<AppSettings>;
        const settings: AppSettings = {
            appearance: { ...DEFAULT_SETTINGS.appearance, ...data.appearance },
            docker: { ...DEFAULT_SETTINGS.docker, ...data.docker },
            odm: { ...DEFAULT_SETTINGS.odm, ...data.odm },
            superpixel: { ...DEFAULT_SETTINGS.superpixel, ...data.superpixel },
        };
        // Handle a saved setting before any page is opened.
        applyTheme(settings.appearance.theme);
        return settings;
    }
    catch {
        applyTheme(DEFAULT_SETTINGS.appearance.theme);
        return structuredClone(DEFAULT_SETTINGS);
    }
}
export function saveSettings(settings: AppSettings): void {
    applyTheme(settings.appearance.theme);
    localStorage.setItem(KEY, JSON.stringify(settings));
}
export function validateJob(job: ODMJobRequest): string | null {
    if (!job.imagePath.trim() || !job.outputPath.trim())
        return 'Choose image and output folders.';
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(job.projectName))
        return 'Project name must use letters, numbers, dots, dashes or underscores.';
    const d = job.settings.docker;
    const o = job.settings.odm;
    const s = job.settings.superpixel;
    if (!Number.isInteger(d.maxConcurrency) || d.maxConcurrency < 1 || d.maxConcurrency > 64)
        return 'Concurrency must be from 1 to 64.';
    if (!Number.isInteger(o.split) || o.split < 1)
        return 'Split size must be a positive whole number.';
    if (!Number.isFinite(o.splitOverlap) || o.splitOverlap < 0)
        return 'Split overlap cannot be negative.';
    if (!Number.isFinite(o.orthophotoResolution) || o.orthophotoResolution <= 0)
        return 'Orthophoto resolution must be positive.';
    if (job.generateSuperpixels && (!Number.isFinite(s.regionArea) || s.regionArea <= 0 || !Number.isFinite(s.compactness) || s.compactness <= 0 || !Number.isFinite(s.sigma) || s.sigma < 0 || !Number.isInteger(s.tileSize) || s.tileSize < 1))
        return 'Invalid superpixel settings.';
    return null;
}
