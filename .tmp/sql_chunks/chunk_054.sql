INSERT INTO skills (name, description, category, content, metadata)
VALUES
);
const segments = new THREE.LineSegments(segmentsGeometry, material);
```

## InstancedMesh

Efficiently render many copies of the same geometry.

```javascript
const geometry = new THREE.BoxGeometry(1, 1, 1);
const material = new THREE.MeshStandardMaterial({ color: 0x00ff00 });
const count = 1000;

const instancedMesh = new THREE.InstancedMesh(geometry, material, count);

// Set transforms for each instance
const dummy = new THREE.Object3D();
const matrix = new THREE.Matrix4();

for (let i = 0; i < count; i++) {
  dummy.position.set(
    (Math.random() - 0.5) * 20,
    (Math.random() - 0.5) * 20,
    (Math.random() - 0.5) * 20,
  );
  dummy.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, 0);
  dummy.scale.setScalar(0.5 + Math.random());
  dummy.updateMatrix();

  instancedMesh.setMatrixAt(i, dummy.matrix);
}

// Flag for GPU update
instancedMesh.instanceMatrix.needsUpdate = true;

// Optional: per-instance colors
instancedMesh.instanceColor = new THREE.InstancedBufferAttribute(
  new Float32Array(count * 3);