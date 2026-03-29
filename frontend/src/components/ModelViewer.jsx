import { useRef, useEffect, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

export default function ModelViewer({ modelData }) {
  const containerRef = useRef(null)
  const sceneRef = useRef(null)
  const rendererRef = useRef(null)
  const cameraRef = useRef(null)
  const controlsRef = useRef(null)
  const animIdRef = useRef(null)

  const initScene = useCallback(() => {
    if (!containerRef.current || !modelData) return

    // Cleanup previous scene
    if (rendererRef.current) {
      cancelAnimationFrame(animIdRef.current)
      rendererRef.current.dispose()
      containerRef.current.innerHTML = ''
    }

    const container = containerRef.current
    const width = container.clientWidth
    const height = container.clientHeight || 400

    // Scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0d1117)
    scene.fog = new THREE.Fog(0x0d1117, 30, 60)
    sceneRef.current = scene

    // Camera
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100)
    camera.position.set(12, 10, 16)
    camera.lookAt(0, 0, 0)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.2
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.minDistance = 3
    controls.maxDistance = 50
    controls.maxPolarAngle = Math.PI / 2
    controlsRef.current = controls

    // Lighting
    const ambient = new THREE.AmbientLight(0xffffff, 0.4)
    scene.add(ambient)

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8)
    dirLight.position.set(10, 15, 10)
    dirLight.castShadow = true
    dirLight.shadow.mapSize.width = 2048
    dirLight.shadow.mapSize.height = 2048
    dirLight.shadow.camera.near = 0.5
    dirLight.shadow.camera.far = 50
    dirLight.shadow.camera.left = -20
    dirLight.shadow.camera.right = 20
    dirLight.shadow.camera.top = 20
    dirLight.shadow.camera.bottom = -20
    scene.add(dirLight)

    const fillLight = new THREE.DirectionalLight(0x6366f1, 0.3)
    fillLight.position.set(-8, 5, -8)
    scene.add(fillLight)

    // Ground grid
    const gridHelper = new THREE.GridHelper(40, 40, 0x334155, 0x1e293b)
    gridHelper.position.y = -0.16
    scene.add(gridHelper)

    // Calculate center offset for all meshes
    let centerX = 0, centerZ = 0, meshCount = 0
    modelData.meshes?.forEach(mesh => {
      centerX += mesh.position[0]
      centerZ += mesh.position[2]
      meshCount++
    })
    if (meshCount > 0) {
      centerX /= meshCount
      centerZ /= meshCount
    }

    // Build meshes
    modelData.meshes?.forEach(mesh => {
      if (mesh.type !== 'box') return

      const [w, h, d] = mesh.dimensions
      const geometry = new THREE.BoxGeometry(w, h, d)

      const color = new THREE.Color(mesh.color)
      const material = new THREE.MeshPhysicalMaterial({
        color: color,
        roughness: 0.7,
        metalness: 0.1,
        clearcoat: 0.1,
        transparent: mesh.element_type === 'floor',
        opacity: mesh.element_type === 'floor' ? 0.8 : 1.0,
      })

      const box = new THREE.Mesh(geometry, material)
      box.position.set(
        mesh.position[0] - centerX,
        mesh.position[1],
        mesh.position[2] - centerZ
      )
      box.castShadow = true
      box.receiveShadow = true

      // Store metadata for raycasting
      box.userData = {
        wall_id: mesh.wall_id,
        wall_type: mesh.wall_type,
        segment_type: mesh.segment_type,
        element_type: mesh.element_type,
      }

      scene.add(box)

      // Add edges for visual clarity
      const edges = new THREE.EdgesGeometry(geometry)
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x000000,
        opacity: 0.15,
        transparent: true,
      })
      const wireframe = new THREE.LineSegments(edges, lineMat)
      wireframe.position.copy(box.position)
      scene.add(wireframe)
    })

    // Add room labels as sprites
    modelData.labels?.forEach(label => {
      const canvas = document.createElement('canvas')
      canvas.width = 256
      canvas.height = 64
      const ctx = canvas.getContext('2d')
      ctx.fillStyle = 'rgba(0,0,0,0)'
      ctx.fillRect(0, 0, 256, 64)
      ctx.fillStyle = '#94a3b8'
      ctx.font = 'bold 20px Inter, sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(label.label, 128, 25)
      ctx.font = '14px Inter, sans-serif'
      ctx.fillStyle = '#64748b'
      ctx.fillText(`${label.area_m2} m²`, 128, 48)

      const texture = new THREE.CanvasTexture(canvas)
      const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true })
      const sprite = new THREE.Sprite(spriteMat)
      sprite.position.set(
        label.position[0] - centerX,
        0.3,
        label.position[2] - centerZ
      )
      sprite.scale.set(3, 0.75, 1)
      scene.add(sprite)
    })

    // Set camera target to center
    controls.target.set(0, 1.5, 0)
    controls.update()

    // Animation loop
    const animate = () => {
      animIdRef.current = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // Resize handler
    const handleResize = () => {
      const w = container.clientWidth
      const h = container.clientHeight || 400
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animIdRef.current)
      renderer.dispose()
    }
  }, [modelData])

  useEffect(() => {
    const cleanup = initScene()
    return cleanup
  }, [initScene])

  const resetCamera = useCallback(() => {
    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(12, 10, 16)
      controlsRef.current.target.set(0, 1.5, 0)
      controlsRef.current.update()
    }
  }, [])

  const topView = useCallback(() => {
    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(0, 20, 0.1)
      controlsRef.current.target.set(0, 0, 0)
      controlsRef.current.update()
    }
  }, [])

  return (
    <div className="section-card">
      <div className="section-header">
        <h2>🏠 3D Model</h2>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          {modelData?.metadata?.total_meshes || 0} meshes • Drag to rotate
        </span>
      </div>
      <div className="section-body" style={{ padding: 0 }}>
        <div className="model-viewer-container" ref={containerRef}>
          <div className="viewer-controls">
            <button onClick={resetCamera}>↻ Reset</button>
            <button onClick={topView}>⬇ Top</button>
          </div>
        </div>
      </div>
    </div>
  )
}
