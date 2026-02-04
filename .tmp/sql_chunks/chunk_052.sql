INSERT INTO skills (name, description, category, content, metadata)
VALUES
);

// LineLoop (closed loop)
const loop = new THREE.LineLoop(geometry, material);

// LineSegments (pairs of points)
const segmentsGeometry = new THREE.BufferGeometry();
segmentsGeometry.setAttribute(
  "position",
  new THREE.BufferAttribute(
    new Float32Array([
      -1,
      0,
      0,
      0,
      1,
      0, // segment 1
      0,
      1,
      0,
      1,
      0,
      0, // segment 2
    ]);