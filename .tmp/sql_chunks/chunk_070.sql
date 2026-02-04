INSERT INTO skills (name, description, category, content, metadata)
VALUES
('threejs-materials', 'Three.js materials - PBR, basic, phong, shader materials, material properties. Use when styling meshes, working with textures, creating custom shaders, or optimizing material performance.', 'general', '---
name: threejs-materials
description: Three.js materials - PBR, basic, phong, shader materials, material properties. Use when styling meshes, working with textures, creating custom shaders, or optimizing material performance.
---

# Three.js Materials

## Quick Start

```javascript
import * as THREE from "three";

// PBR material (recommended for realistic rendering)
const material = new THREE.MeshStandardMaterial({
  color: 0x00ff00,
  roughness: 0.5,
  metalness: 0.5,
});

const mesh = new THREE.Mesh(geometry, material);
```

## Material Types Overview

| Material             | Use Case                              | Lighting           |
| -------------------- | ------------------------------------- | ------------------ |
| MeshBasicMaterial    | Unlit, flat colors, wireframes        | No                 |
| MeshLambertMaterial  | Matte surfaces, performance           | Yes (diffuse only) |
| MeshPhongMaterial    | Shiny surfaces, specular highlights   | Yes                |
| MeshStandardMaterial | PBR, realistic materials              | Yes (PBR)          |
| MeshPhysicalMaterial | Advanced PBR, clearcoat, transmission | Yes (PBR+)         |
| MeshToonMaterial     | Cel-shaded, cartoon look              | Yes (toon)         |
| MeshNormalMaterial   | Debug normals                         | No                 |
| MeshDepthMaterial    | Depth visualization                   | No                 |
| ShaderMaterial       | Custom GLSL shaders                   | Custom             |
| RawShaderMaterial    | Full shader control                   | Custom             |

## MeshBasicMaterial

No lighting calculations. Fast, always visible.

```javascript
const material = new THREE.MeshBasicMaterial({
  color: 0xff0000,
  transparent: true,
  opacity: 0.5,
  side: THREE.DoubleSide, // FrontSide, BackSide, DoubleSide
  wireframe: false,
  map: texture, // Color/diffuse texture
  alphaMap: alphaTexture, // Transparency texture
  envMap: envTexture, // Reflection texture
  reflectivity: 1, // Env map intensity
  fog: true, // Affected by scene fog
});
```

## MeshLambertMaterial

Diffuse-only lighting. Fast, no specular highlights.

```javascript
const material = new THREE.MeshLambertMaterial({
  color: 0x00ff00,
  emissive: 0x111111, // Self-illumination color
  emissiveIntensity: 1,
  map: texture,
  emissiveMap: emissiveTexture,
  envMap: envTexture,
  reflectivity: 0.5,
});
```

## MeshPhongMaterial

Specular highlights. Good for shiny, plastic-like surfaces.

```javascript
const material = new THREE.MeshPhongMaterial({
  color: 0x0000ff,
  specular: 0xffffff, // Highlight color
  shininess: 100, // Highlight sharpness (0-1000)
  emissive: 0x000000,
  flatShading: false, // Flat vs smooth shading
  map: texture,
  specularMap: specTexture, // Per-pixel shininess
  normalMap: normalTexture,
  normalScale: new THREE.Vector2(1, 1);