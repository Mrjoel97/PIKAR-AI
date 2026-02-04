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
  new THREE.Vector2(window.innerWidth, window.innerHeight),
scene,
  camera,
);

outlinePass.edgeStrength = 3;
outlinePass.edgeGlow = 0;
outlinePass.edgeThickness = 1;
outlinePass.pulsePeriod = 0;
outlinePass.visibleEdgeColor.set(0xffffff);
outlinePass.hiddenEdgeColor.set(0x190a05);

// Select objects to outline
outlinePass.selectedObjects = [mesh1, mesh2];

composer.addPass(outlinePass);
```

## Custom ShaderPass

Create your own post-processing effects.

```javascript
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";

const CustomShader = {
  uniforms: {
    tDiffuse: { value: null }, // Required: input texture
    time: { value: 0 },
    intensity: { value: 1.0 },
  },
  vertexShader: `
    varying vec2 vUv;

    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float time;
    uniform float intensity;
    varying vec2 vUv;

    void main() {
      vec2 uv = vUv;

      // Wave distortion
      uv.x += sin(uv.y * 10.0 + time) * 0.01 * intensity;

      vec4 color = texture2D(tDiffuse, uv);
      gl_FragColor = color;
    }
  `,
};

const customPass = new ShaderPass(CustomShader);
composer.addPass(customPass);

// Update in animation loop
customPass.uniforms.time.value = clock.getElapsedTime();
```

### Invert Colors Shader

```javascript
const InvertShader = {
  uniforms: {
    tDiffuse: { value: null },
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    varying vec2 vUv;

    void main() {
      vec4 color = texture2D(tDiffuse, vUv);
      gl_FragColor = vec4(1.0 - color.rgb, color.a);
    }
  `,
};
```

### Chromatic Aberration

```javascript
const ChromaticAberrationShader = {
  uniforms: {
    tDiffuse: { value: null },
    amount: { value: 0.005 },
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float amount;
    varying vec2 vUv;

    void main() {
      vec2 dir = vUv - 0.5;
      float dist = length(dir);

      float r = texture2D(tDiffuse, vUv - dir * amount * dist).r;
      float g = texture2D(tDiffuse, vUv).g;
      float b = texture2D(tDiffuse, vUv + dir * amount * dist).b;

      gl_FragColor = vec4(r, g, b, 1.0);
    }
  `,
};
```

## Combining Multiple Effects

```javascript
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { FXAAShader } from "three/addons/shaders/FXAAShader.js";
import { VignetteShader } from "three/addons/shaders/VignetteShader.js";
import { GammaCorrectionShader } from "three/addons/shaders/GammaCorrectionShader.js";

const composer = new EffectComposer(renderer);

// 1. Render scene
composer.addPass(new RenderPass(scene, camera));

// 2. Bloom
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
0.5,
  0.4,
  0.85,
);
composer.addPass(bloomPass);

// 3. Vignette
const vignettePass = new ShaderPass(VignetteShader);
vignettePass.uniforms["offset"].value = 0.95;
vignettePass.uniforms["darkness"].value = 1.0;
composer.addPass(vignettePass);

// 4. Gamma correction
composer.addPass(new ShaderPass(GammaCorrectionShader));

// 5. Anti-aliasing (always last before output)
const fxaaPass = new ShaderPass(FXAAShader);
fxaaPass.uniforms["resolution"].value.set(
  1 / window.innerWidth,
  1 / window.innerHeight,
);
composer.addPass(fxaaPass);
```

## Render to Texture

```javascript
// Create render target
const renderTarget = new THREE.WebGLRenderTarget(512, 512);

// Render scene to target
renderer.setRenderTarget(renderTarget);
renderer.render(scene, camera);
renderer.setRenderTarget(null);

// Use texture
const texture = renderTarget.texture;
otherMaterial.map = texture;
```

## Multi-Pass Rendering

```javascript
// Multiple composers for different scenes/layers
const bgComposer = new EffectComposer(renderer);
bgComposer.addPass(new RenderPass(bgScene, camera));

const fgComposer = new EffectComposer(renderer);
fgComposer.addPass(new RenderPass(fgScene, camera));
fgComposer.addPass(bloomPass);

