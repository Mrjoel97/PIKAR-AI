INSERT INTO skills (name, description, category, content, metadata)
VALUES
aoMap: aoTexture, // Ambient occlusion (uses uv2!)
  aoMapIntensity: 1,
  displacementMap: dispTexture, // Vertex displacement
  displacementScale: 0.1,
  displacementBias: 0,

  // Emissive
  emissive: 0x000000,
  emissiveIntensity: 1,
  emissiveMap: emissiveTexture,

  // Environment
  envMap: envTexture,
  envMapIntensity: 1,

  // Other
  flatShading: false,
  wireframe: false,
  fog: true,
});

// Note: aoMap requires second UV channel
geometry.setAttribute("uv2", geometry.attributes.uv);
```

## MeshPhysicalMaterial (Advanced PBR)

Extends MeshStandardMaterial with advanced features.

```javascript
const material = new THREE.MeshPhysicalMaterial({
  // All MeshStandardMaterial properties plus:

  // Clearcoat (car paint, lacquer)
  clearcoat: 1.0, // 0-1 clearcoat layer strength
  clearcoatRoughness: 0.1,
  clearcoatMap: ccTexture,
  clearcoatRoughnessMap: ccrTexture,
  clearcoatNormalMap: ccnTexture,
  clearcoatNormalScale: new THREE.Vector2(1, 1);