INSERT INTO skills (name, description, category, content, metadata)
VALUES
specularIntensityMap: specIntTexture,
  specularColorMap: specColorTexture,
});
```

### Glass Material Example

```javascript
const glass = new THREE.MeshPhysicalMaterial({
  color: 0xffffff,
  metalness: 0,
  roughness: 0,
  transmission: 1,
  thickness: 0.5,
  ior: 1.5,
  envMapIntensity: 1,
});
```

### Car Paint Example

```javascript
const carPaint = new THREE.MeshPhysicalMaterial({
  color: 0xff0000,
  metalness: 0.9,
  roughness: 0.5,
  clearcoat: 1,
  clearcoatRoughness: 0.1,
});
```

## MeshToonMaterial

Cel-shaded cartoon look.

```javascript
const material = new THREE.MeshToonMaterial({
  color: 0x00ff00,
  gradientMap: gradientTexture, // Optional: custom shading gradient
});

// Create step gradient texture
const colors = new Uint8Array([0, 128, 255]);
const gradientMap = new THREE.DataTexture(colors, 3, 1, THREE.RedFormat);
gradientMap.minFilter = THREE.NearestFilter;
gradientMap.magFilter = THREE.NearestFilter;
gradientMap.needsUpdate = true;
```

## MeshNormalMaterial

Visualize surface normals. Useful for debugging.

```javascript
const material = new THREE.MeshNormalMaterial({
  flatShading: false,
  wireframe: false,
});
```

## MeshDepthMaterial

Render depth values. Used for shadow maps, DOF effects.

```javascript
const material = new THREE.MeshDepthMaterial({
  depthPacking: THREE.RGBADepthPacking,
});
```

## PointsMaterial

For point clouds.

```javascript
const material = new THREE.PointsMaterial({
  color: 0xffffff,
  size: 0.1,
  sizeAttenuation: true, // Scale with distance
  map: pointTexture,
  alphaMap: alphaTexture,
  transparent: true,
  alphaTest: 0.5, // Discard pixels below threshold
  vertexColors: true, // Use per-vertex colors
});

const points = new THREE.Points(geometry, material);
```

## LineBasicMaterial & LineDashedMaterial

```javascript
// Solid lines
const lineMaterial = new THREE.LineBasicMaterial({
  color: 0xffffff,
  linewidth: 1, // Note: >1 only works on some systems
  linecap: "round",
  linejoin: "round",
});

// Dashed lines
const dashedMaterial = new THREE.LineDashedMaterial({
  color: 0xffffff,
  dashSize: 0.5,
  gapSize: 0.25,
  scale: 1,
});

// Required for dashed lines
const line = new THREE.Line(geometry, dashedMaterial);
line.computeLineDistances();
```

## ShaderMaterial

Custom GLSL shaders with Three.js uniforms.

```javascript
const material = new THREE.ShaderMaterial({
  uniforms: {
    time: { value: 0 },
    color: { value: new THREE.Color(0xff0000) },
    texture1: { value: texture },
  },
  vertexShader: `
    varying vec2 vUv;
    uniform float time;

    void main() {
      vUv = uv;
      vec3 pos = position;
      pos.z += sin(pos.x * 10.0 + time) * 0.1;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    varying vec2 vUv;
    uniform vec3 color;
    uniform sampler2D texture1;

    void main() {
      // Use texture2D() for GLSL 1.0, texture() for GLSL 3.0 (glslVersion: THREE.GLSL3)
      vec4 texColor = texture2D(texture1, vUv);
      gl_FragColor = vec4(color * texColor.rgb, 1.0);
    }
  `,
  transparent: true,
  side: THREE.DoubleSide,
});

// Update uniform in animation loop
material.uniforms.time.value = clock.getElapsedTime();
```

### Built-in Uniforms (auto-provided)

```glsl
// Vertex shader
uniform mat4 modelMatrix;         // Object to world
uniform mat4 modelViewMatrix;     // Object to camera
uniform mat4 projectionMatrix;    // Camera projection
uniform mat4 viewMatrix;          // World to camera
uniform mat3 normalMatrix;        // For transforming normals
uniform vec3 cameraPosition;      // Camera world position