// Combine in render loop
function animate() {
  // Render background without clearing
  renderer.autoClear = false;
  renderer.clear();

  bgComposer.render();

  // Render foreground over it
  renderer.clearDepth();
  fgComposer.render();
}
```

## WebGPU Post-Processing (Three.js r150+)

```javascript
import { postProcessing } from "three/addons/nodes/Nodes.js";
import { pass, bloom, dof } from "three/addons/nodes/Nodes.js";

// Using node-based system
const scenePass = pass(scene, camera);
const bloomNode = bloom(scenePass, 0.5, 0.4, 0.85);

const postProcessing = new THREE.PostProcessing(renderer);
postProcessing.outputNode = bloomNode;

// Render
function animate() {
  postProcessing.render();
}
```

## Performance Tips

1. **Limit passes**: Each pass adds a full-screen render
2. **Lower resolution**: Use smaller render targets for blur passes
3. **Disable unused effects**: Toggle passes on/off
4. **Use FXAA over MSAA**: Less expensive anti-aliasing
5. **Profile with DevTools**: Check GPU usage

```javascript
// Disable pass
bloomPass.enabled = false;

// Reduce bloom resolution
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth / 2, window.innerHeight / 2),
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
      1 / (width * pixelRatio),
1 / (height * pixelRatio),
);
  }

  if (bloomPass) {
    bloomPass.resolution.set(width, height);
  }
}

window.addEventListener("resize", onWindowResize);
```

## See Also

- `threejs-shaders` - Custom shader development
- `threejs-textures` - Render targets
- `threejs-fundamentals` - Renderer setup
', '{"name": "threejs-postprocessing", "description": "Three.js post-processing - EffectComposer, bloom, DOF, screen effects. Use when adding visual effects, color grading, blur, glow, or creating custom screen-space shaders."}'::jsonb),
('threejs-shaders', 'Three.js shaders - GLSL, ShaderMaterial, uniforms, custom effects. Use when creating custom visual effects, modifying vertices, writing fragment shaders, or extending built-in materials.', 'general', '---
name: threejs-shaders
description: Three.js shaders - GLSL, ShaderMaterial, uniforms, custom effects. Use when creating custom visual effects, modifying vertices, writing fragment shaders, or extending built-in materials.
---

# Three.js Shaders

## Quick Start

```javascript
import * as THREE from "three";

const material = new THREE.ShaderMaterial({
  uniforms: {
    time: { value: 0 },
    color: { value: new THREE.Color(0xff0000) },
  },
  vertexShader: `
    void main() {
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform vec3 color;

    void main() {
      gl_FragColor = vec4(color, 1.0);
    }
  `,
});

// Update in animation loop
material.uniforms.time.value = clock.getElapsedTime();
```

## ShaderMaterial vs RawShaderMaterial

### ShaderMaterial

Three.js provides built-in uniforms and attributes.

```javascript
const material = new THREE.ShaderMaterial({
  vertexShader: `
    // Built-in uniforms available:
    // uniform mat4 modelMatrix;
    // uniform mat4 modelViewMatrix;
    // uniform mat4 projectionMatrix;
    // uniform mat4 viewMatrix;
    // uniform mat3 normalMatrix;
    // uniform vec3 cameraPosition;

    // Built-in attributes available:
    // attribute vec3 position;
    // attribute vec3 normal;
    // attribute vec2 uv;

    void main() {
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    void main() {
      gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
    }
  `,
});
```

### RawShaderMaterial

Full control - you define everything.

```javascript
const material = new THREE.RawShaderMaterial({
  uniforms: {
    projectionMatrix: { value: camera.projectionMatrix },
    modelViewMatrix: { value: new THREE.Matrix4() },
  },
  vertexShader: `
    precision highp float;

    attribute vec3 position;
    uniform mat4 projectionMatrix;
    uniform mat4 modelViewMatrix;

    void main() {
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    precision highp float;

    void main() {
      gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
    }
  `,
});
```

## Uniforms

### Uniform Types

```javascript
const material = new THREE.ShaderMaterial({
  uniforms: {
    // Numbers
    floatValue: { value: 1.5 },
    intValue: { value: 1 },

    // Vectors
    vec2Value: { value: new THREE.Vector2(1, 2) },
    vec3Value: { value: new THREE.Vector3(1, 2, 3) },
    vec4Value: { value: new THREE.Vector4(1, 2, 3, 4) },

    // Colors (converted to vec3)
    colorValue: { value: new THREE.Color(0xff0000) },

    // Matrices
    mat3Value: { value: new THREE.Matrix3() },
    mat4Value: { value: new THREE.Matrix4() },

    // Textures
    textureValue: { value: texture },
    cubeTextureValue: { value: cubeTexture },

    // Arrays
    floatArray: { value: [1.0, 2.0, 3.0] },
    vec3Array: {
      value: [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0)],
    },
  },
});
```

### GLSL Declarations

```glsl
// In shader
uniform float floatValue;
uniform int intValue;
uniform vec2 vec2Value;
uniform vec3 vec3Value;
uniform vec3 colorValue;    // Color becomes vec3
uniform vec4 vec4Value;
uniform mat3 mat3Value;
uniform mat4 mat4Value;
uniform sampler2D textureValue;
uniform samplerCube cubeTextureValue;
uniform float floatArray[3];
uniform vec3 vec3Array[2];
```

### Updating Uniforms

```javascript
// Direct assignment
material.uniforms.time.value = clock.getElapsedTime();

