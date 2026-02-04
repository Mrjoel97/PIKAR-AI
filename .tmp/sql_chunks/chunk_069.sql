INSERT INTO skills (name, description, category, content, metadata)
VALUES
);
scene.add(placeholder);

loadModel("model.glb").then((gltf) => {
  scene.remove(placeholder);
  scene.add(gltf.scene);
});
```

## See Also

- `threejs-textures` - Texture configuration
- `threejs-animation` - Playing loaded animations
- `threejs-materials` - Material from loaded models
', '{"name": "threejs-loaders", "description": "Three.js asset loading - GLTF, textures, images, models, async patterns. Use when loading 3D models, textures, HDR environments, or managing loading progress."}'::jsonb);