INSERT INTO skills (name, description, category, content, metadata)
VALUES
bumpMap: bumpTexture,
  bumpScale: 1,
  displacementMap: dispTexture,
  displacementScale: 1,
});
```

## MeshStandardMaterial (PBR)

Physically-based rendering. Recommended for realistic results.

```javascript
const material = new THREE.MeshStandardMaterial({
  color: 0xffffff,
  roughness: 0.5, // 0 = mirror, 1 = diffuse
  metalness: 0.0, // 0 = dielectric, 1 = metal

  // Textures
  map: colorTexture, // Albedo/base color
  roughnessMap: roughTexture, // Per-pixel roughness
  metalnessMap: metalTexture, // Per-pixel metalness
  normalMap: normalTexture, // Surface detail
  normalScale: new THREE.Vector2(1, 1);