// Vector/Color updates
material.uniforms.position.value.set(x, y, z);
material.uniforms.color.value.setHSL(hue, 1, 0.5);

// Matrix updates
material.uniforms.matrix.value.copy(mesh.matrixWorld);
```

## Varyings

Pass data from vertex to fragment shader.

```javascript
const material = new THREE.ShaderMaterial({
  vertexShader: `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vPosition;

    void main() {
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);
      vPosition = (modelViewMatrix * vec4(position, 1.0)).xyz;

      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vPosition;

    void main() {
      // Use interpolated values
      gl_FragColor = vec4(vNormal * 0.5 + 0.5, 1.0);
    }
  `,
});
```

## Common Shader Patterns

### Texture Sampling

```javascript
const material = new THREE.ShaderMaterial({
  uniforms: {
    map: { value: texture },
  },
  vertexShader: `
    varying vec2 vUv;

    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D map;
    varying vec2 vUv;

    void main() {
      vec4 texColor = texture2D(map, vUv);
      gl_FragColor = texColor;
    }
  `,
});
```

### Vertex Displacement

```javascript
const material = new THREE.ShaderMaterial({
  uniforms: {
    time: { value: 0 },
    amplitude: { value: 0.5 },
  },
  vertexShader: `
    uniform float time;
    uniform float amplitude;

    void main() {
      vec3 pos = position;

      // Wave displacement
      pos.z += sin(pos.x * 5.0 + time) * amplitude;
      pos.z += sin(pos.y * 5.0 + time) * amplitude;

      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    void main() {
      gl_FragColor = vec4(0.5, 0.8, 1.0, 1.0);
    }
  `,
});
```

### Fresnel Effect

```javascript
const material = new THREE.ShaderMaterial({
  vertexShader: `
    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    void main() {
      vNormal = normalize(normalMatrix * normal);
      vWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    void main() {
      // cameraPosition is auto-provided by ShaderMaterial
      vec3 viewDirection = normalize(cameraPosition - vWorldPosition);
      float fresnel = pow(1.0 - dot(viewDirection, vNormal), 3.0);

      vec3 baseColor = vec3(0.0, 0.0, 0.5);
      vec3 fresnelColor = vec3(0.5, 0.8, 1.0);

      gl_FragColor = vec4(mix(baseColor, fresnelColor, fresnel), 1.0);
    }
  `,
});
```

### Noise-Based Effects

```glsl
// Simple noise function
float random(vec2 st) {
  return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453);
}

// Value noise
float noise(vec2 st) {
  vec2 i = floor(st);
  vec2 f = fract(st);

  float a = random(i);
  float b = random(i + vec2(1.0, 0.0));
  float c = random(i + vec2(0.0, 1.0));
  float d = random(i + vec2(1.0, 1.0));

  vec2 u = f * f * (3.0 - 2.0 * f);

  return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
}

// Usage
float n = noise(vUv * 10.0 + time);
```

### Gradient

```glsl
// Linear gradient
vec3 color = mix(colorA, colorB, vUv.y);

// Radial gradient
float dist = distance(vUv, vec2(0.5));
vec3 color = mix(centerColor, edgeColor, dist * 2.0);

