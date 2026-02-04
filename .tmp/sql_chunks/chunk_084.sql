INSERT INTO skills (name, description, category, content, metadata)
VALUES
strength,
  radius,
  threshold,
);

// Only apply effects in high-performance scenarios
const isMobile = /iPhone|iPad|Android/i.test(navigator.userAgent);
if (!isMobile) {
  composer.addPass(expensivePass);
}
```

## Handle Resize

```javascript
function onWindowResize() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const pixelRatio = renderer.getPixelRatio();

  camera.aspect = width / height;
  camera.updateProjectionMatrix();

  renderer.setSize(width, height);
  composer.setSize(width, height);

  // Update pass-specific resolutions
  if (fxaaPass) {
    fxaaPass.material.uniforms["resolution"].value.set(
      1 / (width * pixelRatio);