// Attributes
attribute vec3 position;
attribute vec3 normal;
attribute vec2 uv;
```

## RawShaderMaterial

Full control - no built-in uniforms/attributes.

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

## Common Material Properties

All materials share these base properties:

```javascript
// Visibility
material.visible = true;
material.transparent = false;
material.opacity = 1.0;
material.alphaTest = 0; // Discard pixels with alpha < value

// Rendering
material.side = THREE.FrontSide; // FrontSide, BackSide, DoubleSide
material.depthTest = true;
material.depthWrite = true;
material.colorWrite = true;

// Blending
material.blending = THREE.NormalBlending;
// NormalBlending, AdditiveBlending, SubtractiveBlending, MultiplyBlending, CustomBlending

// Stencil
material.stencilWrite = false;
material.stencilFunc = THREE.AlwaysStencilFunc;
material.stencilRef = 0;
material.stencilMask = 0xff;

// Polygon offset (z-fighting fix)
material.polygonOffset = false;
material.polygonOffsetFactor = 0;
material.polygonOffsetUnits = 0;

// Misc
material.dithering = false;
material.toneMapped = true;
```

## Multiple Materials

```javascript
// Assign different materials to geometry groups
const geometry = new THREE.BoxGeometry(1, 1, 1);
const materials = [
  new THREE.MeshBasicMaterial({ color: 0xff0000 }), // right
  new THREE.MeshBasicMaterial({ color: 0x00ff00 }), // left
  new THREE.MeshBasicMaterial({ color: 0x0000ff }), // top
  new THREE.MeshBasicMaterial({ color: 0xffff00 }), // bottom
  new THREE.MeshBasicMaterial({ color: 0xff00ff }), // front
  new THREE.MeshBasicMaterial({ color: 0x00ffff }), // back
];
const mesh = new THREE.Mesh(geometry, materials);

// Custom groups
geometry.clearGroups();
geometry.addGroup(0, 6, 0); // start, count, materialIndex
geometry.addGroup(6, 6, 1);
```

## Environment Maps

```javascript
// Load cube texture
const cubeLoader = new THREE.CubeTextureLoader();
const envMap = cubeLoader.load([
  "px.jpg",
  "nx.jpg", // positive/negative X
  "py.jpg",
  "ny.jpg", // positive/negative Y
  "pz.jpg",
  "nz.jpg", // positive/negative Z
]);

// Apply to material
material.envMap = envMap;
material.envMapIntensity = 1;

// Or set as scene environment (affects all PBR materials)
scene.environment = envMap;

// HDR environment (recommended)
import { RGBELoader } from "three/examples/jsm/loaders/RGBELoader.js";
const rgbeLoader = new RGBELoader();
rgbeLoader.load("environment.hdr", (texture) => {
  texture.mapping = THREE.EquirectangularReflectionMapping;
  scene.environment = texture;
  scene.background = texture;
});
```

## Material Cloning and Modification

```javascript
// Clone material
const clone = material.clone();
clone.color.set(0x00ff00);

// Modify at runtime
material.color.set(0xff0000);
material.needsUpdate = true; // Only needed for some changes

// When needsUpdate is required:
// - Changing flat shading
// - Changing texture
// - Changing transparent
// - Custom shader code changes
```

## Performance Tips

1. **Reuse materials**: Same material = batched draw calls
2. **Avoid transparent when possible**: Transparent materials require sorting
3. **Use alphaTest instead of transparency**: When applicable, faster
4. **Choose simpler materials**: Basic > Lambert > Phong > Standard > Physical
5. **Limit active lights**: Each light adds shader complexity

```javascript
// Material pooling
const materialCache = new Map();
function getMaterial(color) {
  const key = color.toString(16);
  if (!materialCache.has(key)) {
    materialCache.set(key, new THREE.MeshStandardMaterial({ color }));
  }
  return materialCache.get(key);
}

// Dispose when done
material.dispose();
```

## See Also

- `threejs-textures` - Texture loading and configuration
- `threejs-shaders` - Custom shader development
- `threejs-lighting` - Light interaction with materials
', '{"name": "threejs-materials", "description": "Three.js materials - PBR, basic, phong, shader materials, material properties. Use when styling meshes, working with textures, creating custom shaders, or optimizing material performance."}'::jsonb);