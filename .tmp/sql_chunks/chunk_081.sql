INSERT INTO skills (name, description, category, content, metadata)
VALUES
);

composer.addPass(smaaPass);
```

### SSAO (Ambient Occlusion)

```javascript
import { SSAOPass } from "three/addons/postprocessing/SSAOPass.js";

const ssaoPass = new SSAOPass(
  scene,
  camera,
  window.innerWidth,
  window.innerHeight,
);
ssaoPass.kernelRadius = 16;
ssaoPass.minDistance = 0.005;
ssaoPass.maxDistance = 0.1;

composer.addPass(ssaoPass);

// Output modes
ssaoPass.output = SSAOPass.OUTPUT.Default;
// SSAOPass.OUTPUT.Default - Final composited output
// SSAOPass.OUTPUT.SSAO - Just the AO
// SSAOPass.OUTPUT.Blur - Blurred AO
// SSAOPass.OUTPUT.Depth - Depth buffer
// SSAOPass.OUTPUT.Normal - Normal buffer
```

### Depth of Field (DOF)

```javascript
import { BokehPass } from "three/addons/postprocessing/BokehPass.js";

const bokehPass = new BokehPass(scene, camera, {
  focus: 10.0, // Focus distance
  aperture: 0.025, // Aperture (smaller = more DOF)
  maxblur: 0.01, // Max blur amount
});

composer.addPass(bokehPass);

// Update focus dynamically
bokehPass.uniforms["focus"].value = distanceToTarget;
```

### Film Grain

```javascript
import { FilmPass } from "three/addons/postprocessing/FilmPass.js";

const filmPass = new FilmPass(
  0.35, // noise intensity
  0.5, // scanline intensity
  648, // scanline count
  false, // grayscale
);

composer.addPass(filmPass);
```

### Vignette

```javascript
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { VignetteShader } from "three/addons/shaders/VignetteShader.js";

const vignettePass = new ShaderPass(VignetteShader);
vignettePass.uniforms["offset"].value = 1.0; // Vignette size
vignettePass.uniforms["darkness"].value = 1.0; // Vignette intensity

composer.addPass(vignettePass);
```

### Color Correction

```javascript
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { ColorCorrectionShader } from "three/addons/shaders/ColorCorrectionShader.js";

const colorPass = new ShaderPass(ColorCorrectionShader);
colorPass.uniforms["powRGB"].value = new THREE.Vector3(1.2, 1.2, 1.2); // Power
colorPass.uniforms["mulRGB"].value = new THREE.Vector3(1.0, 1.0, 1.0); // Multiply

composer.addPass(colorPass);
```

### Gamma Correction

```javascript
import { GammaCorrectionShader } from "three/addons/shaders/GammaCorrectionShader.js";

const gammaPass = new ShaderPass(GammaCorrectionShader);
composer.addPass(gammaPass);
```

### Pixelation

```javascript
import { RenderPixelatedPass } from "three/addons/postprocessing/RenderPixelatedPass.js";

const pixelPass = new RenderPixelatedPass(6, scene, camera); // 6 = pixel size

composer.addPass(pixelPass);
```

### Glitch Effect

```javascript
import { GlitchPass } from "three/addons/postprocessing/GlitchPass.js";

const glitchPass = new GlitchPass();
glitchPass.goWild = false; // Continuous glitching

composer.addPass(glitchPass);
```

### Halftone

```javascript
import { HalftonePass } from "three/addons/postprocessing/HalftonePass.js";

const halftonePass = new HalftonePass(window.innerWidth, window.innerHeight, {
  shape: 1, // 1 = dot, 2 = ellipse, 3 = line, 4 = square
  radius: 4, // Dot size
  rotateR: Math.PI / 12,
  rotateB: (Math.PI / 12) * 2,
  rotateG: (Math.PI / 12) * 3,
  scatter: 0,
  blending: 1,
  blendingMode: 1,
  greyscale: false,
});

composer.addPass(halftonePass);
```

### Outline

```javascript
import { OutlinePass } from "three/addons/postprocessing/OutlinePass.js";

const outlinePass = new OutlinePass(
  new THREE.Vector2(window.innerWidth, window.innerHeight);