INSERT INTO skills (name, description, category, content, metadata)
VALUES
);
```

## Common Lighting Setups

### Three-Point Lighting

```javascript
// Key light (main light)
const keyLight = new THREE.DirectionalLight(0xffffff, 1);
keyLight.position.set(5, 5, 5);
scene.add(keyLight);

// Fill light (softer, opposite side)
const fillLight = new THREE.DirectionalLight(0xffffff, 0.5);
fillLight.position.set(-5, 3, 5);
scene.add(fillLight);

// Back light (rim lighting)
const backLight = new THREE.DirectionalLight(0xffffff, 0.3);
backLight.position.set(0, 5, -5);
scene.add(backLight);

// Ambient fill
const ambient = new THREE.AmbientLight(0x404040, 0.3);
scene.add(ambient);
```

### Outdoor Daylight

```javascript
// Sun
const sun = new THREE.DirectionalLight(0xffffcc, 1.5);
sun.position.set(50, 100, 50);
sun.castShadow = true;
scene.add(sun);

// Sky ambient
const hemi = new THREE.HemisphereLight(0x87ceeb, 0x8b4513, 0.6);
scene.add(hemi);
```

### Indoor Studio

```javascript
// Multiple area lights
RectAreaLightUniformsLib.init();

const light1 = new THREE.RectAreaLight(0xffffff, 5, 2, 2);
light1.position.set(3, 3, 3);
light1.lookAt(0, 0, 0);
scene.add(light1);

const light2 = new THREE.RectAreaLight(0xffffff, 3, 2, 2);
light2.position.set(-3, 3, 3);
light2.lookAt(0, 0, 0);
scene.add(light2);

// Ambient fill
const ambient = new THREE.AmbientLight(0x404040, 0.2);
scene.add(ambient);
```

## Light Animation

```javascript
const clock = new THREE.Clock();

function animate() {
  const time = clock.getElapsedTime();

  // Orbit light around scene
  light.position.x = Math.cos(time) * 5;
  light.position.z = Math.sin(time) * 5;

  // Pulsing intensity
  light.intensity = 1 + Math.sin(time * 2) * 0.5;

  // Color cycling
  light.color.setHSL((time * 0.1) % 1, 1, 0.5);

  // Update helpers if using
  lightHelper.update();
}
```

## Performance Tips

1. **Limit light count**: Each light adds shader complexity
2. **Use baked lighting**: For static scenes, bake to textures
3. **Smaller shadow maps**: 512-1024 often sufficient
4. **Tight shadow frustums**: Only cover needed area
5. **Disable unused shadows**: Not all lights need shadows
6. **Use light layers**: Exclude objects from certain lights

```javascript
// Light layers
light.layers.set(1); // Light only affects layer 1
mesh.layers.enable(1); // Mesh is on layer 1
otherMesh.layers.disable(1); // Other mesh not affected

// Selective shadows
mesh.castShadow = true;
mesh.receiveShadow = true;
decorMesh.castShadow = false; // Small objects often don''t need to cast
```

## See Also

- `threejs-materials` - Material light response
- `threejs-textures` - Lightmaps and environment maps
- `threejs-postprocessing` - Bloom and other light effects
', '{"name": "threejs-lighting", "description": "Three.js lighting - light types, shadows, environment lighting. Use when adding lights, configuring shadows, setting up IBL, or optimizing lighting performance."}'::jsonb);