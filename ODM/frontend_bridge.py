"""Tauri entry point for exactly the same dual-ODM service used by ODM/app.py.

Run from repository root:
    python -u -m ODM.frontend_bridge '<JSON-request>' job-example

A GUI request replaces UserInterface.get_odm_configuration() only for this run.
The terminal/CLI still calls the same service without a config and keeps its prompts.
"""
import json
import os
import platform
import re
import sys
import traceback
from pathlib import Path

from ODM.command_builder import BEST_GSD_ORTHOPHOTO_RESOLUTION
from ODM.orthomosaic_preview import OrthomosaicPreviewService



# Parse user-selected paths here instead of depending on the CLI UI module.
def parse_path(value):
    """Convert a native folder picker path or a quoted pasted path to Path."""
    raw = str(value).strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("\"", "'"):
        raw = raw[1:-1]
    if not raw:
        raise ValueError('A folder path is required.')
    return Path(raw).expanduser().resolve()


def emit(stage, message=None):
    print('@@ODM_EVENT@@' + json.dumps({
        'kind': 'stage', 'stage': stage, 'message': message or stage
    }), flush=True)


def nvidia_available_on_host():
    """Use the same NVIDIA detection as the command-line backend."""
    from ODM.docker_manager import DockerManager
    return DockerManager().nvidia_gpu_available()


def resolve_gpu_mode(preference):
    """Auto chooses a candidate engine; Docker access must still be checked at run time."""
    if preference not in ('auto', 'cpu', 'nvidia'):
        raise ValueError('GPU preference must be auto, cpu, or nvidia.')
    system = platform.system()
    if preference == 'cpu':
        return 'cpu'
    if preference == 'nvidia':
        if system != 'Windows':
            raise ValueError('NVIDIA mode is supported here only on Windows with Docker GPU access.')
        if not nvidia_available_on_host():
            raise ValueError('NVIDIA driver not detected. Use CPU or install/configure the driver.')
        return 'nvidia'
    # The requested supported systems are Windows (CPU or NVIDIA) and Mac (CPU).
    return 'nvidia' if system == 'Windows' and nvidia_available_on_host() else 'cpu'


def parse_request(request):
    """Convert typed React fields to the existing service's config format."""
    if not isinstance(request, dict):
        raise ValueError('Request must be an object.')
    image_path = parse_path(request.get('imagePath', ''))
    output_path = parse_path(request.get('outputPath', ''))
    project_name = request.get('projectName', '')
    if not isinstance(project_name, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}', project_name):
        raise ValueError('Invalid project name.')
    if not image_path.is_dir():
        raise FileNotFoundError(f'Image folder not found: {image_path}')
    output_path.mkdir(parents=True, exist_ok=True)
    if not output_path.is_dir():
        raise NotADirectoryError(f'Invalid output folder: {output_path}')
    if image_path == output_path or image_path in output_path.parents:
        raise ValueError('Output folder must not be the source image folder or inside it.')

    # The existing RGB workflow looks for *_D.JPG in the SAME folder.
    rgb_images = sorted(p for p in image_path.iterdir()
                        if p.is_file() and p.name.upper().endswith('_D.JPG'))
    if not rgb_images:
        raise FileNotFoundError(f'No *_D.JPG RGB images were found in {image_path}. '
                                'The existing service uses this filename convention.')

    settings = request['settings']
    docker = settings['docker']
    odm = settings['odm']
    gpu = resolve_gpu_mode(docker['gpuMode'])
    print(f'Host: {platform.system()} ({platform.machine()}); ODM engine: {gpu.upper()}', flush=True)
    if gpu == 'nvidia':
        print('NVIDIA GPU detected on Windows. Docker GPU passthrough is required; host detection alone is not proof.', flush=True)
    concurrency = int(docker['maxConcurrency'])
    if not 1 <= concurrency <= 64:
        raise ValueError('Concurrency must be 1–64.')
    split = int(odm['split'])
    overlap = float(odm['splitOverlap'])
    if split <= 0 or overlap < 0:
        raise ValueError('Invalid split/overlap settings.')
    resolution_mode = odm.get('orthophotoResolutionMode', 'best-gsd')
    if resolution_mode not in ('best-gsd', 'manual'):
        raise ValueError('Invalid orthophoto resolution mode.')
    resolution = (
        BEST_GSD_ORTHOPHOTO_RESOLUTION
        if resolution_mode == 'best-gsd'
        else float(odm['orthophotoResolution'])
    )
    if resolution <= 0:
        raise ValueError('Orthophoto resolution must be positive.')
    # This first integration is ODM-only. Reject unsupported workflows
    # explicitly instead of accidentally calling an interactive CLI prompt.
    if request.get('generateSuperpixels', False):
        raise ValueError('Superpixel generation is not connected on this page yet.')

    return {
        'image_path': image_path,
        'output_path': output_path,
        'project_name': project_name,
        'pipeline_options': {
            'split': split,
            'split_overlap': overlap,
            'pc_quality': odm['pointCloudQuality'],
            'feature_quality': odm['featureQuality'],
            'dsm': bool(odm['dsm']),
            'dtm': bool(odm['dtm']),
            'gpu_mode': gpu,
            'max_concurrency': concurrency,
        }
    }


def run_request(request, job_id='job-cli-test'):
    """Run the real service. Kept separate for easy unit testing."""
    if not re.fullmatch(r'job-[a-zA-Z0-9-]{1,64}', job_id):
        raise ValueError('Invalid job ID')
    config = parse_request(request)
    # Existing Rust stop command uses this predictable Docker container name.
    os.environ['ODM_UI_CONTAINER_NAME'] = 'uwplatt-' + job_id
    try:
        from services.odm_processing_service import ODMProcessingService
        service = ODMProcessingService(stage_callback=lambda stage: emit(stage))
        ortho, rgb = service.process_images(
            config=config,
            auto_start_docker=bool(request['settings']['docker']['autoStartDocker']),
        )
        print(f'Multispectral orthomosaic: {ortho}', flush=True)
        print(f'RGB orthomosaic: {rgb}', flush=True)
        emit('Completed', 'Both ODM passes completed successfully.')
        return ortho, rgb
    finally:
        os.environ.pop('ODM_UI_CONTAINER_NAME', None)


def main():
    request = json.loads(sys.argv[1])
    job_id = sys.argv[2] if len(sys.argv) > 2 else 'job-legacy'
    return run_request(request, job_id)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        traceback.print_exc()
        emit('Failed', f'ERROR: {error}')
        sys.exit(1)

def generate_preview(
        raster_path,
        output_path,
):
    """Generates an orthomosaic preview for the frontend."""

    raster_path = Path(raster_path)

    if not raster_path.is_file():
        raise FileNotFoundError(f'Orthomosaic not found: {raster_path}')

    preview_path = OrthomosaicPreviewService.generate_preview(
        raster_path=raster_path,
        output_path=output_path,
    )

    return {
        'preview_path': str(preview_path)
    }