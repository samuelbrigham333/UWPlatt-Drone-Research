Drone Image Processing Pipeline

Python application for processing drone imagery with OpenDroneMap (ODM), extracting multispectral features, generating superpixels, and preparing data for future machine-learning workflows.

Overview

This project provides a command-line workflow around OpenDroneMap running in Docker. The application is designed to be modular so additional image-processing and machine-learning functionality can be added without rebuilding the core ODM workflow.

The current processing flow is:

Validate Docker and input paths.

Collect ODM processing options.

Run OpenDroneMap in Docker.

Locate the generated multispectral orthomosaic.

Tile the orthomosaic to reduce memory usage.

Segment each tile with SLIC superpixels.

Calculate vegetation indices.

Extract statistics for each superpixel.

Export feature data for later analysis and machine learning.

Develop an RGB orthomosaic workflow using the original RGB _D.JPG images.

Project Structure

Drone_Stuff/
│
├── Main.py
│
└── ODM/
    ├── app.py
    ├── command_builder.py
    ├── docker_manager.py
    ├── runner.py
    ├── ui.py
    ├── validate_images.py
    │
    ├── RGBOrthoBuilder.py
    │
    ├── superpixel_segmenter.py
    ├── region_feature_extractor.py
    ├── superpixel_dataset_exporter.py
    │
    └── raster/
        ├── raster_loader.py
        └── vegetation_indices.py

Main Application

Main.py is the application entry point:

from ODM.app import ODMApplication

if __name__ == "__main__":
    app = ODMApplication()
    app.execute()

The main application is responsible for coordinating the different parts of the processing pipeline.

Processing Workflow

1. ODM Processing

The user selects:

Image dataset directory

Output directory

Project name

Split size

Split overlap

Point-cloud quality

The application constructs the Docker command through ODMCommandBuilder and executes it through ODMRunner.

ODM is currently configured around:

opendronemap/odm:3.6.1

The project uses ODM's split processing to help manage large drone datasets.

2. Multispectral Orthomosaic

The multispectral processing produces an orthomosaic containing the expected bands:

Band

Meaning

Band 1

Red

Band 2

Green

Band 3

NIR

Band 4

Red Edge

Band 5

Alpha / mask

The Alpha band is used for raster/mask information but is not intended to be included in feature statistics.

3. Vegetation Indices

The VegetationIndices class calculates vegetation-related raster features including:

NDVI

GNDVI

NDRE

Evenson

CI Red Edge

The indices operate on the multispectral bands from the orthomosaic.

4. Tiling

Large orthomosaics are processed in tiles rather than loading the entire raster into memory at once.

The default tile size is:

2048 × 2048 pixels

This helps control memory usage when processing large orthomosaics.

5. Superpixel Segmentation

SLIC is used to divide each tile into visually/spectrally similar regions.

The user can configure:

Desired region area in square meters

SLIC compactness

Sigma

Tile size

The desired region area is converted into an approximate number of pixels based on the raster's pixel area.

6. Region Feature Extraction

RegionFeatureExtractor calculates statistics for every superpixel.

Current measurements include:

Pixel count

Area in square meters

Mean

Median

Standard deviation

Minimum

Maximum

10th percentile

90th percentile

These statistics can be calculated for the vegetation-index rasters and other feature rasters supplied to the extractor.

Each region receives a unique identifier such as:

T1_R42

where:

T1 identifies the tile

R42 identifies the region within that tile

RGB Orthomosaic Development

The project is also being extended to generate an RGB orthomosaic from the original RGB drone photographs.

The original dataset contains RGB and multispectral imagery together. RGB photographs use the _D.JPG naming pattern, while multispectral images use names such as:

_MS_G
_MS_NIR
_MS_R
_MS_RE

The RGB workflow is therefore intended to:

Use the same full-sized source dataset.

Identify the _D.JPG RGB images.

Avoid copying the original image dataset.

Reuse the existing ODM command-building and Docker-running infrastructure.

Produce an RGB orthomosaic that can later be used as the visual source for superpixel images.

The intended architecture is:

Original DJI Dataset
        │
        ├── Multispectral imagery
        │        │
        │        ▼
        │   ODM multispectral
        │        │
        │        ▼
        │   Multispectral orthomosaic
        │        │
        │        ▼
        │   SLIC / Features
        │
        └── *_D.JPG RGB imagery
                 │
                 ▼
          RGB ODM processing
                 │
                 ▼
           RGB orthomosaic
                 │
                 ▼
        Superpixel visualization

RGBOrthoBuilder is intentionally being kept thin. It is meant to reuse existing classes such as ODMCommandBuilder and ODMRunner rather than creating a second independent ODM pipeline.

Planned Superpixel Dataset

The eventual machine-learning dataset is intended to contain both tabular features and RGB imagery.

A planned structure is:

dataset/
├── images/
│   ├── T1_R42.png
│   ├── T1_R43.png
│   └── ...
│
├── labels.csv
└── metadata.csv

Example labeling information:

region_id,label,confidence,notes
T1_R0,soybean,high,
T1_R1,weed,high,
T1_R2,soil,medium,partially obscured
T1_R3,unknown,low,can't identify

The intended workflow is:

RGB Orthomosaic
       │
       ▼
Superpixel Map
       │
       ├── Full-color image with region outlines
       │
       └── Individual RGB image for each region
                    │
                    ▼
               Human labeling
                    │
                    ▼
              ML dataset

The project may eventually support both:

Tabular models using spectral and geometric features

Image-based models using RGB superpixel images

Multimodal models combining both types of information

Memory and Performance Considerations

Large drone orthomosaics can require substantial memory. The project therefore uses several strategies to limit memory requirements:

ODM split processing

Raster tiling

Processing one tile at a time

Explicit cleanup of large NumPy arrays where appropriate

Avoiding unnecessary copies of the original image dataset

Extracting regional statistics instead of keeping every intermediate result indefinitely

The application is intended to work with large drone datasets on systems with limited RAM.

Requirements

The project currently relies on:

Python

Docker Desktop

OpenDroneMap

NumPy

Rasterio

scikit-image

The exact Python package requirements should be maintained separately in the project's environment/dependency configuration as the project develops.

Running the Application

From the project directory, activate the virtual environment and run:

.\.venv\Scripts\python.exe Main.py

The main menu provides:

=== DRONE PROCESSING ===
1. Run ODM Processing
2. Analyze Existing Ortho
3. Exit

Docker must be available before ODM processing can run.

Development Principles

The project is being developed around a few design principles:

Reuse Existing Processing

New functionality should reuse existing ODM, Docker, validation, raster, and feature-extraction components whenever possible.

Avoid Duplicate Pipelines

RGB processing should not become an entirely separate implementation of the ODM workflow. RGB-specific behavior should be added around the existing pipeline where practical.

Avoid Copying Large Datasets

The original drone imagery should remain in its existing location. The application should avoid making unnecessary copies of large image datasets.

Modular Classes

Processing responsibilities are separated into classes so individual components can be expanded or replaced without rewriting the entire application.

User-Configurable Processing

Important processing parameters such as split size, overlap, superpixel area, compactness, sigma, and tile size should remain configurable rather than being permanently hard-coded.

Current Development Status

Working / established

ODM Docker processing

ODM split/overlap configuration

Orthomosaic discovery

Multispectral band validation

Raster loading

Vegetation-index calculation

Tiled processing

SLIC superpixel segmentation

Region feature extraction

Region identifiers

RGB image identification using _D.JPG

In development

RGB orthomosaic generation

RGB integration with the existing ODM pipeline

RGB superpixel visualization

Individual superpixel RGB image export

Human labeling workflow

Dataset export for machine learning

Future Goals

The longer-term goal is to create a reusable drone-image analysis pipeline capable of:

Processing large drone datasets.

Generating multispectral orthomosaics.

Generating RGB orthomosaics.

Segmenting imagery into meaningful regions.

Extracting spectral, vegetation, and geometric features.

Exporting labeled RGB samples.

Building machine-learning datasets.

Supporting future classification models such as Random Forest and image-based neural networks.

Eventually combining RGB imagery with multispectral/tabular features in a multimodal model.

GENERATED BY ChatGPT model GPT-6 Astra
