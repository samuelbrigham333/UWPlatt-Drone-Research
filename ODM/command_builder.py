"""Build the Docker command for one ODM pass.

The same class is used by the command-line application and the Tauri frontend.
The frontend's Python bridge translates UI setting names to this dictionary.
"""

import os
import platform
import re
from pathlib import Path

BEST_GSD_ORTHOPHOTO_RESOLUTION = 1.0


class ODMCommandBuilder:
    def __init__(self, image_path, output_path, project_name, options, image_directory=None):
        self.image_path = Path(image_path).expanduser().resolve()
        self.image_directory = (
            Path(image_directory).expanduser().resolve()
            if image_directory is not None else None
        )
        self.output_path = Path(output_path).expanduser().resolve()
        self.project_name = str(project_name)
        self.options = options

    def build_command(self):
        # ==========================================================
        # VALIDATE PROCESSING OPTIONS
        # ==========================================================
        options = self.options
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', self.project_name):
            raise ValueError('Invalid ODM project name.')

        gpu = options.get('gpu_mode', 'cpu')
        if gpu not in ('cpu', 'nvidia'):
            raise ValueError('Invalid GPU mode.')
        if gpu == 'nvidia' and platform.system() != 'Windows':
            raise ValueError('NVIDIA mode in this application is Windows-only.')

        split = int(options['split'])
        overlap = float(options['split_overlap'])
        quality = options.get('pc_quality', 'medium')
        feature_quality = options.get('feature_quality', 'high')

        raw_resolution = options.get(
            'orthophoto_resolution', BEST_GSD_ORTHOPHOTO_RESOLUTION
        )

        if raw_resolution is None or str(raw_resolution).strip() == '':
            resolution = BEST_GSD_ORTHOPHOTO_RESOLUTION
        else:
            try:
                resolution = float(raw_resolution)
            except (TypeError, ValueError):
                raise ValueError(
                    "Orthophoto resolution must be a positive number greater than zero or blank."
                )

        
        concurrency = int(options.get('max_concurrency', 1))

        if (
            split < 1
            or overlap < 0
            or (resolution is not None and resolution <= 0 )
            or not 1 <= concurrency <= 64
        ):
            raise ValueError('Invalid ODM numeric settings.')
        if quality not in ('lowest', 'low', 'medium', 'high', 'ultra'):
            raise ValueError('Invalid point cloud quality.')
        if feature_quality not in ('low', 'medium', 'high', 'ultra'):
            raise ValueError('Invalid feature quality.')

        # ==========================================================
        # CONSTRUCT DOCKER COMMAND
        # ==========================================================
        image_folder = self.image_directory or self.image_path
        docker_image = 'opendronemap/odm:3.6.1-gpu' if gpu == 'nvidia' else 'opendronemap/odm:3.6.1'
        command = ['docker', 'run', '--rm']

        # Tauri uses a job-specific name to stop the right container.
        container_name = os.environ.get('ODM_UI_CONTAINER_NAME', '')
        if container_name:
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', container_name):
                raise ValueError('Invalid Docker container name.')
            command.extend(['--name', container_name])

        if gpu == 'nvidia':
            command.extend(['--gpus', 'all'])

        command.extend([
            '-v', f'{self.output_path}:/datasets',
            '-v', f'{image_folder}:/datasets/{self.project_name}/images',
            docker_image,
            '--project-path', '/datasets', self.project_name,
            '--split', str(split),
            '--split-overlap', str(overlap),
            '--pc-quality', quality,
            '--feature-quality', feature_quality,
            '--orthophoto-compression', 'DEFLATE',
            '--max-concurrency', str(concurrency),
        ])

        if resolution is not None:
            command.extend(['--orthophoto-resolution', str(resolution)])

        if gpu == 'nvidia':
            command.extend(['--feature-type', 'sift'])
        if options.get('dsm', False):
            command.append('--dsm')
        if options.get('dtm', False):
            command.append('--dtm')

        return command