// Smooth gradient with custom curve
float t = smoothstep(0.0, 1.0, vUv.y);
vec3 color = mix(colorA, colorB, t);
```

### Rim Lighting

```javascript
const material = new THREE.ShaderMaterial({
  vertexShader: `
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    void main() {
      vNormal = normalize(normalMatrix * normal);
      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
      vViewPosition = mvPosition.xyz;
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  fragmentShader: `
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    void main() {
      vec3 viewDir = normalize(-vViewPosition);
      float rim = 1.0 - max(0.0, dot(viewDir, vNormal));
      rim = pow(rim, 4.0);

      vec3 baseColor = vec3(0.2, 0.2, 0.8);
      vec3 rimColor = vec3(1.0, 0.5, 0.0);

      gl_FragColor = vec4(baseColor + rimColor * rim, 1.0);
    }
  `,
});
```

### Dissolve Effect

```glsl
uniform float progress;
uniform sampler2D noiseMap;

void main() {
  float noise = texture2D(noiseMap, vUv).r;

  if (noise < progress) {
    discard;
  }

  // Edge glow
  float edge = smoothstep(progress, progress + 0.1, noise);
  vec3 edgeColor = vec3(1.0, 0.5, 0.0);
  vec3 baseColor = vec3(0.5);

  gl_FragColor = vec4(mix(edgeColor, baseColor, edge), 1.0);
}
```

## Extending Built-in Materials

### onBeforeCompile

Modify existing material shaders.

```javascript
const material = new THREE.MeshStandardMaterial({ color: 0x00ff00 });

material.onBeforeCompile = (shader) => {
  // Add custom uniform
  shader.uniforms.time = { value: 0 };

  // Store reference for updates
  material.userData.shader = shader;

  // Modify vertex shader
  shader.vertexShader = shader.vertexShader.replace(
    "#include <begin_vertex>",
    `
    #include <begin_vertex>
    transformed.y += sin(position.x * 10.0 + time) * 0.1;
    `,
  );

  // Add uniform declaration
  shader.vertexShader = "uniform float time;\n" + shader.vertexShader;
};

// Update in animation loop
if (material.userData.shader) {
  material.userData.shader.uniforms.time.value = clock.getElapsedTime();
}
```

### Common Injection Points

```javascript
// Vertex shader chunks
"#include <begin_vertex>"; // After position is calculated
"#include <project_vertex>"; // After gl_Position
"#include <beginnormal_vertex>"; // Normal calculation start

// Fragment shader chunks
"#include <color_fragment>"; // After diffuse color
"#include <output_fragment>"; // Final output
"#include <fog_fragment>"; // After fog applied
```

## GLSL Built-in Functions

### Math Functions

```glsl
// Basic
abs(x), sign(x), floor(x), ceil(x), fract(x)
mod(x, y), min(x, y), max(x, y), clamp(x, min, max)
mix(a, b, t), step(edge, x), smoothstep(edge0, edge1, x)

// Trigonometry
sin(x), cos(x), tan(x)
asin(x), acos(x), atan(y, x), atan(x)
radians(degrees), degrees(radians)

// Exponential
pow(x, y), exp(x), log(x), exp2(x), log2(x)
sqrt(x), inversesqrt(x)
```

### Vector Functions

```glsl
// Length and distance
length(v), distance(p0, p1), dot(x, y), cross(x, y)

// Normalization
normalize(v)

// Reflection and refraction
reflect(I, N), refract(I, N, eta)

// Component-wise
lessThan(x, y), lessThanEqual(x, y)
greaterThan(x, y), greaterThanEqual(x, y)
equal(x, y), notEqual(x, y)
any(bvec), all(bvec)
```

### Texture Functions

```glsl
// GLSL 1.0 (default) - use texture2D/textureCube
texture2D(sampler, coord)
texture2D(sampler, coord, bias)
textureCube(sampler, coord)

// GLSL 3.0 (glslVersion: THREE.GLSL3) - use texture()
// texture(sampler, coord) replaces texture2D/textureCube
// Also use: out vec4 fragColor instead of gl_FragColor

// Texture size (GLSL 1.30+)
textureSize(sampler, lod)
```

## Common Material Properties

```javascript
const material = new THREE.ShaderMaterial({
  uniforms: {
    /* ... */
  },
  vertexShader: "/* ... */",
  fragmentShader: "/* ... */",

  // Rendering
  transparent: true,
  opacity: 1.0,
  side: THREE.DoubleSide,
  depthTest: true,
  depthWrite: true,

  // Blending
  blending: THREE.NormalBlending,
  // AdditiveBlending, SubtractiveBlending, MultiplyBlending

  // Wireframe
  wireframe: false,
  wireframeLinewidth: 1, // Note: >1 has no effect on most platforms (WebGL limitation)

  // Extensions
  extensions: {
    derivatives: true, // For fwidth, dFdx, dFdy
    fragDepth: true, // gl_FragDepth
    drawBuffers: true, // Multiple render targets
    shaderTextureLOD: true, // texture2DLod
  },

  // GLSL version
  glslVersion: THREE.GLSL3, // For WebGL2 features
});
```

## Shader Includes

### Using Three.js Shader Chunks

```javascript
import { ShaderChunk } from "three";

const fragmentShader = `
  ${ShaderChunk.common}
  ${ShaderChunk.packing}

  uniform sampler2D depthTexture;
  varying vec2 vUv;

  void main() {
    float depth = texture2D(depthTexture, vUv).r;
    float linearDepth = perspectiveDepthToViewZ(depth, 0.1, 1000.0);
    gl_FragColor = vec4(vec3(-linearDepth / 100.0), 1.0);
  }
`;
```

### External Shader Files

```javascript
// With vite/webpack
import vertexShader from "./shaders/vertex.glsl";
import fragmentShader from "./shaders/fragment.glsl";

const material = new THREE.ShaderMaterial({
  vertexShader,
  fragmentShader,
});
```

## Instanced Shaders

```javascript
// Instanced attribute
const offsets = new Float32Array(instanceCount * 3);
// Fill offsets...
geometry.setAttribute("offset", new THREE.InstancedBufferAttribute(offsets, 3));

const material = new THREE.ShaderMaterial({
  vertexShader: `
    attribute vec3 offset;

    void main() {
      vec3 pos = position + offset;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    void main() {
      gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
    }
  `,
});
```

## Debugging Shaders

```javascript
// Check for compile errors
material.onBeforeCompile = (shader) => {
  console.log("Vertex Shader:", shader.vertexShader);
  console.log("Fragment Shader:", shader.fragmentShader);
};

// Visual debugging
fragmentShader: `
  void main() {
    // Debug UV
    gl_FragColor = vec4(vUv, 0.0, 1.0);

    // Debug normals
    gl_FragColor = vec4(vNormal * 0.5 + 0.5, 1.0);

    // Debug position
    gl_FragColor = vec4(vPosition * 0.1 + 0.5, 1.0);
  }
`;

// Check WebGL errors
renderer.debug.checkShaderErrors = true;
```

## Performance Tips

1. **Minimize uniforms**: Group related values into vectors
2. **Avoid conditionals**: Use mix/step instead of if/else
3. **Precalculate**: Move calculations to JS when possible
4. **Use textures**: For complex functions, use lookup tables
5. **Limit overdraw**: Avoid transparent objects when possible

```glsl
// Instead of:
if (value > 0.5) {
  color = colorA;
} else {
  color = colorB;
}

// Use:
color = mix(colorB, colorA, step(0.5, value));
```

## See Also

- `threejs-materials` - Built-in material types
- `threejs-postprocessing` - Full-screen shader effects
- `threejs-textures` - Texture sampling in shaders
', '{"name": "threejs-shaders", "description": "Three.js shaders - GLSL, ShaderMaterial, uniforms, custom effects. Use when creating custom visual effects, modifying vertices, writing fragment shaders, or extending built-in materials."}'::jsonb),
('threejs-textures', 'Three.js textures - texture types, UV mapping, environment maps, texture settings. Use when working with images, UV coordinates, cubemaps, HDR environments, or texture optimization.', 'general', '---
name: threejs-textures
description: Three.js textures - texture types, UV mapping, environment maps, texture settings. Use when working with images, UV coordinates, cubemaps, HDR environments, or texture optimization.
---

# Three.js Textures

## Quick Start

```javascript
import * as THREE from "three";

// Load texture
const loader = new THREE.TextureLoader();
const texture = loader.load("texture.jpg");

// Apply to material
const material = new THREE.MeshStandardMaterial({
  map: texture,
});
```

## Texture Loading

### Basic Loading

```javascript
const loader = new THREE.TextureLoader();

// Async with callbacks
loader.load(
  "texture.jpg",
  (texture) => console.log("Loaded"),
(progress) => console.log("Progress"),
(error) => console.error("Error");