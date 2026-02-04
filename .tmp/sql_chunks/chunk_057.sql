INSERT INTO skills (name, description, category, content, metadata)
VALUES
];

const mesh = new THREE.Mesh(geometry, material);
mesh.morphTargetInfluences[0] = 0.5; // 50% blend
```

## Performance Tips

1. **Use indexed geometry**: Reuse vertices with indices
2. **Merge static meshes**: Reduce draw calls with `mergeGeometries`
3. **Use InstancedMesh**: For many identical objects
4. **Choose appropriate segment counts**: More segments = smoother but slower
5. **Dispose unused geometry**: `geometry.dispose()`

```javascript
// Good segment counts for common uses
new THREE.SphereGeometry(1, 32, 32); // Good quality
new THREE.SphereGeometry(1, 64, 64); // High quality
new THREE.SphereGeometry(1, 16, 16); // Performance mode

// Dispose when done
geometry.dispose();
```

## See Also

- `threejs-fundamentals` - Scene setup and Object3D
- `threejs-materials` - Material types for meshes
- `threejs-shaders` - Custom vertex manipulation
', '{"name": "threejs-geometry", "description": "Three.js geometry creation - built-in shapes, BufferGeometry, custom geometry, instancing. Use when creating 3D shapes, working with vertices, building custom meshes, or optimizing with instanced rendering."}'::jsonb);