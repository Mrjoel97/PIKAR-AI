INSERT INTO skills (name, description, category, content, metadata)
VALUES
);

// Wireframe (all triangles)
const wireframe = new THREE.WireframeGeometry(boxGeometry);
const wireMesh = new THREE.LineSegments(
  wireframe,
  new THREE.LineBasicMaterial({ color: 0xffffff });