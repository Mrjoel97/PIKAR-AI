INSERT INTO skills (name, description, category, content, metadata)
VALUES
); // size 2, offset 3
```

## EdgesGeometry & WireframeGeometry

```javascript
// Edge lines (only hard edges)
const edges = new THREE.EdgesGeometry(boxGeometry, 15); // 15 = threshold angle
const edgeMesh = new THREE.LineSegments(
  edges,
  new THREE.LineBasicMaterial({ color: 0xffffff });