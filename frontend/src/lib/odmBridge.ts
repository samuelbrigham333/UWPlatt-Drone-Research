/**
 * Tauri-to-Python bridge.
 * Centralizes native folder selection, system diagnostics,
 * processing commands, and backend event subscriptions.
 */

import { invoke, isTauri } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { open } from '@tauri-apps/plugin-dialog';
import type { ODMJobRequest } from '../types/appSettings';
export interface SystemInfo {
    os: string;
    arch: string;
    dockerInstalled: boolean;
    dockerRunning: boolean;
    nvidiaHostVisible: boolean;
}
export interface ODMEvent {
    jobId: string;
    kind: 'log' | 'stage' | 'finish';
    message: string;
    stage?: string;
    success?: boolean;
}
export async function chooseFolder(): Promise<string | null> {
    if (!isTauri())
        throw new Error('Native folder selection requires the Tauri desktop app.');
    const selection = await open({ directory: true, multiple: false, title: 'Choose folder' });
    return typeof selection === 'string' ? selection : null;
}
export async function getSystemInfo(): Promise<SystemInfo> {
    if (!isTauri())
        throw new Error('System checks require the Tauri desktop app.');
    return invoke<SystemInfo>('odm_system_info');
}
export function onODMEvent(callback: (event: ODMEvent) => void): Promise<() => void> {
    return listen<ODMEvent>('odm-event', (e) => callback(e.payload));
}
export async function startODM(jobId: string, request: ODMJobRequest): Promise<void> {
    if (!isTauri())
        throw new Error('Start ODM inside Tauri, not the regular web browser.');
    return invoke('odm_start', { jobId, requestJson: JSON.stringify(request) });
}
export async function cancelODM(jobId: string): Promise<void> {
    return invoke('odm_cancel', { jobId });
}
